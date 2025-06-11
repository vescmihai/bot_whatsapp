import mysql.connector
import json
import requests
from datetime import datetime

class GeneradorIntereses:
    def __init__(self):
        """
        Inicializar el generador de intereses
        Configura la conexión a la base de datos y la API de OpenAI
        """
        # Configuración de la base de datos MySQL
        self.db_config = {
            'host': 'localhost',
            'user': 'root',          # Cambia esto por tu usuario de MySQL
            'password': '',  # Cambia esto por tu contraseña de MySQL
            'database': 'bot_productos_db',
            'charset': 'utf8mb4'
        }
        
        # Clave API de OpenAI
        self.api_key = ""

    def obtener_conversaciones_cliente(self, telefono, tipo_conversacion):
        """
        Obtiene las conversaciones del cliente según el tipo solicitado
        
        Args:
            telefono (str): Número de teléfono del cliente
            tipo_conversacion (str): 'inicial_3' o 'final_3'
        
        Returns:
            list: Lista de mensajes de las conversaciones
        """
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor(dictionary=True)
            
            # Verificar si el cliente existe
            cursor.execute("SELECT id_cliente FROM cliente WHERE telefono = %s", (telefono,))
            cliente = cursor.fetchone()
            
            if not cliente:
                conexion.close()
                return None  # Cliente no existe
            
            id_cliente = cliente['id_cliente']
            
            # Obtener conversaciones según el tipo
            if tipo_conversacion.startswith('inicial'):
                # Extraer número de conversaciones (inicial_3 -> 3)
                numero = int(tipo_conversacion.split('_')[1])
                cursor.execute("""
                    SELECT c.id_conversacion, c.fecha_inicio
                    FROM conversacion c
                    WHERE c.id_cliente = %s
                    ORDER BY c.fecha_inicio ASC
                    LIMIT %s
                """, (id_cliente, numero))
                
            elif tipo_conversacion.startswith('final'):
                # Extraer número de conversaciones (final_3 -> 3)
                numero = int(tipo_conversacion.split('_')[1])
                cursor.execute("""
                    SELECT c.id_conversacion, c.fecha_inicio
                    FROM conversacion c
                    WHERE c.id_cliente = %s
                    ORDER BY c.fecha_inicio DESC
                    LIMIT %s
                """, (id_cliente, numero))
            
            conversaciones = cursor.fetchall()
            
            if not conversaciones:
                conexion.close()
                return []
            
            # Obtener todos los mensajes de estas conversaciones
            ids_conversaciones = [str(conv['id_conversacion']) for conv in conversaciones]
            placeholders = ','.join(['%s'] * len(ids_conversaciones))
            
            cursor.execute(f"""
                SELECT m.contenido, m.emisor, m.fecha_envio, c.fecha_inicio
                FROM mensaje m
                JOIN conversacion c ON m.id_conversacion = c.id_conversacion
                WHERE m.id_conversacion IN ({placeholders})
                ORDER BY c.fecha_inicio, m.fecha_envio
            """, ids_conversaciones)
            
            mensajes = cursor.fetchall()
            conexion.close()
            
            return mensajes
            
        except Exception as e:
            print(f"Error al obtener conversaciones: {e}")
            return []

    def obtener_productos_disponibles(self):
        """
        Obtiene la lista de productos disponibles en la base de datos
        para hacer match con los intereses detectados
        """
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT id_producto, nombre, descripcion
                FROM producto
                WHERE activo = TRUE
                ORDER BY nombre
            """)
            
            productos = cursor.fetchall()
            conexion.close()
            
            return {prod['nombre']: prod['id_producto'] for prod in productos}
            
        except Exception as e:
            print(f"Error al obtener productos: {e}")
            return {}

    def analizar_intereses_con_openai(self, mensajes, productos_disponibles):
        """
        Usa OpenAI para analizar las conversaciones y detectar intereses en productos
        
        Args:
            mensajes (list): Lista de mensajes de las conversaciones
            productos_disponibles (dict): Diccionario de productos {nombre: id}
        
        Returns:
            list: Array de objetos con formato [{"nombre": "producto", "nivel_interes": "alto"}]
        """
        try:
            # Construir el contexto de conversación
            contexto_conversacion = []
            for msg in mensajes:
                emisor = "Cliente" if msg['emisor'] == 'usuario' else "Vendedor"
                contexto_conversacion.append(f"{emisor}: {msg['contenido']}")
            
            conversacion_texto = "\n".join(contexto_conversacion)
            productos_lista = list(productos_disponibles.keys())
            
            # Prompt para OpenAI
            prompt = f"""
PRODUCTOS DISPONIBLES EN LA TIENDA:
{', '.join(productos_lista)}

CONVERSACIÓN DEL CLIENTE:
{conversacion_texto}

INSTRUCCIONES:
1. Analiza la conversación y detecta qué productos mencionó o preguntó el cliente
2. SOLO considera productos que están en la lista de productos disponibles
3. Determina el nivel de interés: "bajo", "medio", "alto"
4. DEBES devolver ÚNICAMENTE un array JSON válido con este formato exacto:
[{{"nombre": "nombre_exacto_del_producto", "nivel_interes": "alto"}}]

REGLAS IMPORTANTES:
- Los nombres deben coincidir EXACTAMENTE con los de la lista de productos disponibles
- Si el cliente preguntó precio o características = "alto"
- Si mencionó o mostró curiosidad = "medio"  
- Si solo lo nombró de pasada = "bajo"
- Si no hay interés en ningún producto, devuelve: []

RESPUESTA (solo JSON):
"""
            
            # Llamada a OpenAI
            endpoint = 'https://api.openai.com/v1/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                'model': 'gpt-4o-mini',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Eres un analizador de intereses de clientes. SIEMPRE responde únicamente con JSON válido.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.1,  # Muy bajo para respuestas consistentes
                'max_tokens': 300
            }
            
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"Error en API OpenAI: {response.status_code}")
                return []
            
            data = response.json()
            respuesta_ai = data['choices'][0]['message']['content'].strip()
            
            # Intentar parsear el JSON
            try:
                intereses = json.loads(respuesta_ai)
                # Validar que sea una lista
                if isinstance(intereses, list):
                    return intereses
                else:
                    print(f"Respuesta no es lista: {respuesta_ai}")
                    return []
            except json.JSONDecodeError:
                print(f"Error al parsear JSON: {respuesta_ai}")
                return []
            
        except Exception as e:
            print(f"Error en análisis de intereses: {e}")
            return []

    def guardar_intereses_en_bd(self, telefono, intereses, productos_disponibles):
        """
        Guarda los intereses en la base de datos con manejo mejorado de errores
        """
        conexion = None
        try:
            # Establecer conexión con autocommit deshabilitado
            conexion = mysql.connector.connect(**self.db_config)
            conexion.autocommit = False  # Usar transacciones manuales
            cursor = conexion.cursor()

            # Obtener ID del cliente
            cursor.execute("SELECT id_cliente FROM cliente WHERE telefono = %s", (telefono,))
            cliente = cursor.fetchone()

            if not cliente:
                print(f"❌ No se encontró cliente con teléfono: {telefono}")
                return False

            id_cliente = cliente[0]
            print(f"✅ Cliente encontrado: ID {id_cliente}")

            # Contador de operaciones exitosas
            operaciones_exitosas = 0
            
            for interes in intereses:
                try:
                    nombre_producto = interes.get('nombre')
                    nivel_interes = interes.get('nivel_interes')

                    # Validaciones
                    if not nombre_producto or not nivel_interes:
                        print(f"⚠️ Interés inválido (sin nombre o nivel): {interes}")
                        continue

                    if nombre_producto not in productos_disponibles:
                        print(f"⚠️ Producto no encontrado: {nombre_producto}")
                        continue

                    # Validar nivel de interés
                    if nivel_interes not in ['bajo', 'medio', 'alto']:
                        print(f"⚠️ Nivel de interés inválido: {nivel_interes}")
                        continue

                    id_producto = productos_disponibles[nombre_producto]
                    print(f"🔄 Procesando: {nombre_producto} (ID: {id_producto}) -> {nivel_interes}")

                    # Verificar si ya existe el interés
                    cursor.execute("""
                        SELECT id_interes, nivel_interes FROM interes
                        WHERE id_cliente = %s AND id_producto = %s AND activo = TRUE
                    """, (id_cliente, id_producto))

                    interes_existente = cursor.fetchone()

                    if interes_existente:
                        id_interes_existente = interes_existente[0]
                        nivel_actual = interes_existente[1]
                        
                        if nivel_actual != nivel_interes:
                            # Actualizar nivel de interés
                            cursor.execute("""
                                UPDATE interes
                                SET nivel_interes = %s, fecha_interes = CURRENT_TIMESTAMP
                                WHERE id_interes = %s
                            """, (nivel_interes, id_interes_existente))
                            
                            print(f"✅ Interés actualizado: {nivel_actual} -> {nivel_interes}")
                            operaciones_exitosas += 1
                        else:
                            print(f"ℹ️ Interés ya registrado con mismo nivel")
                    else:
                        # Insertar nuevo interés - INCLUIR TODOS LOS CAMPOS REQUERIDOS
                        cursor.execute("""
                            INSERT INTO interes (id_cliente, id_producto, nivel_interes, fecha_interes, activo)
                            VALUES (%s, %s, %s, CURRENT_TIMESTAMP, TRUE)
                        """, (id_cliente, id_producto, nivel_interes))
                        
                        print(f"✅ Nuevo interés insertado con ID: {cursor.lastrowid}")
                        operaciones_exitosas += 1

                except Exception as e_item:
                    print(f"❌ Error procesando interés individual {interes}: {e_item}")
                    continue

            # Confirmar transacción solo si hubo operaciones exitosas
            if operaciones_exitosas > 0:
                conexion.commit()
                print(f"✅ Transacción confirmada: {operaciones_exitosas} operaciones")
                
                # Verificar los intereses guardados
                cursor.execute("""
                    SELECT i.nivel_interes, p.nombre, i.fecha_interes
                    FROM interes i
                    JOIN producto p ON i.id_producto = p.id_producto
                    WHERE i.id_cliente = %s AND i.activo = TRUE
                    ORDER BY i.fecha_interes DESC
                    LIMIT 10
                """, (id_cliente,))
                
                intereses_verificacion = cursor.fetchall()
                print(f"📊 Intereses actuales del cliente ({len(intereses_verificacion)} total):")
                for interes_ver in intereses_verificacion:
                    print(f"   • {interes_ver[1]}: {interes_ver[0]} ({interes_ver[2]})")
                
                return True
            else:
                print("ℹ️ No hubo cambios que guardar")
                return True

        except mysql.connector.Error as e:
            print(f"❌ Error MySQL: {e}")
            if conexion and conexion.is_connected():
                conexion.rollback()
                print("🔄 Transacción revertida")
            return False
            
        except Exception as e:
            print(f"❌ Error general: {e}")
            if conexion and conexion.is_connected():
                conexion.rollback()
                print("🔄 Transacción revertida")
            return False
            
        finally:
            if conexion and conexion.is_connected():
                cursor.close()
                conexion.close()
                print("🔌 Conexión cerrada")

    def crear_cliente_si_no_existe(self, telefono):
        """
        Crea un cliente si no existe en la base de datos
        """
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor()

            # Verificar si el cliente existe
            cursor.execute("SELECT id_cliente FROM cliente WHERE telefono = %s", (telefono,))
            cliente_existente = cursor.fetchone()

            if cliente_existente:
                print(f"ℹ️ Cliente ya existe con ID: {cliente_existente[0]}")
                conexion.close()
                return cliente_existente[0]

            # Crear nuevo cliente
            cursor.execute("""
                INSERT INTO cliente (telefono, nombre, fecha_registro, activo)
                VALUES (%s, %s, CURRENT_TIMESTAMP, TRUE)
            """, (telefono, f"Cliente {telefono}"))

            id_cliente = cursor.lastrowid
            conexion.commit()
            print(f"✅ Nuevo cliente creado con ID: {id_cliente}")
            conexion.close()
            return id_cliente

        except Exception as e:
            print(f"❌ Error creando cliente: {e}")
            return None

    def analizar_mensaje_directo(self, mensaje, productos_disponibles):
        """
        Analiza un mensaje directo del usuario usando OpenAI para detectar intereses
        
        Args:
            mensaje (str): Mensaje del usuario
            productos_disponibles (dict): Productos disponibles {nombre: id}
        
        Returns:
            list: Lista de intereses detectados
        """
        try:
            productos_lista = list(productos_disponibles.keys())
            
            prompt = f"""
PRODUCTOS DISPONIBLES EN LA TIENDA:
{', '.join(productos_lista)}

MENSAJE DEL CLIENTE: "{mensaje}"

INSTRUCCIONES:
1. Analiza el mensaje y detecta qué productos específicos menciona o busca el cliente
2. SOLO considera productos que están EXACTAMENTE en la lista de productos disponibles
3. Si el cliente menciona una categoría (ej: "laptop", "teléfono", "audífonos"), busca productos de esa categoría en la lista
4. Determina el nivel de interés basado en el mensaje:
   - "alto": Pregunta específica sobre precio, características, disponibilidad
   - "medio": Consulta general o búsqueda de opciones
   - "bajo": Mención casual
5. DEBES devolver ÚNICAMENTE un array JSON válido:
[{{"nombre": "nombre_exacto_del_producto", "nivel_interes": "alto"}}]

REGLAS IMPORTANTES:
- Los nombres deben coincidir EXACTAMENTE con los de la lista
- Si no encuentras productos que coincidan, devuelve: []
- Si el cliente busca una categoría, incluye TODOS los productos relevantes de esa categoría

RESPUESTA (solo JSON):
"""
            
            endpoint = 'https://api.openai.com/v1/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}'
            }
            
            payload = {
                'model': 'gpt-4o-mini',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'Eres un experto en análisis de intenciones de compra. SIEMPRE responde únicamente con JSON válido.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'temperature': 0.1,
                'max_tokens': 300
            }
            
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            
            if response.status_code != 200:
                print(f"Error en API OpenAI: {response.status_code}")
                return []
            
            data = response.json()
            respuesta_ai = data['choices'][0]['message']['content'].strip()
            print(f"🤖 Respuesta de OpenAI: {respuesta_ai}")
            
            try:
                intereses = json.loads(respuesta_ai)
                if isinstance(intereses, list):
                    return intereses
                else:
                    print(f"Respuesta no es lista: {respuesta_ai}")
                    return []
            except json.JSONDecodeError:
                print(f"Error al parsear JSON: {respuesta_ai}")
                return []
                
        except Exception as e:
            print(f"Error en análisis de mensaje directo: {e}")
            return []

    def procesar_intereses_cliente(self, telefono, tipo_conversacion, mensaje_usuario=None):
        """
        Función principal que procesa los intereses de un cliente
        VERSIÓN MEJORADA con análisis de mensaje directo para chat_auto
        
        Args:
            telefono (str): Número de teléfono del cliente
            tipo_conversacion (str): 'inicial_3', 'final_3', 'chat_auto', etc.
            mensaje_usuario (str): Mensaje del usuario (para chat_auto)
        
        Returns:
            dict: Respuesta con estado del proceso
        """
        try:
            print(f"🚀 Iniciando procesamiento de intereses para: {telefono}")
            print(f"📝 Tipo de conversación: {tipo_conversacion}")
            
            # Manejar caso especial para chat automático
            if tipo_conversacion == "chat_auto":
                # Para chat automático, crear cliente si no existe
                id_cliente = self.crear_cliente_si_no_existe(telefono)
                if not id_cliente:
                    return {
                        'estado': 'error',
                        'mensaje': 'No se pudo crear o encontrar el cliente'
                    }
                
                # Obtener productos disponibles
                productos_disponibles = self.obtener_productos_disponibles()
                if not productos_disponibles:
                    return {
                        'estado': 'error',
                        'mensaje': 'No se pudieron obtener productos'
                    }
                
                # Si hay mensaje del usuario, analizarlo
                if mensaje_usuario:
                    print(f"💬 Analizando mensaje: {mensaje_usuario}")
                    intereses = self.analizar_mensaje_directo(mensaje_usuario, productos_disponibles)
                    print(f"🎯 Intereses detectados: {intereses}")
                    
                    if intereses:
                        exito = self.guardar_intereses_en_bd(telefono, intereses, productos_disponibles)
                        return {
                            'estado': 'exito' if exito else 'error',
                            'mensaje': 'Proceso correctamente' if exito else 'Error al procesar',
                            'intereses_detectados': intereses
                        }
                    else:
                        print("ℹ️ No se detectaron intereses específicos en el mensaje")
                        return {
                            'estado': 'exito',
                            'mensaje': 'Proceso correctamente',
                            'detalle': 'Sin intereses detectados en el mensaje'
                        }
                else:
                    print("⚠️ Chat automático sin mensaje para analizar")
                    return {
                        'estado': 'exito',
                        'mensaje': 'Proceso correctamente',
                        'detalle': 'Chat automático sin mensaje'
                    }
            
            # 1. Obtener conversaciones del cliente
            mensajes = self.obtener_conversaciones_cliente(telefono, tipo_conversacion)
            
            if mensajes is None:
                return {
                    'estado': 'error',
                    'mensaje': 'No existe el usuario'
                }
            
            if not mensajes:
                return {
                    'estado': 'exito',
                    'mensaje': 'Proceso correctamente',
                    'detalle': 'Sin conversaciones para analizar'
                }
            
            # 2. Obtener productos disponibles
            productos_disponibles = self.obtener_productos_disponibles()
            
            if not productos_disponibles:
                return {
                    'estado': 'error',
                    'mensaje': 'Proceso incorrecto',
                    'detalle': 'No se pudieron obtener productos'
                }
            
            print(f"📦 Productos disponibles: {len(productos_disponibles)}")
            print(f"💬 Mensajes a analizar: {len(mensajes)}")
            
            # 3. Analizar intereses con OpenAI
            intereses = self.analizar_intereses_con_openai(mensajes, productos_disponibles)
            print(f"🤖 Intereses detectados por OpenAI: {intereses}")

            # 4. Guardar intereses en la base de datos
            if intereses:
                exito = self.guardar_intereses_en_bd(telefono, intereses, productos_disponibles)
                
                if exito:
                    return {
                        'estado': 'exito',
                        'mensaje': 'Proceso correctamente',
                        'intereses_detectados': intereses
                    }
                else:
                    return {
                        'estado': 'error',
                        'mensaje': 'Proceso incorrecto',
                        'detalle': 'Error al guardar intereses'
                    }
            else:
                return {
                    'estado': 'exito',
                    'mensaje': 'Proceso correctamente',
                    'detalle': 'Sin intereses detectados'
                }
            
        except Exception as e:
            print(f"❌ Error en procesar_intereses_cliente: {e}")
            import traceback
            traceback.print_exc()
            return {
                'estado': 'error',
                'mensaje': 'Proceso incorrecto',
                'detalle': str(e)
            }