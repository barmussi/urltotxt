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

def test_stream(url, timeout=15):
    """Probar un stream individual con FFmpeg por 15 segundos"""
    try:
        cmd = [
            "ffmpeg", 
            "-i", url, 
            "-t", "15",
            "-c", "copy", 
            "-f", "null", 
            "-y",
            "/dev/null"
        ]
        
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=20
        )
        
        if result.returncode == 0:
            return True, "OK"
        else:
            error_output = result.stderr
            if "403" in error_output:
                return False, "Error 403"
            elif "404" in error_output:
                return False, "Error 404"
            else:
                return False, "Error FFmpeg"
            
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, f"Exception: {str(e)}"

def parse_m3u_file(m3u_content):
    """Parsear contenido M3U"""
    channels = {}
    lines = m3u_content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF'):
            # Extraer nombre del canal
            last_comma = line.rfind(',')
            if last_comma != -1:
                channel_name = line[last_comma + 1:].strip()
                
                # Buscar URL
                i += 1
                while i < len(lines) and (not lines[i].strip() or lines[i].startswith('#')):
                    i += 1
                
                if i < len(lines) and lines[i].strip() and not lines[i].startswith('#'):
                    url = lines[i].strip()
                    if channel_name and url:
                        if channel_name not in channels:
                            channels[channel_name] = []
                        channels[channel_name].append(url)
        i += 1
    
    return channels

def process_channel(channel):
    """Procesar un canal individual"""
    global process_status
    
    channel_name = channel['name']
    process_status['current_channel'] = channel_name
    process_status['channels_processed'] += 1
    
    logger.info(f"Procesando: {channel_name}")
    
    valid_servers = []
    
    # Probar servidores en paralelo
    server_data = [(channel_name, server) for server in channel['servers']]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for server in channel['servers']:
            future = executor.submit(test_stream, server['url'])
            futures.append((server, future))
        
        for server, future in futures:
            process_status['servers_checked'] += 1
            is_valid, error_msg = future.result()
            
            if is_valid:
                valid_servers.append(server)
                process_status['servers_working'] += 1
                logger.info(f"  ✅ {server['name']} funciona")
            else:
                logger.info(f"  ❌ {server['name']} falló: {error_msg}")
    
    # Reorganizar numeración
    for i, server in enumerate(valid_servers, 1):
        server['name'] = str(i)
    
    channel['servers'] = valid_servers
    return channel

def verify_m3u_urls(m3u_channels):
    """Verificar URLs del M3U"""
    global process_status
    
    verified_channels = {}
    total_urls = sum(len(urls) for urls in m3u_channels.values())
    checked_urls = 0
    
    for channel_name, urls in m3u_channels.items():
        valid_urls = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {executor.submit(test_stream, url): url for url in urls}
            
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                checked_urls += 1
                process_status['servers_checked'] += 1
                
                try:
                    is_valid, error_msg = future.result()
                    if is_valid:
                        valid_urls.append(url)
                        process_status['servers_working'] += 1
                        logger.info(f"  ✅ M3U URL funciona")
                    else:
                        logger.info(f"  ❌ M3U URL falló: {error_msg}")
                except Exception as e:
                    logger.error(f"Error verificando URL M3U: {e}")
        
        if valid_urls:
            verified_channels[channel_name] = valid_urls
    
    return verified_channels

def background_verification(json_url, m3u_content=None):
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
        
        # Descargar JSON
        logger.info("Descargando JSON...")
        response = requests.get(json_url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        total_channels = len(data['channels'])
        process_status['total_channels'] = total_channels
        process_status['current_stage'] = "Verifying JSON channels"
        
        logger.info(f"JSON descargado: {total_channels} canales")
        
        # Verificar canales JSON
        verified_channels = []
        for i, channel in enumerate(data['channels']):
            process_status['progress'] = (i / total_channels) * 50  # 50% para JSON
            verified_channel = process_channel(channel)
            if verified_channel['servers']:
                verified_channels.append(verified_channel)
        
        data['channels'] = verified_channels
        
        # Procesar M3U si está disponible
        if m3u_content:
            process_status['current_stage'] = "Verifying M3U channels"
            logger.info("Procesando M3U...")
            
            m3u_channels = parse_m3u_file(m3u_content)
            verified_m3u_channels = verify_m3u_urls(m3u_channels)
            
            # Combinar resultados (simplificado)
            for m3u_channel_name, urls in verified_m3u_channels.items():
                # Buscar canal existente
                existing_channel = None
                for channel in data['channels']:
                    if m3u_channel_name.lower() in channel['name'].lower() or channel['name'].lower() in m3u_channel_name.lower():
                        existing_channel = channel
                        break
                
                if existing_channel:
                    # Agregar URLs al canal existente
                    existing_urls = {server['url'] for server in existing_channel['servers']}
                    for url in urls:
                        if url not in existing_urls:
                            new_server_num = len(existing_channel['servers']) + 1
                            existing_channel['servers'].append({
                                'name': f'M3U_{new_server_num}',
                                'url': url
                            })
                else:
                    # Nuevo canal
                    data['channels'].append({
                        'name': m3u_channel_name,
                        'category': 'From M3U',
                        'imageUrl': '',
                        'servers': [{'name': str(i+1), 'url': url} for i, url in enumerate(urls)]
                    })
        
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
    <p>API para verificar canales M3U8</p>
    <ul>
        <li><a href="/status">Estado</a></li>
        <li><a href="/start">Iniciar verificación</a></li>
    </ul>
    """

@app.route('/status')
def status():
    """Obtener estado del proceso"""
    return jsonify(process_status)

@app.route('/start', methods=['POST'])
def start_verification():
    """Iniciar proceso de verificación"""
    global process_status
    
    if process_status['is_running']:
        return jsonify({"error": "El proceso ya está en ejecución"}), 409
    
    # Obtener parámetros
    json_url = request.json.get('json_url', 'https://muyproject.netlify.app/data2.json')
    m3u_content = request.json.get('m3u_content')
    
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
    thread = threading.Thread(target=background_verification, args=(json_url, m3u_content))
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "message": "Proceso iniciado", 
        "status_url": "/status",
        "download_url": "/download"
    })

@app.route('/download')
def download_results():
    """Descargar resultados"""
    if not process_results['output_file'] or not os.path.exists(process_results['output_file']):
        return jsonify({"error": "No hay archivos disponibles"}), 404
    
    return send_file(
        process_results['output_file'],
        as_attachment=True,
        download_name=process_results['output_file']
    )

@app.route('/upload_m3u', methods=['POST'])
def upload_m3u():
    """Subir archivo M3U"""
    if 'file' not in request.files:
        return jsonify({"error": "No se envió archivo"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "Nombre de archivo vacío"}), 400
    
    if file and file.filename.endswith('.m3u'):
        content = file.read().decode('utf-8')
        return jsonify({
            "message": "Archivo M3U recibido",
            "lines": len(content.split('\n'))
        })
    
    return jsonify({"error": "Archivo debe ser .m3u"}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
