import mysql.connector
from datetime import datetime

class ManejadorConversaciones:
    def __init__(self):
        """
        Inicializar el manejador de conversaciones
        """
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'bot_productos_db',
            'charset': 'utf8mb4'
        }
    
    def obtener_o_crear_cliente(self, telefono):
        """
        Obtiene el ID del cliente o lo crea si no existe
        """
        conexion = None
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor()
            
            # Buscar cliente existente
            cursor.execute("SELECT id_cliente FROM cliente WHERE telefono = %s", (telefono,))
            resultado = cursor.fetchone()
            
            if resultado:
                return resultado[0]
            
            # Crear nuevo cliente
            cursor.execute("""
                INSERT INTO cliente (telefono, nombre, fecha_registro, activo)
                VALUES (%s, %s, CURRENT_TIMESTAMP, TRUE)
            """, (telefono, f"Cliente {telefono}"))
            
            id_cliente = cursor.lastrowid
            conexion.commit()
            print(f"✅ Nuevo cliente creado: ID {id_cliente}")
            return id_cliente
            
        except Exception as e:
            print(f"❌ Error en obtener_o_crear_cliente: {e}")
            if conexion:
                conexion.rollback()
            return None
        finally:
            if conexion and conexion.is_connected():
                cursor.close()
                conexion.close()
    
    def obtener_conversacion_activa(self, id_cliente):
        """
        Obtiene la conversación activa del cliente o None si no hay
        Una conversación se considera activa si fue actualizada en los últimos 5 minutos
        """
        conexion = None
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor()
            
            # Buscar conversación activa (última actualización < 5 minutos)
            cursor.execute("""
                SELECT id_conversacion 
                FROM conversacion 
                WHERE id_cliente = %s 
                AND estado = 'activa'
                AND TIMESTAMPDIFF(MINUTE, fecha_ultima_actividad, NOW()) < 5
                ORDER BY fecha_ultima_actividad DESC
                LIMIT 1
            """, (id_cliente,))
            
            resultado = cursor.fetchone()
            return resultado[0] if resultado else None
            
        except Exception as e:
            print(f"❌ Error obteniendo conversación activa: {e}")
            return None
        finally:
            if conexion and conexion.is_connected():
                cursor.close()
                conexion.close()
    
    def crear_conversacion(self, id_cliente):
        """
        Crea una nueva conversación para el cliente
        """
        conexion = None
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor()
            
            # Cerrar conversaciones anteriores del cliente
            cursor.execute("""
                UPDATE conversacion 
                SET estado = 'finalizada'
                WHERE id_cliente = %s AND estado = 'activa'
            """, (id_cliente,))
            
            # Crear nueva conversación
            cursor.execute("""
                INSERT INTO conversacion (
                    id_cliente, 
                    fecha_inicio, 
                    fecha_ultima_actividad, 
                    estado, 
                    canal
                )
                VALUES (%s, NOW(), NOW(), 'activa', 'whatsapp')
            """, (id_cliente,))
            
            id_conversacion = cursor.lastrowid
            conexion.commit()
            print(f"✅ Nueva conversación creada: ID {id_conversacion}")
            return id_conversacion
            
        except Exception as e:
            print(f"❌ Error creando conversación: {e}")
            if conexion:
                conexion.rollback()
            return None
        finally:
            if conexion and conexion.is_connected():
                cursor.close()
                conexion.close()
    
    def guardar_mensaje(self, id_conversacion, contenido, emisor='usuario'):
        """
        Guarda un mensaje en la base de datos
        
        Args:
            id_conversacion: ID de la conversación
            contenido: Contenido del mensaje
            emisor: 'usuario' o 'bot'
        """
        conexion = None
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor()
            
            # Insertar mensaje
            cursor.execute("""
                INSERT INTO mensaje (
                    id_conversacion,
                    contenido,
                    emisor,
                    fecha_envio
                )
                VALUES (%s, %s, %s, NOW())
            """, (id_conversacion, contenido, emisor))
            
            id_mensaje = cursor.lastrowid
            
            # Actualizar fecha_ultima_actividad de la conversación
            cursor.execute("""
                UPDATE conversacion 
                SET fecha_ultima_actividad = NOW()
                WHERE id_conversacion = %s
            """, (id_conversacion,))
            
            conexion.commit()
            print(f"✅ Mensaje guardado: ID {id_mensaje} ({emisor})")
            return id_mensaje
            
        except Exception as e:
            print(f"❌ Error guardando mensaje: {e}")
            if conexion:
                conexion.rollback()
            return None
        finally:
            if conexion and conexion.is_connected():
                cursor.close()
                conexion.close()
    
    def procesar_mensaje_entrante(self, telefono, mensaje_contenido):
        """
        Procesa un mensaje entrante: crea/obtiene cliente y conversación, guarda el mensaje
        
        Returns:
            dict con id_cliente, id_conversacion, id_mensaje
        """
        try:
            # 1. Obtener o crear cliente
            id_cliente = self.obtener_o_crear_cliente(telefono)
            if not id_cliente:
                return None
            
            # 2. Obtener conversación activa o crear nueva
            id_conversacion = self.obtener_conversacion_activa(id_cliente)
            if not id_conversacion:
                id_conversacion = self.crear_conversacion(id_cliente)
                if not id_conversacion:
                    return None
            
            # 3. Guardar mensaje del usuario
            id_mensaje = self.guardar_mensaje(id_conversacion, mensaje_contenido, 'usuario')
            
            return {
                'id_cliente': id_cliente,
                'id_conversacion': id_conversacion,
                'id_mensaje': id_mensaje
            }
            
        except Exception as e:
            print(f"❌ Error en procesar_mensaje_entrante: {e}")
            return None
    
    def guardar_respuesta_bot(self, id_conversacion, respuesta):
        """
        Guarda la respuesta del bot
        """
        return self.guardar_mensaje(id_conversacion, respuesta, 'bot')
    
    def cerrar_conversacion(self, id_conversacion):
        """
        Cierra una conversación marcándola como finalizada
        """
        conexion = None
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor()
            
            cursor.execute("""
                UPDATE conversacion 
                SET estado = 'finalizada',
                    fecha_fin = NOW()
                WHERE id_conversacion = %s
            """, (id_conversacion,))
            
            conexion.commit()
            print(f"✅ Conversación {id_conversacion} cerrada")
            return True
            
        except Exception as e:
            print(f"❌ Error cerrando conversación: {e}")
            return False
        finally:
            if conexion and conexion.is_connected():
                cursor.close()
                conexion.close()