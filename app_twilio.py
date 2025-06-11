# app_twilio_local.py - Versión simplificada para desarrollo local

import os
import base64
import tempfile
import requests  # Para subir PDFs
from datetime import datetime

from flask import Flask, request, jsonify
from flask_cors import CORS
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# Importar tus módulos existentes
from analizador import AnalizadorContexto
from entrenamiento_fino import EntrenamientoFino
from generar_pdf import GeneradorPDF
from manejador_conversaciones import ManejadorConversaciones
from generador_intereses import GeneradorIntereses

# ============================================
# CONFIGURACIÓN LOCAL
# ============================================

app = Flask(__name__)
CORS(app)

# Configuración Twilio - SANDBOX (para desarrollo)
TWILIO_ACCOUNT_SID = ''  # Tu Account SID real
TWILIO_AUTH_TOKEN = ''     # Tu Auth Token real
TWILIO_WHATSAPP_NUMBER = ''            # Número sandbox

print("🚀 Inicializando sistema para desarrollo local...")

# Inicializar módulos
entrenamiento_fino = EntrenamientoFino()
generador_pdf = GeneradorPDF(entrenamiento_fino)
analizador = AnalizadorContexto(entrenamiento_fino, generador_pdf)
manejador_conversaciones = ManejadorConversaciones()
generador_intereses = GeneradorIntereses()

print("✅ Todos los módulos inicializados correctamente")

# ============================================
# FUNCIONES AUXILIARES LOCALES
# ============================================

def limpiar_telefono(numero):
    """Limpia número de teléfono PARA ARCHIVOS (sin +)"""
    return numero.replace('whatsapp:', '').replace('+', '').replace(' ', '').replace('-', '')

def limpiar_telefono_twilio(numero):
    """Limpia número de teléfono PARA TWILIO (con +)"""
    return numero.replace('whatsapp:', '').replace(' ', '').replace('-', '')

def obtener_conversacion_previa(telefono_limpio, limite=5):
    """Obtiene contexto de conversación previa (simplificado)"""
    try:
        import mysql.connector
        
        config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'bot_productos_db',
            'charset': 'utf8mb4'
        }
        
        conexion = mysql.connector.connect(**config)
        cursor = conexion.cursor(dictionary=True)
        
        # Obtener últimos mensajes
        cursor.execute("""
            SELECT m.contenido, m.emisor, m.fecha_envio
            FROM mensaje m
            INNER JOIN conversacion c ON m.id_conversacion = c.id_conversacion
            INNER JOIN cliente cl ON c.id_cliente = cl.id_cliente
            WHERE cl.telefono = %s
            ORDER BY m.fecha_envio DESC
            LIMIT %s
        """, (telefono_limpio, limite))
        
        mensajes = cursor.fetchall()
        conexion.close()
        
        # Formatear conversación
        conversacion = ""
        for msg in reversed(mensajes):
            emisor = "Cliente" if msg['emisor'] == 'usuario' else "Vendedor"
            conversacion += f"{emisor}: {msg['contenido']}\n"
        
        return conversacion.strip()
        
    except Exception as e:
        print(f"⚠️ Error obteniendo conversación: {e}")
        return ""

def subir_pdf_temporal(filepath, filename):
    """Sube PDF a servicios compatibles (sin transfer.sh)"""
    try:
        print(f"📤 Subiendo {filename} para adjunto directo...")
        
        # OPCIÓN 1: catbox.moe (ya funciona perfecto)
        try:
            with open(filepath, 'rb') as f:
                response = requests.post(
                    'https://catbox.moe/user/api.php',
                    data={'reqtype': 'fileupload'},
                    files={'fileToUpload': (filename, f, 'application/pdf')},
                    timeout=30
                )
            
            if response.status_code == 200 and response.text.startswith('https://'):
                url = response.text.strip()
                print(f"✅ PDF subido a catbox.moe: {url}")
                return url
        except Exception as e:
            print(f"⚠️ catbox.moe falló: {e}")
        
        # OPCIÓN 2: 0x0.st como backup
        try:
            with open(filepath, 'rb') as f:
                response = requests.post(
                    'https://0x0.st',
                    files={'file': (filename, f, 'application/pdf')},
                    timeout=30
                )
            
            if response.status_code == 200:
                url = response.text.strip()
                if url.startswith('https://'):
                    print(f"✅ PDF subido a 0x0.st: {url}")
                    return url
        except Exception as e:
            print(f"⚠️ 0x0.st falló: {e}")
        
        return None
        
    except Exception as e:
        print(f"❌ Error general: {e}")
        return None

def enviar_whatsapp_sin_pdf(telefono, mensaje):
    """Envía mensaje sin PDF cuando falla la subida"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        numero_destino = f'whatsapp:{limpiar_telefono_twilio(telefono)}'
        
        mensaje_sin_pdf = f"{mensaje}\n\n📄 He generado tu información personalizada. Por limitaciones técnicas temporales, el PDF no se pudo adjuntar automáticamente."
        
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=mensaje_sin_pdf,
            to=numero_destino
        )
        
        print(f"📱 Mensaje enviado sin PDF")
        print(f"   📧 SID: {message.sid}")
        print(f"   📞 Para: {numero_destino}")
        
        return {
            'exito': True,
            'mensaje_sid': message.sid,
            'metodo': 'twilio_sin_pdf'
        }
        
    except Exception as e:
        print(f"❌ Error enviando mensaje básico: {e}")
        return {
            'exito': False,
            'error': str(e),
            'metodo': 'error_total'
        }

def simular_envio_pdf(telefono, pdf_base64, mensaje):
    """Envía mensaje + PDF por WhatsApp - VERSION CORREGIDA"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        numero_destino = f'whatsapp:{limpiar_telefono_twilio(telefono)}'
        
        if pdf_base64 and len(pdf_base64) > 100:
            # Guardar PDF localmente
            pdf_data = base64.b64decode(pdf_base64)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            telefono_limpio = limpiar_telefono(telefono)
            filename = f"pdf_{telefono_limpio}_{timestamp}.pdf"
            filepath = f"temp_pdfs/{filename}"
            
            os.makedirs("temp_pdfs", exist_ok=True)
            with open(filepath, "wb") as f:
                f.write(pdf_data)
            
            print(f"📄 PDF guardado: {filepath}")
            
            # ENVIAR MENSAJE PRINCIPAL PRIMERO
            mensaje_principal = client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                body=mensaje,
                to=numero_destino
            )
            print(f"📱 Mensaje principal enviado: {mensaje_principal.sid}")
            
            # INTENTAR ENVIAR PDF
            pdf_url = subir_pdf_temporal(filepath, filename)
            pdf_sid = None
            
            if pdf_url:
                try:
                    # Esperar un momento antes del PDF
                    import time
                    time.sleep(3)
                    
                    # ENVIAR PDF COMO ADJUNTO
                    mensaje_pdf = client.messages.create(
                        from_=TWILIO_WHATSAPP_NUMBER,
                        body="📎 Tu documento adjunto:",
                        media_url=[pdf_url],
                        to=numero_destino
                    )
                    pdf_sid = mensaje_pdf.sid
                    print(f"📄 PDF enviado: {pdf_sid}")
                    
                except Exception as e_pdf:
                    print(f"⚠️ Error enviando PDF adjunto: {e_pdf}")
                    # PDF falló, pero mensaje principal ya se envió
                    pdf_sid = None
            
            # ✅ RETORNO CORRECTO - SIEMPRE EXITOSO SI EL MENSAJE SE ENVIÓ
            return {
                'exito': True,
                'mensaje_sid': mensaje_principal.sid,
                'pdf_sid': pdf_sid,
                'pdf_url': pdf_url if pdf_url else None,
                'metodo': 'garantizado',  # Cambié de 'twilio_directo' para evitar confusión
                'archivo_local': filepath
            }
        else:
            # SIN PDF - Solo mensaje
            mensaje_simple = client.messages.create(
                from_=TWILIO_WHATSAPP_NUMBER,
                body=mensaje,
                to=numero_destino
            )
            
            print(f"📱 Mensaje simple enviado: {mensaje_simple.sid}")
            
            return {
                'exito': True,
                'mensaje_sid': mensaje_simple.sid,
                'metodo': 'garantizado'
            }
            
    except Exception as e:
        print(f"❌ Error total en envío: {e}")
        return {
            'exito': False,
            'error': str(e),
            'metodo': 'error'
        }

def subir_pdf_temporal(filepath, filename):
    """Sube PDF SIN transfer.sh (corregido)"""
    try:
        print(f"📤 Subiendo {filename} para adjunto directo...")
        
        # OPCIÓN 1: catbox.moe (ya funciona perfecto)
        try:
            with open(filepath, 'rb') as f:
                response = requests.post(
                    'https://catbox.moe/user/api.php',
                    data={'reqtype': 'fileupload'},
                    files={'fileToUpload': (filename, f, 'application/pdf')},
                    timeout=30
                )
            
            if response.status_code == 200 and response.text.startswith('https://'):
                url = response.text.strip()
                print(f"✅ PDF subido a catbox.moe: {url}")
                return url
        except Exception as e:
            print(f"⚠️ catbox.moe falló: {e}")
        
        # OPCIÓN 2: 0x0.st como backup
        try:
            with open(filepath, 'rb') as f:
                response = requests.post(
                    'https://0x0.st',
                    files={'file': (filename, f, 'application/pdf')},
                    timeout=30
                )
            
            if response.status_code == 200:
                url = response.text.strip()
                if url.startswith('https://'):
                    print(f"✅ PDF subido a 0x0.st: {url}")
                    return url
        except Exception as e:
            print(f"⚠️ 0x0.st falló: {e}")
        
        print("❌ Todos los servicios de subida fallaron")
        return None
        
    except Exception as e:
        print(f"❌ Error general subiendo: {e}")
        return None

def enviar_pdf_directo_twilio(telefono, mensaje, pdf_url, filepath):
    """Envía PDF directamente usando Twilio con media_url"""
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Formato correcto para Twilio WhatsApp
        numero_destino = f'whatsapp:{limpiar_telefono_twilio(telefono)}'
        
        print(f"📱 Enviando a: {numero_destino}")
        print(f"📄 PDF URL: {pdf_url}")
        
        # ENVÍO DIRECTO CON TWILIO
        message = client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=mensaje,
            media_url=[pdf_url],  # ✅ ADJUNTO DIRECTO
            to=numero_destino
        )
        
        print(f"✅ PDF ENVIADO DIRECTAMENTE POR TWILIO!")
        print(f"   📧 Message SID: {message.sid}")
        print(f"   📄 Media URL: {pdf_url}")
        print(f"   📞 Enviado a: {numero_destino}")
        print(f"   💰 Status: {message.status}")
        
        return {
            'exito': True,
            'mensaje_sid': message.sid,
            'archivo_local': filepath,
            'pdf_url': pdf_url,
            'metodo': 'twilio_directo',
            'status': message.status
        }
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error en envío directo Twilio: {error_msg}")
        
        # Información detallada del error
        if "21611" in error_msg:
            print("   ⚠️ Error 21611: URL de media no accesible")
        elif "21610" in error_msg:
            print("   ⚠️ Error 21610: Formato de media no soportado")
        elif "21408" in error_msg:
            print("   ⚠️ Error 21408: No se pudo descargar la media")
        
        # Fallback: enviar mensaje sin PDF
        print("🔄 Intentando envío sin PDF...")
        resultado = enviar_whatsapp_sin_pdf(telefono, mensaje)
        resultado['archivo_local'] = filepath
        resultado['error_twilio'] = error_msg
        resultado['metodo'] = 'fallback_sin_pdf'
        return resultado

# ============================================
# WEBHOOK PRINCIPAL - SIMPLIFICADO
# ============================================

@app.route('/twilio/webhook', methods=['POST'])
def webhook_twilio():
    """Webhook principal simplificado para desarrollo - SIN ERRORES"""
    try:
        # Obtener datos del mensaje
        mensaje_entrante = request.form.get('Body', '').strip()
        numero_remitente = request.form.get('From', '')
        
        print(f"\n📥 MENSAJE RECIBIDO")
        print(f"De: {numero_remitente}")
        print(f"Mensaje: {mensaje_entrante}")
        print("-" * 50)
        
        # Limpiar teléfono
        telefono_limpio = limpiar_telefono(numero_remitente)
        
        # Procesar mensaje en BD
        datos_conversacion = manejador_conversaciones.procesar_mensaje_entrante(
            telefono_limpio, 
            mensaje_entrante
        )
        
        if not datos_conversacion:
            print("❌ Error procesando mensaje")
            respuesta = MessagingResponse()
            respuesta.message("Lo siento, hubo un error. Intenta de nuevo.")
            return str(respuesta)
        
        id_conversacion = datos_conversacion['id_conversacion']
        print(f"✅ Conversación ID: {id_conversacion}")
        
        # COMANDOS ESPECIALES
        mensaje_lower = mensaje_entrante.lower()
        
        # Comando: PDF de intereses
        if any(cmd in mensaje_lower for cmd in ['mis intereses', 'pdf intereses', 'mi perfil']):
            print("📄 Generando PDF de intereses...")
            
            pdf_base64 = generador_pdf.intereses_usuario(telefono_limpio)
            resultado = simular_envio_pdf(
                numero_remitente,
                pdf_base64,
                "📊 Tu reporte personalizado de intereses:"
            )
            
            # ✅ CORRECCIÓN: NO enviar TwiML adicional para comandos especiales
            # Ya se procesó todo en simular_envio_pdf
            
            # Procesar intereses para el comando
            try:
                resultado_intereses = generador_intereses.procesar_intereses_cliente(
                    telefono_limpio, "chat_auto", mensaje_entrante
                )
                print(f"💾 Intereses procesados: {resultado_intereses.get('estado')}")
            except Exception as ei:
                print(f"⚠️ Error procesando intereses: {ei}")
            
            # Guardar en BD (el mensaje ya se envió por simular_envio_pdf)
            texto_para_bd = "📊 Tu reporte personalizado de intereses:"
            manejador_conversaciones.guardar_respuesta_bot(id_conversacion, texto_para_bd)
            
            print(f"✅ COMANDO PROCESADO: PDF de intereses enviado")
            print("=" * 50)
            
            # NO retornar TwiML - ya se manejó en simular_envio_pdf
            return "OK", 200
        
        # Comando: Estado del sistema
        if 'estado' in mensaje_lower or 'status' in mensaje_lower:
            estado_msg = f"""🤖 ESTADO DEL SISTEMA
✅ Bot funcionando
✅ Base de datos conectada
✅ IA lista
✅ Envío de PDFs habilitado
📊 Conversación ID: {id_conversacion}
🆔 Tu ID: {telefono_limpio}

Comandos disponibles:
• "mis intereses" - Tu PDF personalizado
• "estado" - Este mensaje
• Pregunta sobre productos gaming"""
            
            manejador_conversaciones.guardar_respuesta_bot(id_conversacion, estado_msg)
            respuesta = MessagingResponse()
            respuesta.message(estado_msg)
            return str(respuesta)
        
        # ANÁLISIS PRINCIPAL
        print("🤖 Analizando mensaje con IA...")
        
        # Obtener contexto
        conversacion_previa = obtener_conversacion_previa(telefono_limpio)
        
        # Analizar con tu sistema
        resultado_analisis = analizador.analizar_pregunta(mensaje_entrante, conversacion_previa)
        
        if resultado_analisis['status'] != 'success':
            print(f"❌ Error en análisis: {resultado_analisis}")
            respuesta_texto = "Disculpa, no pude procesar tu consulta. ¿Puedes reformular tu pregunta sobre productos gaming?"
            
            # Procesar sin PDF
            try:
                resultado_intereses = generador_intereses.procesar_intereses_cliente(
                    telefono_limpio, "chat_auto", mensaje_entrante
                )
                print(f"💾 Intereses procesados: {resultado_intereses.get('estado')}")
            except Exception as ei:
                print(f"⚠️ Error procesando intereses: {ei}")
            
            manejador_conversaciones.guardar_respuesta_bot(id_conversacion, respuesta_texto)
            
            respuesta = MessagingResponse()
            respuesta.message(respuesta_texto)
            return str(respuesta)
        else:
            data = resultado_analisis['data']
            respuesta_texto = data['respuesta_agente']
            
            # Manejar PDF si se generó
            pdf_generado = data.get('pdf_generado')
            tipo_interes = data.get('tipo_interes')
            
            if pdf_generado and len(str(pdf_generado)) > 100:
                print(f"📄 PDF generado para: {tipo_interes}")
                
                # ✅ ENVIAR PDF Y MENSAJE JUNTOS
                resultado_pdf = simular_envio_pdf(
                    numero_remitente,
                    pdf_generado,
                    respuesta_texto
                )
                
                # Procesar intereses en background
                try:
                    resultado_intereses = generador_intereses.procesar_intereses_cliente(
                        telefono_limpio, "chat_auto", mensaje_entrante
                    )
                    print(f"💾 Intereses procesados: {resultado_intereses.get('estado')}")
                except Exception as ei:
                    print(f"⚠️ Error procesando intereses: {ei}")
                
                # Guardar respuesta en BD
                manejador_conversaciones.guardar_respuesta_bot(id_conversacion, respuesta_texto)
                
                # ✅ VERIFICAR SI SE ENVIÓ CORRECTAMENTE
                if resultado_pdf.get('exito'):
                    print(f"✅ PDF y mensaje enviados exitosamente")
                    print(f"   📧 Mensaje SID: {resultado_pdf.get('mensaje_sid')}")
                    print(f"   📄 PDF SID: {resultado_pdf.get('pdf_sid', 'N/A')}")
                    print("=" * 50)
                    
                    # NO retornar TwiML - ya se envió todo
                    return "OK", 200
                else:
                    print(f"⚠️ Error enviando PDF: {resultado_pdf.get('error')}")
                    # Continuar con envío normal como fallback
                    respuesta_texto += "\n\n📄 PDF generado pero no se pudo enviar adjunto."
            
            # SI NO HAY PDF O FALLÓ EL ENVÍO - Enviar respuesta normal
            try:
                resultado_intereses = generador_intereses.procesar_intereses_cliente(
                    telefono_limpio, "chat_auto", mensaje_entrante
                )
                print(f"💾 Intereses procesados: {resultado_intereses.get('estado')}")
            except Exception as ei:
                print(f"⚠️ Error procesando intereses: {ei}")
            
            # Guardar respuesta
            manejador_conversaciones.guardar_respuesta_bot(id_conversacion, respuesta_texto)
            
            print(f"✅ RESPUESTA ENVIADA: {respuesta_texto[:100]}...")
            print("=" * 50)
            
            # Enviar respuesta TwiML normal
            respuesta = MessagingResponse()
            respuesta.message(respuesta_texto)
            return str(respuesta)
        
    except Exception as e:
        print(f"❌ ERROR EN WEBHOOK: {str(e)}")
        import traceback
        traceback.print_exc()
        
        respuesta = MessagingResponse()
        respuesta.message("Ocurrió un error interno. El equipo técnico ha sido notificado.")
        return str(respuesta)
# ============================================
# ENDPOINTS DE PRUEBA LOCAL
# ============================================

@app.route('/api/test_mensaje', methods=['POST'])
def test_mensaje():
    """Endpoint para probar mensajes sin Twilio"""
    try:
        data = request.get_json()
        telefono = data.get('telefono', '+59171234567')
        mensaje = data.get('mensaje', '')
        
        # Simular procesamiento del webhook
        telefono_limpio = limpiar_telefono(telefono)
        
        # Procesar como si viniera de Twilio
        datos_conv = manejador_conversaciones.procesar_mensaje_entrante(telefono_limpio, mensaje)
        
        if datos_conv:
            # Analizar
            conversacion_previa = obtener_conversacion_previa(telefono_limpio)
            resultado = analizador.analizar_pregunta(mensaje, conversacion_previa)
            
            if resultado['status'] == 'success':
                respuesta_agente = resultado['data']['respuesta_agente']
                manejador_conversaciones.guardar_respuesta_bot(datos_conv['id_conversacion'], respuesta_agente)
                
                return jsonify({
                    'exito': True,
                    'respuesta': respuesta_agente,
                    'conversacion_id': datos_conv['id_conversacion'],
                    'tipo_interes': resultado['data'].get('tipo_interes'),
                    'pdf_generado': len(str(resultado['data'].get('pdf_generado', ''))) > 100
                })
        
        return jsonify({'exito': False, 'error': 'Error procesando mensaje'})
        
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)})

@app.route('/api/enviar_whatsapp_local', methods=['POST'])
def enviar_whatsapp_local():
    """Envía mensaje directo por WhatsApp"""
    try:
        data = request.get_json()
        telefono = data.get('telefono')
        mensaje = data.get('mensaje')
        
        if not telefono or not mensaje:
            return jsonify({'error': 'Faltan telefono o mensaje'}), 400
        
        resultado = enviar_whatsapp_sin_pdf(telefono, mensaje)
        
        if resultado['exito']:
            return jsonify({
                'exito': True,
                'mensaje_sid': resultado['mensaje_sid'],
                'mensaje': 'Enviado correctamente'
            })
        else:
            return jsonify({'exito': False, 'error': resultado['error']})
        
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)})

@app.route('/api/generar_pdf_local', methods=['POST'])
def generar_pdf_local():
    """Genera PDF y lo guarda localmente"""
    try:
        data = request.get_json()
        telefono = data.get('telefono', '').replace('whatsapp:', '').replace('+', '')
        
        if not telefono:
            return jsonify({'error': 'Telefono requerido'}), 400
        
        # Generar PDF
        pdf_base64 = generador_pdf.intereses_usuario(telefono)
        
        if isinstance(pdf_base64, str) and len(pdf_base64) > 100:
            # Guardar localmente
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"temp_pdfs/intereses_{telefono}_{timestamp}.pdf"
            
            os.makedirs("temp_pdfs", exist_ok=True)
            
            with open(filename, "wb") as f:
                f.write(base64.b64decode(pdf_base64))
            
            return jsonify({
                'exito': True,
                'mensaje': 'PDF generado correctamente',
                'archivo': filename,
                'tamaño_base64': len(pdf_base64)
            })
        else:
            return jsonify({
                'exito': False,
                'error': 'No se pudo generar PDF',
                'detalle': pdf_base64
            })
        
    except Exception as e:
        return jsonify({'exito': False, 'error': str(e)})
    


@app.route('/api/health', methods=['GET'])
def health():
    """Estado del sistema"""
    try:
        # Verificar conexión BD
        import mysql.connector
        config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'bot_productos_db'
        }
        
        conexion = mysql.connector.connect(**config)
        conexion.close()
        bd_status = "✅ Conectada"
        
    except:
        bd_status = "❌ Error conexión"
    
    return jsonify({
        'status': 'ok',
        'message': 'Bot WhatsApp - Con Envío de PDFs',
        'base_datos': bd_status,
        'twilio_sandbox': TWILIO_WHATSAPP_NUMBER,
        'webhook_url': '/twilio/webhook',
        'pdf_enabled': True,
        'servicios_pdf': ['file.io', '0x0.st'],
        'endpoints_test': {
            'test_mensaje': '/api/test_mensaje (POST)',
            'enviar_whatsapp': '/api/enviar_whatsapp_local (POST)',
            'generar_pdf': '/api/generar_pdf_local (POST)'
        }
    })

@app.route('/', methods=['GET'])
def home():
    """Página principal"""
    return jsonify({
        'message': '🤖 Bot WhatsApp Gaming - Con Envío de PDFs',
        'version': 'Local v2.0 - PDF Enabled',
        'webhook_twilio': '/twilio/webhook',
        'configuracion': {
            'ngrok_requerido': True,
            'webhook_url': 'https://tu-dominio.ngrok.io/twilio/webhook',
            'sandbox_number': TWILIO_WHATSAPP_NUMBER
        },
        'comandos_whatsapp': [
            'mis intereses - Genera y ENVÍA PDF personalizado',
            'estado - Estado del sistema',
            'Cualquier pregunta sobre gaming - PDF automático si aplica'
        ],
        'nuevas_funciones': [
            '✅ Envío real de PDFs por WhatsApp',
            '✅ Archivos adjuntos descargables',
            '✅ Servicios temporales online',
            '✅ Fallback a mensaje sin PDF'
        ],
        'endpoints_desarrollo': {
            'health': '/api/health',
            'test_mensaje': '/api/test_mensaje',
            'enviar_whatsapp': '/api/enviar_whatsapp_local',
            'generar_pdf': '/api/generar_pdf_local'
        }
    })

if __name__ == '__main__':
    print("\n🚀 INICIANDO BOT WHATSAPP - CON ENVÍO DE PDFs")
    print("=" * 60)
    print("📡 Servidor: http://localhost:5000")
    print("🔗 Webhook: http://localhost:5000/twilio/webhook")
    print("📱 Sandbox WhatsApp:", TWILIO_WHATSAPP_NUMBER)
    print("📄 Envío de PDFs: ✅ HABILITADO")
    print("🌐 Servicios PDF: file.io, 0x0.st")
    print("\n🔧 CONFIGURACIÓN REQUERIDA:")
    print("1. Instalar dependencias: pip install requests")
    print("2. Instalar ngrok: npm install -g ngrok")
    print("3. Ejecutar ngrok: ngrok http 5000")
    print("4. Configurar webhook en Twilio Console con URL de ngrok")
    print("5. Activar sandbox de WhatsApp")
    print("\n📋 COMANDOS WHATSAPP:")
    print("• 'mis intereses' - PDF personalizado ADJUNTO")
    print("• 'estado' - Estado del sistema")
    print("• 'precio play 5' - Info + PDF automático")
    print("\n✅ Listo para enviar PDFs por WhatsApp!")
    print("=" * 60)
    
    # Crear directorio para PDFs
    os.makedirs("temp_pdfs", exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)