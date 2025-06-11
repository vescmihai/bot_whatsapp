#!/usr/bin/env python3
"""
Script de pruebas para desarrollo local del Bot WhatsApp
Ejecutar: python test_local.py
"""

import requests
import json
import time
import os
from datetime import datetime

# Configuración
BASE_URL = "http://localhost:5000"
NUMERO_PRUEBA = "+59171234567"  # Cambia por tu número

def print_header(titulo):
    """Imprime encabezado bonito"""
    print(f"\n{'='*60}")
    print(f"🧪 {titulo}")
    print(f"{'='*60}")

def print_result(exito, mensaje):
    """Imprime resultado de prueba"""
    emoji = "✅" if exito else "❌"
    print(f"{emoji} {mensaje}")

def test_servidor():
    """Verifica que el servidor esté funcionando"""
    print_header("VERIFICANDO SERVIDOR")
    
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            print_result(True, "Servidor funcionando correctamente")
            print(f"   📊 Estado BD: {data.get('base_datos', 'No disponible')}")
            print(f"   📱 Sandbox: {data.get('twilio_sandbox', 'No configurado')}")
            return True
        else:
            print_result(False, f"Servidor respondió con código {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print_result(False, "No se puede conectar al servidor")
        print("   💡 Asegúrate de que el servidor esté corriendo: python app_twilio_local.py")
        return False
    except Exception as e:
        print_result(False, f"Error inesperado: {e}")
        return False

def test_mensaje_simple():
    """Prueba el procesamiento básico de mensajes"""
    print_header("PRUEBA DE MENSAJE SIMPLE")
    
    payload = {
        "telefono": NUMERO_PRUEBA,
        "mensaje": "Hola, ¿qué laptops gaming tienen disponibles?"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/test_mensaje", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('exito'):
                print_result(True, "Mensaje procesado correctamente")
                respuesta = data.get('respuesta', '')
                print(f"   🤖 Respuesta: {respuesta[:100]}...")
                print(f"   💬 Conversación ID: {data.get('conversacion_id')}")
                print(f"   🎯 Tipo interés: {data.get('tipo_interes')}")
                print(f"   📄 PDF generado: {'Sí' if data.get('pdf_generado') else 'No'}")
                return True
            else:
                print_result(False, f"Error procesando: {data.get('error')}")
                return False
        else:
            print_result(False, f"Error HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"Error en prueba: {e}")
        return False

def test_comando_intereses():
    """Prueba el comando especial de intereses"""
    print_header("PRUEBA DE COMANDO 'MIS INTERESES'")
    
    payload = {
        "telefono": NUMERO_PRUEBA,
        "mensaje": "mis intereses"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/test_mensaje", json=payload, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('exito'):
                print_result(True, "Comando de intereses procesado")
                print(f"   📄 PDF generado: {'Sí' if data.get('pdf_generado') else 'No'}")
                return True
            else:
                print_result(False, f"Error: {data.get('error')}")
                return False
        else:
            print_result(False, f"Error HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_generar_pdf():
    """Prueba la generación directa de PDF"""
    print_header("PRUEBA DE GENERACIÓN PDF")
    
    payload = {
        "telefono": NUMERO_PRUEBA
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/generar_pdf_local", json=payload, timeout=20)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('exito'):
                print_result(True, "PDF generado correctamente")
                print(f"   📁 Archivo: {data.get('archivo')}")
                print(f"   📊 Tamaño: {data.get('tamaño_base64')} caracteres base64")
                
                # Verificar que el archivo existe
                archivo = data.get('archivo', '')
                if archivo and os.path.exists(archivo):
                    size = os.path.getsize(archivo)
                    print(f"   💾 Tamaño archivo: {size} bytes")
                    print_result(True, "Archivo PDF creado exitosamente")
                    return True
                else:
                    print_result(False, "Archivo PDF no encontrado")
                    return False
            else:
                print_result(False, f"Error generando PDF: {data.get('error')}")
                print(f"   📝 Detalle: {data.get('detalle', 'N/A')}")
                return False
        else:
            print_result(False, f"Error HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def test_envio_whatsapp():
    """Prueba el envío real por WhatsApp (requiere configuración Twilio)"""
    print_header("PRUEBA DE ENVÍO WHATSAPP")
    
    mensaje_test = f"🧪 Mensaje de prueba desde el bot - {datetime.now().strftime('%H:%M:%S')}"
    
    payload = {
        "telefono": NUMERO_PRUEBA,
        "mensaje": mensaje_test
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/enviar_whatsapp_local", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get('exito'):
                print_result(True, "Mensaje enviado por WhatsApp")
                print(f"   📱 SID: {data.get('mensaje_sid')}")
                print(f"   📞 Número: {NUMERO_PRUEBA}")
                print(f"   💬 Mensaje: {mensaje_test}")
                return True
            else:
                print_result(False, f"Error enviando: {data.get('error')}")
                return False
        else:
            print_result(False, f"Error HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"Error: {e}")
        print("   💡 Asegúrate de que las credenciales de Twilio estén configuradas")
        return False

def test_simulacion_webhook():
    """Simula un webhook completo de Twilio"""
    print_header("SIMULACIÓN DE WEBHOOK TWILIO")
    
    # Datos que Twilio enviaría
    webhook_data = {
        'Body': '¿Tienen mouse gaming RGB?',
        'From': f'whatsapp:{NUMERO_PRUEBA}',
        'To': 'whatsapp:+14155238886',
        'MessageSid': f'test_sid_{datetime.now().strftime("%H%M%S")}'
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/twilio/webhook",
            data=webhook_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=15
        )
        
        if response.status_code == 200:
            respuesta_twiml = response.text
            
            # Verificar que es TwiML válido
            if '<Response>' in respuesta_twiml and '<Message>' in respuesta_twiml:
                print_result(True, "Webhook procesado correctamente")
                print(f"   📄 Respuesta TwiML generada ({len(respuesta_twiml)} caracteres)")
                
                # Extraer mensaje de la respuesta
                import re
                match = re.search(r'<Message><!\[CDATA\[(.*?)\]\]></Message>', respuesta_twiml)
                if match:
                    mensaje_respuesta = match.group(1)
                    print(f"   🤖 Mensaje: {mensaje_respuesta[:100]}...")
                
                return True
            else:
                print_result(False, "Respuesta no es TwiML válido")
                print(f"   📄 Respuesta: {respuesta_twiml[:200]}...")
                return False
        else:
            print_result(False, f"Error HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print_result(False, f"Error: {e}")
        return False

def mostrar_archivos_generados():
    """Muestra los archivos PDF generados"""
    print_header("ARCHIVOS GENERADOS")
    
    try:
        if os.path.exists("temp_pdfs"):
            archivos = os.listdir("temp_pdfs")
            archivos_pdf = [f for f in archivos if f.endswith('.pdf')]
            
            if archivos_pdf:
                print(f"📁 Se encontraron {len(archivos_pdf)} archivos PDF:")
                for archivo in archivos_pdf:
                    ruta = os.path.join("temp_pdfs", archivo)
                    size = os.path.getsize(ruta)
                    timestamp = os.path.getmtime(ruta)
                    fecha = datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')
                    print(f"   📄 {archivo} - {size} bytes - {fecha}")
            else:
                print("📂 No se encontraron archivos PDF")
        else:
            print("📂 Directorio temp_pdfs no existe")
            
    except Exception as e:
        print(f"❌ Error listando archivos: {e}")

def main():
    """Ejecuta todas las pruebas"""
    print("🚀 INICIANDO PRUEBAS LOCALES DEL BOT WHATSAPP")
    print(f"⏰ Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"📞 Número de prueba: {NUMERO_PRUEBA}")
    
    # Lista de pruebas
    pruebas = [
        ("Servidor funcionando", test_servidor),
        ("Mensaje simple", test_mensaje_simple),
        ("Comando intereses", test_comando_intereses),
        ("Generación PDF", test_generar_pdf),
        ("Envío WhatsApp", test_envio_whatsapp),
        ("Simulación Webhook", test_simulacion_webhook)
    ]
    
    resultados = []
    
    # Ejecutar pruebas
    for nombre, test_func in pruebas:
        print(f"\n⏳ Ejecutando: {nombre}...")
        resultado = test_func()
        resultados.append((nombre, resultado))
        
        if not resultado:
            print("⚠️ Prueba falló, continuando con las siguientes...")
        
        time.sleep(1)  # Pausa entre pruebas
    
    # Mostrar archivos generados
    mostrar_archivos_generados()
    
    # Resumen final
    print_header("RESUMEN DE PRUEBAS")
    
    exitosas = 0
    for nombre, resultado in resultados:
        status = "✅ EXITOSA" if resultado else "❌ FALLIDA"
        print(f"{nombre}: {status}")
        if resultado:
            exitosas += 1
    
    print(f"\n🎯 RESULTADO FINAL: {exitosas}/{len(resultados)} pruebas exitosas")
    
    # Recomendaciones
    print_header("RECOMENDACIONES")
    
    if exitosas == len(resultados):
        print("🎉 ¡Excelente! Todas las pruebas pasaron.")
        print("🚀 Tu bot está listo para usar.")
        print("\n📱 Para usar con WhatsApp:")
        print("1. Ejecuta: ngrok http 5000")
        print("2. Configura el webhook en Twilio Console")
        print("3. Activa el sandbox de WhatsApp")
        print("4. ¡Envía mensajes desde tu WhatsApp!")
    else:
        print("⚠️ Algunas pruebas fallaron. Revisa:")
        
        if not resultados[0][1]:  # Servidor
            print("• Asegúrate de que el servidor esté corriendo")
            print("• Ejecuta: python app_twilio_local.py")
        
        if not resultados[4][1]:  # WhatsApp
            print("• Verifica las credenciales de Twilio")
            print("• Asegúrate de que el sandbox esté activado")
        
        print("\n💡 Consulta los logs para más detalles")
    
    return exitosas == len(resultados)

def mostrar_comandos_utiles():
    """Muestra comandos útiles para desarrollo"""
    print_header("COMANDOS ÚTILES PARA DESARROLLO")
    
    print("🔧 CONFIGURACIÓN INICIAL:")
    print("pip install twilio flask flask-cors requests")
    print("")
    
    print("🚀 EJECUTAR SERVIDOR:")
    print("python app_twilio_local.py")
    print("")
    
    print("🌐 EXPONER CON NGROK:")
    print("npm install -g ngrok")
    print("ngrok http 5000")
    print("")
    
    print("🧪 EJECUTAR PRUEBAS:")
    print("python test_local.py")
    print("")
    
    print("📱 CONFIGURAR TWILIO:")
    print("1. Ve a https://console.twilio.com/")
    print("2. Messaging > Try it out > Send a WhatsApp message")
    print("3. Configura webhook: https://tu-dominio.ngrok.io/twilio/webhook")
    print("4. Activa sandbox enviando mensaje de activación")
    print("")
    
    print("💬 COMANDOS DEL BOT:")
    print("• 'mis intereses' - Genera PDF personalizado")
    print("• 'estado' - Muestra estado del sistema")
    print("• Cualquier pregunta sobre productos gaming")

def test_interactivo():
    """Modo interactivo para probar mensajes"""
    print_header("MODO INTERACTIVO")
    print("Escribe mensajes para probar el bot (escribe 'salir' para terminar)")
    
    while True:
        try:
            mensaje = input("\n💬 Tu mensaje: ").strip()
            
            if mensaje.lower() in ['salir', 'exit', 'quit']:
                print("👋 Saliendo del modo interactivo...")
                break
            
            if not mensaje:
                continue
            
            payload = {
                "telefono": NUMERO_PRUEBA,
                "mensaje": mensaje
            }
            
            print("⏳ Procesando...")
            
            response = requests.post(f"{BASE_URL}/api/test_mensaje", json=payload, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('exito'):
                    respuesta = data.get('respuesta', '')
                    print(f"🤖 Bot: {respuesta}")
                    
                    if data.get('pdf_generado'):
                        print("📄 PDF generado para esta consulta")
                else:
                    print(f"❌ Error: {data.get('error')}")
            else:
                print(f"❌ Error HTTP: {response.status_code}")
                
        except KeyboardInterrupt:
            print("\n👋 Saliendo...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando == "help":
            mostrar_comandos_utiles()
        elif comando == "interactive":
            test_interactivo()
        elif comando == "servidor":
            test_servidor()
        elif comando == "whatsapp":
            test_envio_whatsapp()
        elif comando == "pdf":
            test_generar_pdf()
        else:
            print(f"❌ Comando desconocido: {comando}")
            print("Comandos disponibles: help, interactive, servidor, whatsapp, pdf")
    else:
        # Ejecutar todas las pruebas
        main()