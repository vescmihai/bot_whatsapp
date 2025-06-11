import mysql.connector
import json
import os
import requests
from datetime import datetime
from entrenamiento_fino import EntrenamientoFino
from generar_pdf import GeneradorPDF
import base64 

# class AnalizadorContexto:
#     def __init__(self):
#         self.entrenamiento_fino = EntrenamientoFino()
#         self.generar_pdf = GeneradorPDF()
class AnalizadorContexto:
    def __init__(self, entrenamiento_fino=None, generador_pdf=None):
        # Usar instancias pasadas o crear nuevas
        self.entrenamiento_fino = entrenamiento_fino 
        self.generar_pdf = generador_pdf
        # self.entrenamiento_fino = entrenamiento_fino if entrenamiento_fino else EntrenamientoFino()
        # self.generar_pdf = generador_pdf if generador_pdf else GeneradorPDF(self.entrenamiento_fino)
    
    def analizar_pregunta(self, pregunta, conversacion):
        try:
            # Resumir la conversacion previa para el uso del contexto
            # del modelo y tenga idea de la conversación previa pasada
            conversacion_resumida = self.entrenamiento_fino.obtener_informacion_modelo(
                """
                    Eres un asistente especializado en resumir conversaciones de ventas de productos gamer.
                    Tu tarea es analizar el historial de conversación y crear un resumen BREVE y DIRECTO que capture únicamente la información comercial relevante.
                    INSTRUCCIONES:
                    - Resume SOLO información útil para ventas: productos mencionados, presupuesto, necesidades específicas, preferencias
                    - Elimina saludos, cortesías y conversación casual
                    - Máximo 2-3 líneas por intercambio importante
                    - Enfócate en: qué busca el cliente, qué se recomendó, decisiones tomadas
                    Responde con un párrafo corto y directo con los puntos clave de la conversación.
                """,
                 conversacion
            )
            
            # Obtener el resumen para usarlo en el contexto del vendedor
            resumen_conversacion = ""
            if conversacion_resumida['status'] == 'success':
                resumen_conversacion = conversacion_resumida['data']
            else:
                resumen_conversacion = "Sin conversación previa"
            
            # Obtener respuesta del agente vendedor con contexto completo
            datos_contexto = self.entrenamiento_fino.obtener_informacion_modelo(
                f"""
                Eres un vendedor HUMANO especialista en productos gamer trabajando en una tienda física. Tu comunicación será enviada por WhatsApp, así que usa formato elegante con saltos de línea apropiados.
                
                PERSONALIDAD Y ESTILO:
                - Inicio: Formal y profesional
                - Progresivamente: Más amigable y cercano conforme avanza la conversación  
                - Siempre respetuoso y experto en el rubro
                - Nunca reveles que eres IA - comportarte 100% como vendedor humano
                - Respuestas directas, informativas pero no muy largas
                - Usa emojis ocasionalmente para WhatsApp (sin exagerar)
                
                INFORMACIÓN DE NUESTRA SUCURSAL Y STOCK:
                - Enfócate en productos gaming, colecciones y promociones de nuestra tienda
                - Si preguntan por productos sin stock: responde naturalmente sobre disponibilidad futura o alternativas
                - Si mencionan colección/promoción que NO tenemos: sugiere naturalmente las opciones disponibles
                - Considera el stock disponible al hacer recomendaciones, pero de forma conversacional
                
                - Si preguntan por productos sin stock: NUNCA digas solo "no tenemos" - TRANSFORMA en oportunidad
                - Si SIN STOCK: No pierdas la venta, transforma la situación
                * Ofrece información completa del producto (precio, specs, etc.)
                * Invita INMEDIATAMENTE a personarse en la tienda para informarle cuando lleguen nuevos ejemplares
                * Apartarle uno cuando llegue o mostrarle alternativas similares disponibles
                * Mantén el interés: "Te puedo avisar apenas llegue" / "Podemos apartarte uno"
                
                MANEJO DE PDFs INTELIGENTE:
                - Si el cliente muestra interés en una colección específica disponible, menciona naturalmente que tienes información detallada disponible
                - Si el cliente muestra interés en una promoción específica disponible, menciona de forma natural que puedes compartir los detalles completos
                - Si ya enviaste información antes en esta conversación, refiérete a ello de manera natural y conversacional
                - Evita frases roboticas o repetitivas - responde como un vendedor humano real
                
                CONTEXTO DE CONVERSACIÓN PREVIA:
                {resumen_conversacion}
                
                FORMATO DE RESPUESTA OBLIGATORIO (JSON válido):
                SOLO incluye "respuesta_agente" + UNO de estos campos según corresponda:
                
                OPCIÓN 1 - Si es colección:
                {{
                    "respuesta_agente": "Tu respuesta como vendedor humano aquí",
                    "interes_coleccion": "nombre_coleccion"
                }}
                
                OPCIÓN 2 - Si es promoción:
                {{
                    "respuesta_agente": "Tu respuesta como vendedor humano aquí", 
                    "interes_promocion": "nombre_promocion"
                }}
                
                OPCIÓN 3 - Si no está claro:
                {{
                    "respuesta_agente": "Tu respuesta como vendedor humano aquí",
                    "interes": "indefinido"
                }}
                
                REGLAS IMPORTANTES PARA CLASIFICAR INTERÉS:
                - Si el cliente muestra interés en una COLECCIÓN específica de productos: usa SOLO "interes_coleccion"
                - Si el cliente muestra interés en una PROMOCIÓN específica: usa SOLO "interes_promocion"  
                - Si NO está claro qué busca o es conversación general: usa SOLO "interes": "indefinido"
                - NUNCA combines campos, solo UNO por respuesta
                - Analiza la pregunta actual junto con el contexto de conversación previa para determinar el interés real
                - Verifica que la colección/promoción exista en nuestra base de datos antes de clasificarla
                
                EJEMPLOS DE RESPUESTAS NATURALES:
                Ejemplo 1: {{"respuesta_agente": "¡Excelente elección! Nuestras laptops gaming son increíbles. Te puedo mostrar todo el catálogo completo si gustas", "interes_coleccion": "laptops_gaming"}}
                Ejemplo 2: {{"respuesta_agente": "Perfecto timing! Justo tenemos una promoción genial este mes que te va a encantar", "interes_promocion": "oferta_del_mes"}}
                Ejemplo 3: {{"respuesta_agente": "¡Hola! ¿Qué tipo de setup gaming estás buscando?", "interes": "indefinido"}}
                
                Usa toda la base de conocimiento de productos disponible para dar respuestas precisas y relevantes sobre nuestra sucursal.
                """,
                pregunta
            )
            
            # Obtener la respuesta del agente vendedor con el contexto completo
            if datos_contexto['status'] == 'success':
                respuesta_json = json.loads(datos_contexto['data'])
                respuesta_agente = respuesta_json.get("respuesta_agente", "")
                
                # Determinar qué tipo de interés existe (solo uno debería existir)
                if "interes_coleccion" in respuesta_json and respuesta_json["interes_coleccion"]:
                    tipo_interes = "coleccion"
                    titulo_interes = respuesta_json["interes_coleccion"]
                elif "interes_promocion" in respuesta_json and respuesta_json["interes_promocion"]:
                    tipo_interes = "promocion"
                    titulo_interes = respuesta_json["interes_promocion"]
                elif "interes" in respuesta_json:
                    tipo_interes = "indefinido"
                    titulo_interes = respuesta_json["interes"]
                else:
                    # Fallback por si no viene ninguno
                    tipo_interes = "indefinido"
                    titulo_interes = "indefinido"
                
                # Se procede a evaluar el tipo de interes que se ha detectado
                print(f"Tipo de interés detectado: {tipo_interes} - Valor: {titulo_interes}")
                
                # Generar PDF según el tipo de interés
                pdf_generado = None
                if tipo_interes == "coleccion":
                    # Obtener un pdf de la colección
                    pdf_generado = self.generar_pdf.informacion_coleccion(titulo_interes)
                elif tipo_interes == "promocion":
                    # Obtener un pdf de la promoción
                    pdf_generado = self.generar_pdf.informacion_promocion(titulo_interes)
                else:
                    # No se genera PDF si el interés es indefinido
                    pdf_generado = "No se generará PDF ya que el interés es indefinido"
                
                # Preparar respuesta final para el cliente
                respuesta_enviar_cliente = {
                    "respuesta_agente": respuesta_agente,
                    "pdf_generado": pdf_generado,
                    "tipo_interes": tipo_interes,
                    "titulo_interes": titulo_interes
                }
                
                return {
                    "status": "success",
                    "data": respuesta_enviar_cliente
                }
            
            else:
                return {
                    "status": "error",
                    "message": "Error al obtener respuesta del agente vendedor",
                    "details": datos_contexto
                }
        
        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "message": "Error al parsear JSON de respuesta",
                "details": str(e)
            }
        
        except Exception as e:
            return {
                "status": "error",
                "message": "Error general en análisis de contexto",
                "details": str(e)
            }
        
# def main():
#     print("🎮 Sistema de Ventas Gaming - Test Rápido")
#     print("=" * 50)
    
#     # Crear instancia
#     analizador = AnalizadorContexto()
#     print("✅ Sistema inicializado")
    
#     # Crear carpeta para PDFs si no existe
#     pdf_folder = "pdfs_generados"
#     if not os.path.exists(pdf_folder):
#         os.makedirs(pdf_folder)
#         print(f"📁 Carpeta '{pdf_folder}' creada")
    
#     def guardar_pdf_si_existe(pdf_data, nombre_test):
#         """Función helper para guardar PDFs en base64"""
#         if isinstance(pdf_data, str) and len(pdf_data) > 100:  # Es base64 válido
#             try:
#                 # Decodificar base64
#                 pdf_bytes = base64.b64decode(pdf_data)
                
#                 # Crear nombre de archivo con timestamp
#                 timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#                 filename = f"{pdf_folder}/{nombre_test}_{timestamp}.pdf"
                
#                 # Guardar archivo
#                 with open(filename, "wb") as f:
#                     f.write(pdf_bytes)
                
#                 print(f"📄 PDF guardado: {filename}")
#                 return f"✅ PDF guardado como {filename}"
#             except Exception as e:
#                 print(f"❌ Error guardando PDF: {e}")
#                 return f"❌ Error guardando PDF: {e}"
#         else:
#             return pdf_data  # Devolver el mensaje original si no es base64
    
#     # Ejemplo 1: Consulta inicial
#     print("\n--- Ejemplo 1: Consulta sobre laptops ---")
#     resultado1 = analizador.analizar_pregunta(
#         "Hola, estoy buscando una laptop gaming", 
#         ""
#     )
#     if resultado1['status'] == 'success':
#         print("Respuesta:", resultado1['data']['respuesta_agente'])
#         print("Tipo:", resultado1['data']['tipo_interes'])
#         pdf_result = guardar_pdf_si_existe(resultado1['data']['pdf_generado'], "consulta_laptops")
#         print("PDF:", pdf_result)
#     else:
#         print("Error:", resultado1['message'])
#         print("Detalles:", resultado1.get('details', 'No hay detalles'))
    
#     # Ejemplo 2: Consulta sobre promociones
#     print("\n--- Ejemplo 2: Consulta sobre promociones ---")
#     resultado2 = analizador.analizar_pregunta(
#         "¿Qué promociones tienen este mes?",
#         "Cliente: Hola, estoy buscando una laptop gaming"
#     )
#     if resultado2['status'] == 'success':
#         print("Respuesta:", resultado2['data']['respuesta_agente'])
#         print("Tipo:", resultado2['data']['tipo_interes'])
#         pdf_result = guardar_pdf_si_existe(resultado2['data']['pdf_generado'], "consulta_promociones")
#         print("PDF:", pdf_result)
#     else:
#         print("Error:", resultado2['message'])
#         print("Detalles:", resultado2.get('details', 'No hay detalles'))
    
#     # Ejemplo 3: Interés específico en colección
#     print("\n--- Ejemplo 3: Interés en mouse gaming ---")
#     resultado3 = analizador.analizar_pregunta(
#         "Me interesa ver la colección de mouse gaming",
#         "Cliente: ¿Qué promociones tienen?\nVendedor: Tenemos varias opciones disponibles"
#     )
#     if resultado3['status'] == 'success':
#         print("Respuesta:", resultado3['data']['respuesta_agente'])
#         print("Tipo:", resultado3['data']['tipo_interes'])
#         pdf_result = guardar_pdf_si_existe(resultado3['data']['pdf_generado'], "coleccion_mouse")
#         print("PDF:", pdf_result)
#     else:
#         print("Error:", resultado3['message'])
#         print("Detalles:", resultado3.get('details', 'No hay detalles'))
    
#     # Ejemplo 4: Test específico para forzar generación de PDF
#     print("\n--- Ejemplo 4: Test de colección específica ---")
#     resultado4 = analizador.analizar_pregunta(
#         "Quiero ver toda la información de la colección Consolas & Gaming",
#         ""
#     )
#     if resultado4['status'] == 'success':
#         print("Respuesta:", resultado4['data']['respuesta_agente'])
#         print("Tipo:", resultado4['data']['tipo_interes'])
#         pdf_result = guardar_pdf_si_existe(resultado4['data']['pdf_generado'], "coleccion_consolas")
#         print("PDF:", pdf_result)
#     else:
#         print("Error:", resultado4['message'])
#         print("Detalles:", resultado4.get('details', 'No hay detalles'))
    
#     # Ejemplo 5: Test de promoción específica
#     print("\n--- Ejemplo 5: Test de promoción específica ---")
#     resultado5 = analizador.analizar_pregunta(
#         "Me interesa la promoción Cyber Monday Gaming",
#         ""
#     )
#     if resultado5['status'] == 'success':
#         print("Respuesta:", resultado5['data']['respuesta_agente'])
#         print("Tipo:", resultado5['data']['tipo_interes'])
#         pdf_result = guardar_pdf_si_existe(resultado5['data']['pdf_generado'], "promocion_cyber_monday")
#         print("PDF:", pdf_result)
#     else:
#         print("Error:", resultado5['message'])
#         print("Detalles:", resultado5.get('details', 'No hay detalles'))
    
#     print(f"\n🎯 Test completado!")
#     print(f"📁 Revisa la carpeta '{pdf_folder}' para ver los PDFs generados")

# if __name__ == "__main__":
#     # Ejecutar modo normal
#     main()