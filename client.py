#!/usr/bin/env python3
"""
Cliente para el servicio de verificación de canales
"""

import requests
import json
import time
import sys

def main():
    # URL de tu app en Render (cambiar por tu URL real)
    base_url = "https://tu-app.render.com"  # Cambiar por tu URL
    
    # Opción 1: Solo JSON
    payload = {
        "json_url": "https://muyproject.netlify.app/data2.json"
    }
    
    # Opción 2: Con archivo M3U (subir primero)
    # Primero subir el archivo M3U
    with open('tul.m3u', 'r') as f:
        m3u_content = f.read()
    
    payload = {
        "json_url": "https://muyproject.netlify.app/data2.json",
        "m3u_content": m3u_content
    }
    
    print("Iniciando verificación...")
    response = requests.post(f"{base_url}/start", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['message']}")
        print(f"📊 Estado: {base_url}/status")
        print(f"📥 Descarga: {base_url}/download")
        
        # Monitorear progreso
        while True:
            status_response = requests.get(f"{base_url}/status")
            status = status_response.json()
            
            print(f"\rProgreso: {status['progress']:.1f}% | "
                  f"Canales: {status['channels_processed']}/{status['total_channels']} | "
                  f"Servidores: {status['servers_working']}/{status['servers_checked']} | "
                  f"Etapa: {status['current_stage']}", end="")
            
            if not status['is_running']:
                break
                
            time.sleep(5)
        
        print("\n\n✅ Proceso completado!")
        
        # Descargar resultado
        download_response = requests.get(f"{base_url}/download")
        if download_response.status_code == 200:
            with open('resultado_final.json', 'wb') as f:
                f.write(download_response.content)
            print("📁 Resultado descargado: resultado_final.json")
        else:
            print("❌ Error descargando resultado")
    
    else:
        print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    main()