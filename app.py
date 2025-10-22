#!/usr/bin/env python3
"""
Servicio Web para Verificación de Canales M3U8 en Render.com
"""

from flask import Flask, request, jsonify, send_file
import json
import requests
import subprocess
import concurrent.futures
import time
import os
import sys
import threading
from datetime import datetime
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Estado global del proceso
process_status = {
    "is_running": False,
    "start_time": None,
    "progress": 0,
    "current_channel": "",
    "channels_processed": 0,
    "total_channels": 0,
    "servers_checked": 0,
    "servers_working": 0,
    "estimated_time_remaining": None,
    "current_stage": "Idle"
}

# Resultados
process_results = {
    "output_file": None,
    "error": None
}

def test_stream(url, timeout=10):
    """Probar un stream individual con FFmpeg por 10 segundos (reducido para pruebas)"""
    try:
        cmd = [
            "ffmpeg", 
            "-i", url, 
            "-t", "10",  # Reducido a 10 segundos para pruebas
            "-c", "copy", 
            "-f", "null", 
            "-y",
            "/dev/null"
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=15
        )
        
        if result.returncode == 0:
            return True, "OK"
        else:
            return False, "FFmpeg error"
            
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, f"Exception: {str(e)}"

def background_verification():
    """Proceso principal en segundo plano"""
    global process_status, process_results
    
    try:
        process_status.update({
            "is_running": True,
            "start_time": datetime.now().isoformat(),
            "progress": 0,
            "current_channel": "",
            "channels_processed": 0,
            "servers_checked": 0,
            "servers_working": 0,
            "current_stage": "Downloading JSON"
        })
        
        # URL del JSON
        json_url = "https://muyproject.netlify.app/data2.json"
        
        # Descargar JSON
        logger.info("Descargando JSON...")
        response = requests.get(json_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        total_channels = len(data['channels'])
        process_status['total_channels'] = total_channels
        process_status['current_stage'] = "Verifying JSON channels"
        
        logger.info(f"JSON descargado: {total_channels} canales")
        
        # Verificar canales JSON (versión simplificada para prueba)
        verified_channels = []
        total_servers = sum(len(channel['servers']) for channel in data['channels'])
        servers_checked = 0
        
        for i, channel in enumerate(data['channels']):
            process_status['current_channel'] = channel['name']
            process_status['channels_processed'] = i
            process_status['progress'] = (i / total_channels) * 100
            
            logger.info(f"Procesando: {channel['name']}")
            
            valid_servers = []
            
            # Probar servidores en paralelo (limitado para no sobrecargar)
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                for server in channel['servers']:
                    future = executor.submit(test_stream, server['url'])
                    futures.append((server, future))
                
                for server, future in futures:
                    servers_checked += 1
                    process_status['servers_checked'] = servers_checked
                    
                    is_valid, error_msg = future.result()
                    
                    if is_valid:
                        valid_servers.append(server)
                        process_status['servers_working'] += 1
                        logger.info(f"  ✅ {server['name']} funciona")
                    else:
                        logger.info(f"  ❌ {server['name']} falló: {error_msg}")
            
            # Reorganizar numeración
            for j, server in enumerate(valid_servers, 1):
                server['name'] = str(j)
            
            channel['servers'] = valid_servers
            if valid_servers:
                verified_channels.append(channel)
            
            # Pequeña pausa para no sobrecargar
            time.sleep(1)
        
        data['channels'] = verified_channels
        
        process_status['progress'] = 100
        process_status['current_stage'] = "Saving results"
        
        # Guardar resultado
        timestamp = int(time.time())
        output_file = f"canales_verificados_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        process_results['output_file'] = output_file
        process_status['is_running'] = False
        process_status['current_stage'] = "Completed"
        
        logger.info("Proceso completado exitosamente!")
        
    except Exception as e:
        logger.error(f"Error en el proceso: {e}")
        process_results['error'] = str(e)
        process_status['is_running'] = False
        process_status['current_stage'] = "Error"

@app.route('/')
def home():
    """Página principal"""
    return """
    <h1>Verificador de Canales M3U8</h1>
    <p>Servicio funcionando correctamente</p>
    <ul>
        <li><a href="/status">Estado del sistema</a></li>
        <li><a href="/start">Iniciar verificación</a></li>
        <li><a href="/download" target="_blank">Descargar resultados</a></li>
    </ul>
    <p>Usa <code>POST /start</code> para iniciar el proceso</p>
    """

@app.route('/status')
def status():
    """Obtener estado del proceso"""
    return jsonify(process_status)

@app.route('/start', methods=['GET', 'POST'])
def start_verification():
    """Iniciar proceso de verificación"""
    global process_status
    
    if process_status['is_running']:
        return jsonify({
            "error": "El proceso ya está en ejecución", 
            "status": process_status
        }), 409
    
    # Reiniciar estado
    process_status.update({
        "is_running": True,
        "start_time": datetime.now().isoformat(),
        "progress": 0,
        "current_channel": "",
        "channels_processed": 0,
        "servers_checked": 0,
        "servers_working": 0,
        "total_channels": 0,
        "current_stage": "Starting"
    })
    
    process_results.update({
        "output_file": None,
        "error": None
    })
    
    # Ejecutar en segundo plano
    thread = threading.Thread(target=background_verification)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": "Proceso de verificación iniciado", 
        "status_url": "/status",
        "download_url": "/download",
        "estimated_time": "30-60 minutos"
    })

@app.route('/download')
def download_results():
    """Descargar resultados"""
    if not process_results['output_file']:
        return jsonify({"error": "No hay resultados disponibles"}), 404
    
    if not os.path.exists(process_results['output_file']):
        return jsonify({"error": "Archivo de resultados no encontrado"}), 404
    
    return send_file(
        process_results['output_file'],
        as_attachment=True,
        download_name=process_results['output_file']
    )

@app.route('/health')
def health_check():
    """Health check para Render"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
