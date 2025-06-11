from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from analizador import AnalizadorContexto
# from generador_intereses import GeneradorIntereses
# from generador_imagen import GeneradorImagen
# from twilio.rest import Client
# from twilio.twiml.messaging_response import MessagingResponse
# from manejador_conversaciones import ManejadorConversaciones
from entrenamiento_fino import EntrenamientoFino
import os
import base64
import tempfile
import mysql.connector
from generar_pdf import GeneradorPDF

# Crear la aplicación Flask
app = Flask(__name__)
CORS(app)



# Instanciar módulos personalizados
entrenamiento_fino = EntrenamientoFino()
generador_pdf = GeneradorPDF(entrenamiento_fino)
analizador = AnalizadorContexto(entrenamiento_fino, generador_pdf)
# generador_intereses = GeneradorIntereses()
# generador_imagen = GeneradorImagen()
# manejador_conversaciones = ManejadorConversaciones()

# ENDPOINTS NUEVOS
@app.route('/api/analizar_pregunta', methods=['POST'])
def analizar_pregunta():
    """
    NUEVO ENDPOINT: Analiza pregunta con contexto de conversación
    """
    try:
        data = request.get_json()
        if not data or 'pregunta' not in data or 'conversacion' not in data:
            return jsonify({'error': 'Debes enviar "pregunta" y "conversacion" en el body'}), 400
        
        pregunta = data['pregunta']
        conversacion = data['conversacion']
        
        if not pregunta.strip():
            return jsonify({'error': 'La pregunta no puede estar vacía'}), 400
        
        respuesta = analizador.analizar_pregunta(pregunta, conversacion)
        return jsonify(respuesta)
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor', 'detalle': str(e)}), 500

@app.route('/api/generar_pdf_intereses', methods=['POST'])
def generar_pdf_intereses():
    """
    NUEVO ENDPOINT: Genera PDF de intereses del usuario
    """
    try:
        data = request.get_json()
        if not data or 'numero_telefono' not in data:
            return jsonify({'error': 'Debes enviar "numero_telefono" en el body'}), 400
        
        numero_telefono = data['numero_telefono'].replace('whatsapp:', '').replace('+', '').replace(' ', '')
        resultado_pdf = generador_pdf.intereses_usuario(numero_telefono)
        
        if isinstance(resultado_pdf, str) and resultado_pdf.startswith("Error"):
            return jsonify({'estado': 'error', 'mensaje': resultado_pdf}), 400
        
        return jsonify({
            'estado': 'exito',
            'mensaje': 'PDF generado correctamente',
            'pdf_base64': resultado_pdf,
            'numero_telefono': numero_telefono
        })
    except Exception as e:
        return jsonify({'error': 'Error interno del servidor', 'detalle': str(e)}), 500


# @app.route('/api/verificar_contexto', methods=['POST'])
# def consulta():
#     try:
#         data = request.get_json()
#         if not data or 'pregunta' not in data:
#             return jsonify({'error': 'Debes enviar una pregunta en el campo "pregunta"'}), 400

#         pregunta = data['pregunta']
#         if not pregunta.strip():
#             return jsonify({'error': 'La pregunta no puede estar vacía'}), 400

#         respuesta = analizador.analizar_pregunta(pregunta)
#         return jsonify(respuesta)
#     except Exception as e:
#         print(f"Error en la consulta: {str(e)}")
#         return jsonify({'error': 'Error interno del servidor', 'detalle': str(e)}), 500

# @app.route('/api/generador_intereses', methods=['POST'])
# def generar_intereses():
#     try:
#         data = request.get_json()
#         if not data or 'usuario_telefono' not in data or 'conversacion' not in data:
#             return jsonify({'estado': 'error', 'mensaje': 'Debes enviar usuario_telefono y conversacion'}), 400

#         usuario_telefono = data['usuario_telefono']
#         tipo_conversacion = data['conversacion']
#         mensaje_usuario = data.get('mensaje', None)

#         if not usuario_telefono.strip() or not tipo_conversacion.strip():
#             return jsonify({'estado': 'error', 'mensaje': 'Los campos no pueden estar vacíos'}), 400

#         if not (tipo_conversacion.startswith('inicial_') or tipo_conversacion.startswith('final_') or tipo_conversacion == 'chat_auto'):
#             return jsonify({'estado': 'error', 'mensaje': 'Formato de conversación inválido. Use inicial_N, final_N o chat_auto'}), 400

#         resultado = generador_intereses.procesar_intereses_cliente(
#             usuario_telefono, 
#             tipo_conversacion, 
#             mensaje_usuario
#         )
#         return jsonify(resultado)
#     except Exception as e:
#         print(f"Error en generador de intereses: {str(e)}")
#         return jsonify({'estado': 'error', 'mensaje': 'Proceso incorrecto', 'detalle': str(e)}), 500

# @app.route('/api/generar_imagen', methods=['POST'])
# def generar_imagen_personalizada():
#     """
#     Genera imagen de intereses con opción de última conversación o todos
#     """
#     try:
#         data = request.get_json()
#         if not data or 'usuario_telefono' not in data:
#             return jsonify({'error': 'Debes enviar usuario_telefono'}), 400

#         usuario_telefono = data['usuario_telefono']
#         solo_ultima_conversacion = data.get('solo_ultima_conversacion', True)  # Por defecto solo última
        
#         if not usuario_telefono.strip():
#             return jsonify({'error': 'El usuario_telefono no puede estar vacío'}), 400

#         resultado = generador_imagen.generar_imagen_cliente(
#             usuario_telefono, 
#             solo_ultima_conversacion=solo_ultima_conversacion
#         )
#         return jsonify(resultado)
#     except Exception as e:
#         print(f"Error en generador de imagen: {str(e)}")
#         return jsonify({'error': 'Error interno del servidor', 'detalle': str(e)}), 500
# def cerrar_conversacion():
#     """
#     Endpoint para cerrar una conversación específica
#     """
#     try:
#         data = request.get_json()
#         telefono = data.get('telefono')
        
#         if not telefono:
#             return jsonify({'error': 'Debes enviar el número de teléfono'}), 400
        
#         # Limpiar teléfono
#         telefono_limpio = telefono.replace('whatsapp:', '').replace('+', '')
        
#         # Obtener cliente
#         id_cliente = manejador_conversaciones.obtener_o_crear_cliente(telefono_limpio)
        
#         if not id_cliente:
#             return jsonify({'error': 'Cliente no encontrado'}), 404
        
#         # Obtener conversación activa
#         id_conversacion = manejador_conversaciones.obtener_conversacion_activa(id_cliente)
        
#         if id_conversacion:
#             exito = manejador_conversaciones.cerrar_conversacion(id_conversacion)
#             if exito:
#                 return jsonify({
#                     'estado': 'exito',
#                     'mensaje': 'Conversación cerrada correctamente',
#                     'id_conversacion': id_conversacion
#                 })
        
#         return jsonify({
#             'estado': 'info',
#             'mensaje': 'No hay conversación activa para cerrar'
#         })
        
#     except Exception as e:
#         print(f"Error cerrando conversación: {str(e)}")
#         return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500
    
# Agregar este endpoint en app.py

# @app.route('/api/cerrar_conversaciones_inactivas', methods=['POST'])
# def cerrar_conversaciones_inactivas():
#     """
#     Endpoint para cerrar todas las conversaciones inactivas (más de 5 minutos sin actividad)
#     Útil para ejecutar periódicamente con un cron job
#     """
#     try:
#         conexion = mysql.connector.connect(**manejador_conversaciones.db_config)
#         cursor = conexion.cursor()
        
#         # Cerrar todas las conversaciones activas con más de 5 minutos de inactividad
#         cursor.execute("""
#             UPDATE conversacion 
#             SET estado = 'finalizada',
#                 fecha_fin = NOW()
#             WHERE estado = 'activa'
#             AND TIMESTAMPDIFF(MINUTE, fecha_ultima_actividad, NOW()) > 5
#         """)
        
#         conversaciones_cerradas = cursor.rowcount
#         conexion.commit()
#         conexion.close()
        
#         print(f"✅ Se cerraron {conversaciones_cerradas} conversaciones inactivas")
        
#         return jsonify({
#             'estado': 'exito',
#             'mensaje': f'Se cerraron {conversaciones_cerradas} conversaciones inactivas',
#             'conversaciones_cerradas': conversaciones_cerradas
#         })
        
#     except Exception as e:
#         print(f"Error cerrando conversaciones inactivas: {str(e)}")
#         return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500

# # También puedes agregar un endpoint para ver el estado de las conversaciones
# @app.route('/api/estado_conversaciones', methods=['GET'])
# def estado_conversaciones():
#     """
#     Endpoint para ver el estado de las conversaciones activas
#     """
#     try:
#         conexion = mysql.connector.connect(**manejador_conversaciones.db_config)
#         cursor = conexion.cursor(dictionary=True)
        
#         # Obtener conversaciones activas
#         cursor.execute("""
#             SELECT 
#                 c.id_conversacion,
#                 cl.telefono,
#                 c.fecha_inicio,
#                 c.fecha_ultima_actividad,
#                 TIMESTAMPDIFF(MINUTE, c.fecha_ultima_actividad, NOW()) as minutos_inactiva,
#                 COUNT(m.id_mensaje) as total_mensajes
#             FROM conversacion c
#             JOIN cliente cl ON c.id_cliente = cl.id_cliente
#             LEFT JOIN mensaje m ON c.id_conversacion = m.id_conversacion
#             WHERE c.estado = 'activa'
#             GROUP BY c.id_conversacion
#             ORDER BY c.fecha_ultima_actividad DESC
#         """)
        
#         conversaciones_activas = cursor.fetchall()
        
#         # Obtener estadísticas generales
#         cursor.execute("""
#             SELECT 
#                 COUNT(CASE WHEN estado = 'activa' THEN 1 END) as activas,
#                 COUNT(CASE WHEN estado = 'finalizada' THEN 1 END) as finalizadas,
#                 COUNT(*) as total
#             FROM conversacion
#             WHERE DATE(fecha_inicio) = CURDATE()
#         """)
        
#         estadisticas = cursor.fetchone()
#         conexion.close()
        
#         return jsonify({
#             'estado': 'exito',
#             'conversaciones_activas': conversaciones_activas,
#             'estadisticas_hoy': estadisticas
#         })
        
#     except Exception as e:
#         print(f"Error obteniendo estado de conversaciones: {str(e)}")
#         return jsonify({'error': 'Error interno', 'detalle': str(e)}), 500

# @app.route('/api/generar_y_enviar_imagen', methods=['POST'])
# def generar_y_enviar_imagen():
#     """
#     Endpoint principal que genera la imagen de intereses y la envía por WhatsApp
#     Por defecto genera imagen solo con intereses de la última conversación
#     """
#     try:
#         data = request.get_json()
#         telefono = data.get('telefono')
#         mensaje_adicional = data.get('mensaje_adicional', '')
#         solo_ultima_conversacion = data.get('solo_ultima_conversacion', True)  # Por defecto solo última

#         if not telefono:
#             return jsonify({
#                 'estado': 'error', 
#                 'mensaje': 'Debes enviar el número de teléfono'
#             }), 400

#         # Limpiar el número de teléfono
#         telefono_limpio = telefono.replace('whatsapp:', '').replace('+', '').replace(' ', '')
        
#         print(f"🚀 Generando imagen de intereses para: {telefono_limpio}")
#         print(f"📋 Modo: {'Última conversación' if solo_ultima_conversacion else 'Todos los intereses'}")

#         # 1. Generar la imagen de intereses
#         resultado_imagen = generador_imagen.generar_imagen_cliente(
#             telefono_limpio,
#             solo_ultima_conversacion=solo_ultima_conversacion
#         )
        
#         if 'estado' in resultado_imagen and resultado_imagen['estado'] == 'error':
#             return jsonify({
#                 'estado': 'error',
#                 'mensaje': 'Error al generar imagen',
#                 'detalle': resultado_imagen.get('mensaje', 'Error desconocido')
#             }), 500

#         # Verificar que se generó correctamente la imagen
#         if 'urlImagen' not in resultado_imagen:
#             return jsonify({
#                 'estado': 'error',
#                 'mensaje': 'No se pudo generar la imagen de intereses'
#             }), 500

#         url_imagen = resultado_imagen['urlImagen']
#         print(f"✅ Imagen generada exitosamente: {url_imagen}")

#         # 2. Enviar por WhatsApp
#         try:
#             client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            
#             # Preparar mensaje según el modo
#             if not mensaje_adicional:
#                 if solo_ultima_conversacion:
#                     mensaje_adicional = "🎯 Aquí están los productos que consultaste en nuestra última conversación:"
#                 else:
#                     mensaje_adicional = "🎯 Aquí tienes tu lista personalizada de productos que podrían interesarte:"
            
#             # Enviar mensaje con imagen
#             message = client.messages.create(
#                 from_=TWILIO_WHATSAPP_NUMBER,
#                 body=mensaje_adicional,
#                 media_url=[url_imagen],
#                 to=f'whatsapp:{telefono}'
#             )

#             print(f"📱 Mensaje enviado exitosamente. SID: {message.sid}")

#             return jsonify({
#                 'estado': 'exito',
#                 'mensaje': 'Imagen generada y enviada correctamente',
#                 'mensaje_sid': message.sid,
#                 'url_imagen': url_imagen,
#                 'telefono_destino': telefono,
#                 'modo': 'ultima_conversacion' if solo_ultima_conversacion else 'todos_intereses'
#             })

#         except Exception as e_twilio:
#             print(f"❌ Error enviando por Twilio: {e_twilio}")
#             return jsonify({
#                 'estado': 'error_envio',
#                 'mensaje': 'Imagen generada pero error al enviar',
#                 'url_imagen': url_imagen,
#                 'detalle_error': str(e_twilio)
#             }), 500

#     except Exception as e:
#         print(f"❌ Error general en generar_y_enviar_imagen: {str(e)}")
#         return jsonify({
#             'estado': 'error',
#             'mensaje': 'Error interno del servidor',
#             'detalle': str(e)
#         }), 500

# @app.route('/api/enviar_imagen_intereses', methods=['POST'])
# def enviar_imagen_intereses():
#     """
#     Endpoint que envía solo la imagen (asumiendo que ya existe en Cloudinary)
#     Requiere:
#     - 'telefono': número de teléfono del cliente
#     - 'url_imagen': URL de la imagen a enviar
#     - 'mensaje': mensaje opcional
#     """
#     try:
#         data = request.get_json()
#         telefono = data.get('telefono')
#         url_imagen = data.get('url_imagen')
#         mensaje = data.get('mensaje', '🎯 Tu lista personalizada de productos:')

#         if not telefono or not url_imagen:
#             return jsonify({
#                 'estado': 'error',
#                 'mensaje': 'Faltan parámetros: telefono y url_imagen'
#             }), 400

#         client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
#         message = client.messages.create(
#             from_=TWILIO_WHATSAPP_NUMBER,
#             body=mensaje,
#             media_url=[url_imagen],
#             to=f'whatsapp:{telefono}'
#         )

#         return jsonify({
#             'estado': 'exito',
#             'mensaje': 'Imagen enviada correctamente',
#             'mensaje_sid': message.sid
#         })

#     except Exception as e:
#         print(f"Error enviando imagen: {str(e)}")
#         return jsonify({
#             'estado': 'error',
#             'detalle': str(e)
#         }), 500

# @app.route('/api/comando_imagen', methods=['POST'])
# def comando_imagen():
#     """
#     Endpoint especial para comandos automáticos
#     Detecta si un usuario escribió algo como "imagen", "lista", "intereses"
#     y automáticamente genera y envía la imagen
#     """
#     try:
#         data = request.get_json()
#         telefono = data.get('telefono')
#         mensaje_usuario = data.get('mensaje', '').lower().strip()

#         if not telefono:
#             return jsonify({'error': 'Debes enviar el número de teléfono'}), 400

#         # Palabras clave que activan la generación de imagen
#         palabras_clave = ['imagen', 'lista', 'intereses', 'productos', 'recomendaciones', 'catálogo']
        
#         # Verificar si el mensaje contiene palabras clave
#         activar_imagen = any(palabra in mensaje_usuario for palabra in palabras_clave)
        
#         if not activar_imagen:
#             return jsonify({
#                 'estado': 'no_activado',
#                 'mensaje': 'El mensaje no activó la generación de imagen'
#             })

#         # Generar y enviar imagen
#         telefono_limpio = telefono.replace('whatsapp:', '').replace('+', '')
        
#         resultado_imagen = generador_imagen.generar_imagen_cliente(telefono_limpio)
        
#         if 'estado' in resultado_imagen and resultado_imagen['estado'] == 'error':
#             return jsonify({
#                 'estado': 'error',
#                 'mensaje': resultado_imagen.get('mensaje', 'Error al generar imagen')
#             })

#         if 'urlImagen' not in resultado_imagen:
#             return jsonify({
#                 'estado': 'error',
#                 'mensaje': 'No se pudo generar la imagen'
#             })

#         # Enviar por WhatsApp
#         client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
#         message = client.messages.create(
#             from_=TWILIO_WHATSAPP_NUMBER,
#             body="🎯 Aquí tienes tu lista personalizada de productos basada en tus intereses:",
#             media_url=[resultado_imagen['urlImagen']],
#             to=f'whatsapp:{telefono}'
#         )

#         return jsonify({
#             'estado': 'exito',
#             'mensaje': 'Imagen generada y enviada automáticamente',
#             'mensaje_sid': message.sid,
#             'activado_por': mensaje_usuario
#         })

#     except Exception as e:
#         print(f"Error en comando_imagen: {str(e)}")
#         return jsonify({
#             'estado': 'error',
#             'detalle': str(e)
#         }), 500

# @app.route('/api/enviar_whatsapp', methods=['POST'])
# def enviar_whatsapp():
#     """
#     Envía un mensaje de WhatsApp usando Twilio (sin imagen)
#     """
#     try:
#         data = request.get_json()
#         telefono = data.get('telefono')
#         mensaje = data.get('mensaje')

#         if not telefono or not mensaje:
#             return jsonify({'estado': 'error', 'mensaje': 'Faltan parámetros: telefono y mensaje'}), 400

#         client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
#         message = client.messages.create(
#             from_=TWILIO_WHATSAPP_NUMBER,
#             body=mensaje,
#             to=f'whatsapp:{telefono}'
#         )

#         return jsonify({'estado': 'ok', 'mensaje_sid': message.sid, 'mensaje': 'Mensaje enviado correctamente'})
#     except Exception as e:
#         print(f"Error enviando WhatsApp: {str(e)}")
#         return jsonify({'estado': 'error', 'detalle': str(e)}), 500

# @app.route('/api/health', methods=['GET'])
# def health():
#     return jsonify({
#         'status': 'ok',
#         'message': 'Servidor funcionando correctamente',
#         'modulos': {
#             'analizador': 'activo',
#             'generador_intereses': 'activo',
#             'generador_imagen': 'activo',
#             'twilio_multimedia': 'activo'
#         }
#     })

# @app.route('/twilio/webhook', methods=['POST'])
# def webhook_twilio():
#     try:
#         mensaje_entrante = request.form.get('Body', '').strip()
#         numero_remitente = request.form.get('From')  # Ej: whatsapp:+59171234567
        
#         print(f"📥 Mensaje recibido de {numero_remitente}: {mensaje_entrante}")
        
#         # Limpiar número de teléfono
#         telefono_limpio = numero_remitente.replace("whatsapp:", "").replace("+", "")
        
#         # NUEVO: Procesar y guardar mensaje entrante
#         datos_conversacion = manejador_conversaciones.procesar_mensaje_entrante(
#             telefono_limpio, 
#             mensaje_entrante
#         )
        
#         if not datos_conversacion:
#             print("❌ Error al procesar mensaje entrante")
#             respuesta = MessagingResponse()
#             respuesta.message("Lo siento, hubo un error al procesar tu mensaje.")
#             return str(respuesta)
        
#         id_conversacion = datos_conversacion['id_conversacion']
#         print(f"📝 Conversación ID: {id_conversacion}")
        
#         # Verificar si es un comando para generar imagen
#         comandos_imagen = ['imagen', 'lista', 'intereses', 'productos', 'recomendaciones']
#         es_comando_imagen = any(cmd in mensaje_entrante.lower() for cmd in comandos_imagen)
        
#         if es_comando_imagen:
#             print("🖼️ Comando de imagen detectado")
#             try:
#                 # Generar imagen SOLO con última conversación
#                 resultado_imagen = generador_imagen.generar_imagen_cliente(
#                     telefono_limpio,
#                     solo_ultima_conversacion=True  # Solo última conversación
#                 )
                
#                 if 'urlImagen' in resultado_imagen:
#                     # Enviar imagen como respuesta
#                     client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    
#                     mensaje_imagen = "🎯 Aquí están los productos que consultaste en esta conversación:"
                    
#                     # Guardar respuesta del bot en la BD
#                     manejador_conversaciones.guardar_respuesta_bot(
#                         id_conversacion, 
#                         f"{mensaje_imagen} [Imagen enviada: {resultado_imagen['urlImagen']}]"
#                     )
                    
#                     client.messages.create(
#                         from_=TWILIO_WHATSAPP_NUMBER,
#                         body=mensaje_imagen,
#                         media_url=[resultado_imagen['urlImagen']],
#                         to=numero_remitente
#                     )
                    
#                     print("✅ Imagen enviada como respuesta automática")
#                     return "OK", 200
#                 else:
#                     print("❌ Error generando imagen, enviando respuesta de texto")
#                     texto_error = "Lo siento, no pude generar tu lista en este momento."
                    
#                     # Guardar respuesta de error
#                     manejador_conversaciones.guardar_respuesta_bot(id_conversacion, texto_error)
                    
#                     respuesta = MessagingResponse()
#                     respuesta.message(texto_error)
#                     return str(respuesta)
                    
#             except Exception as e_img:
#                 print(f"⚠️ Error procesando comando de imagen: {e_img}")
        
#         # Analizar la pregunta con el contexto
#         respuesta_contexto = analizador.analizar_pregunta(mensaje_entrante)
#         texto_respuesta = respuesta_contexto.get('respuesta', 'Lo siento, no entendí tu mensaje.')
        
#         # NUEVO: Guardar respuesta del bot
#         manejador_conversaciones.guardar_respuesta_bot(id_conversacion, texto_respuesta)
        
#         # Guardar intereses (ahora con el mensaje del usuario)
#         try:
#             resultado_intereses = generador_intereses.procesar_intereses_cliente(
#                 telefono_limpio, 
#                 "chat_auto", 
#                 mensaje_entrante
#             )
#             print("💾 Resultado del procesamiento de intereses:", resultado_intereses)
#         except Exception as ei:
#             print(f"⚠️ No se pudo procesar intereses: {ei}")
        
#         # Responder por WhatsApp
#         respuesta = MessagingResponse()
#         respuesta.message(texto_respuesta)
#         return str(respuesta)
        
#     except Exception as e:
#         print(f"❌ Error en webhook de Twilio: {str(e)}")
#         return "Error", 500

# @app.route('/', methods=['GET'])
# def home():
#     return jsonify({
#         'message': 'API de Análisis de Contexto y Generación de Contenido',
#         'version': '3.0',
#         'endpoints': {
#             'consulta_productos': '/api/verificar_contexto (POST)',
#             'generar_intereses': '/api/generador_intereses (POST)',
#             'generar_imagen': '/api/generar_imagen (POST)',
#             'generar_y_enviar_imagen': '/api/generar_y_enviar_imagen (POST)',
#             'enviar_imagen_intereses': '/api/enviar_imagen_intereses (POST)',
#             'comando_imagen': '/api/comando_imagen (POST)',
#             'enviar_whatsapp': '/api/enviar_whatsapp (POST)',
#             'health': '/api/health (GET)'
#         }
#     })

if __name__ == '__main__':
    print("🚀 Iniciando servidor Flask...")
    print("📡 Servidor disponible en: http://localhost:5000")
    print("🔗 Endpoints disponibles:")
    print("   • POST /api/verificar_contexto - Consultas de productos")
    print("   • POST /api/generador_intereses - Análisis de intereses")
    print("   • POST /api/generar_imagen - Generación de imágenes")
    print("   • POST /api/generar_y_enviar_imagen - Generar y enviar imagen por WhatsApp")
    print("   • POST /api/enviar_imagen_intereses - Enviar imagen existente")
    print("   • POST /api/comando_imagen - Comando automático de imagen")
    print("   • POST /api/enviar_whatsapp - Enviar mensajes por WhatsApp")
    print("   • GET  /api/health - Estado del servidor")
    app.run(debug=False, host='0.0.0.0', port=5000)