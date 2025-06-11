import mysql.connector
from mysql.connector import Error
import weasyprint
from datetime import datetime
import json
import os
import base64 
from io import BytesIO
from entrenamiento_fino import EntrenamientoFino

class GeneradorPDF:
    # def __init__(self):
    #     self.entrenamiento_fino = EntrenamientoFino()
    def __init__(self, entrenamiento_fino=None):
    # Si se pasa una instancia, usarla; sino crear nueva
        # self.entrenamiento_fino = entrenamiento_fino if entrenamiento_fino else EntrenamientoFino()
        self.entrenamiento_fino = entrenamiento_fino 
        # Configuración de la base de datos MySQL
        self.db_config = {
            'host': 'localhost',
            'user': 'root',          
            'password': '',  
            'database': 'bot_productos_db',
            'charset': 'utf8mb4'
        }
    
    def obtener_conexion_db(self):
        """Obtiene una conexión a la base de datos MySQL"""
        try:
            conexion = mysql.connector.connect(**self.db_config)
            if conexion.is_connected():
                return conexion
        except Error as e:
            print(f"Error al conectar a MySQL: {e}")
            return None
    
    def verificar_conexion_db(self):
        """Verifica si la conexión a la base de datos está funcionando"""
        conexion = self.obtener_conexion_db()
        if conexion:
            conexion.close()
            return True
        return False
    
    def intereses_usuario(self, numero_telefono):
        """
        Identifica intereses del usuario basado en conversaciones y genera PDF personalizado
        """
        try:
            conexion = self.obtener_conexion_db()
            if not conexion:
                return "Error de conexión a la base de datos"
            
            cursor = conexion.cursor(dictionary=True)
            
            # Obtener conversaciones del cliente
            query_conversaciones = """
            SELECT c.id_conversacion, cl.nombre, cl.telefono,
                   GROUP_CONCAT(
                       CONCAT(m.emisor, ': ', m.contenido) 
                       ORDER BY m.fecha_envio 
                       SEPARATOR '\n'
                   ) as conversacion_completa
            FROM conversacion c
            INNER JOIN cliente cl ON c.id_cliente = cl.id_cliente
            INNER JOIN mensaje m ON c.id_conversacion = m.id_conversacion
            WHERE cl.telefono = %s
            GROUP BY c.id_conversacion, cl.nombre, cl.telefono
            """
            
            cursor.execute(query_conversaciones, (numero_telefono,))
            conversaciones = cursor.fetchall()
            
            if not conversaciones:
                cursor.close()
                conexion.close()
                return "El usuario no tiene datos para crear marketing o información"
            
            # Preparar texto de conversaciones para análisis
            texto_conversaciones = ""
            for conv in conversaciones:
                texto_conversaciones += f"Conversación ID {conv['id_conversacion']}:\n"
                texto_conversaciones += conv['conversacion_completa'] + "\n\n"
            
            # Obtener productos, colecciones y promociones existentes para el prompt
            cursor.execute("SELECT id_producto, nombre FROM producto WHERE activo = TRUE")
            productos_bd = cursor.fetchall()
            
            cursor.execute("SELECT id_coleccion, nombre FROM coleccion WHERE activo = TRUE")
            colecciones_bd = cursor.fetchall()
            
            cursor.execute("SELECT id_promocion, nombre FROM promocion WHERE activo = TRUE")
            promociones_bd = cursor.fetchall()
            
            # Crear listas para el prompt
            productos_disponibles = "\n".join([f"ID: {p['id_producto']} - {p['nombre']}" for p in productos_bd])
            colecciones_disponibles = "\n".join([f"ID: {c['id_coleccion']} - {c['nombre']}" for c in colecciones_bd])
            promociones_disponibles = "\n".join([f"ID: {pr['id_promocion']} - {pr['nombre']}" for pr in promociones_bd])
            
            # Prompt mejorado para identificar intereses
            prompt_system = f"""
            Eres un experto analista de intereses de clientes. Analiza las conversaciones entre un cliente y un agente de ventas IA.
            
            PRODUCTOS DISPONIBLES EN BD:
            {productos_disponibles}
            
            COLECCIONES DISPONIBLES EN BD:
            {colecciones_disponibles}
            
            PROMOCIONES DISPONIBLES EN BD:
            {promociones_disponibles}
            
            INSTRUCCIONES:
            1. Identifica SOLO productos, colecciones y promociones que el cliente mencionó o preguntó específicamente
            2. Usa SOLO los IDs de la lista de arriba
            3. Determina nivel de interés:
               - 'alto': Mencionó varias veces, preguntó precio, mostró intención de compra
               - 'medio': Preguntó específicamente o pidió información
               - 'bajo': Solo mostró curiosidad básica
            
            FORMATO DE RESPUESTA (JSON):
            Devuelve un JSON con esta estructura exacta:
            {{
                "productos": [
                    {{"id_producto": ID, "nivel": "alto/medio/bajo"}},
                    {{"id_producto": ID, "nivel": "alto/medio/bajo"}}
                ],
                "colecciones": [
                    {{"id_coleccion": ID, "nivel": "alto/medio/bajo"}}
                ],
                "promociones": [
                    {{"id_promocion": ID, "nivel": "alto/medio/bajo"}}
                ]
            }}
            
            Si no hay intereses en alguna categoría, deja el array vacío [].
            RESPONDE SOLO CON EL JSON, SIN TEXTO ADICIONAL.
            """
            
            # Obtener ID del cliente
            cursor.execute("SELECT id_cliente FROM cliente WHERE telefono = %s", (numero_telefono,))
            cliente_data = cursor.fetchone()
            id_cliente = cliente_data['id_cliente'] if cliente_data else None
            
            if not id_cliente:
                cursor.close()
                conexion.close()
                return "Cliente no encontrado"
            
            # Analizar intereses con IA
            respuesta_ia = self.entrenamiento_fino.obtener_informacion_modelo(
                 prompt_system,
                 f"CONVERSACIONES DEL CLIENTE:\n{texto_conversaciones}",
            )

            # 🔍 DEBUG: Ver qué está pasando
            print(f"🔍 Tipo de respuesta: {type(respuesta_ia)}")
            print(f"🔍 Contenido completo: {respuesta_ia}")

            if isinstance(respuesta_ia, dict):
                print(f"🔍 Status: {respuesta_ia.get('status')}")
                print(f"🔍 Message: {respuesta_ia.get('message')}")
                if 'error_details' in respuesta_ia:
                    print(f"🔍 Error details: {respuesta_ia.get('error_details')}")

            if isinstance(respuesta_ia, dict):
                if respuesta_ia.get('status') == 'success':
                    respuesta_texto = respuesta_ia.get('data', '')
                else:
                    print(f"Error en respuesta IA: {respuesta_ia.get('message', 'Error desconocido')}")
                    cursor.close()
                    conexion.close()
                    return f"Error en IA: {respuesta_ia.get('message', 'Error desconocido')}"
            else:
                respuesta_texto = str(respuesta_ia)
            
            # Procesar respuesta JSON
            try:
                respuesta_texto_limpia = respuesta_texto.strip()
                intereses_data = json.loads(respuesta_texto_limpia)
                
                # Procesar productos de interés
                for producto_interes in intereses_data.get('productos', []):
                    self._insertar_o_actualizar_interes_producto(
                        cursor, id_cliente, 
                        producto_interes['id_producto'], 
                        producto_interes['nivel']
                    )
                
                # Procesar colecciones de interés
                for coleccion_interes in intereses_data.get('colecciones', []):
                    self._insertar_o_actualizar_interes_coleccion(
                        cursor, id_cliente,
                        coleccion_interes['id_coleccion'],
                        coleccion_interes['nivel']
                    )
                
                # Procesar promociones de interés
                for promocion_interes in intereses_data.get('promociones', []):
                    self._insertar_o_actualizar_interes_promocion(
                        cursor, id_cliente,
                        promocion_interes['id_promocion'],
                        promocion_interes['nivel']
                    )
                
                # ⚠️ CORREGIDO: Mover commit y generación de PDF aquí
                conexion.commit()
                
                # Generar PDF con intereses del usuario
                pdf_path = self._generar_pdf_intereses_usuario(numero_telefono, cursor)
                
                cursor.close()
                conexion.close()
                
                return pdf_path
                    
            except json.JSONDecodeError as e:
                print(f"Error parseando JSON de IA: {e}")
                print(f"Respuesta IA: {respuesta_ia}")
                cursor.close()
                conexion.close()
                return "Error procesando respuesta de IA"
            
        except Exception as e:
            print(f"Error en intereses_usuario: {e}")
            if 'conexion' in locals() and conexion.is_connected():
                conexion.close()
            return f"Error procesando intereses: {e}"
    
    def _insertar_o_actualizar_interes_producto(self, cursor, id_cliente, id_producto, nivel_interes):
        """Inserta o actualiza interés en producto"""
        try:
            # Verificar si ya existe
            cursor.execute("""
                SELECT id_interes FROM interes_producto 
                WHERE id_cliente = %s AND id_producto = %s
            """, (id_cliente, id_producto))
            
            existe = cursor.fetchone()
            
            if existe:
                # Actualizar
                cursor.execute("""
                    UPDATE interes_producto 
                    SET nivel_interes = %s, fecha_interes = CURRENT_TIMESTAMP, activo = TRUE
                    WHERE id_cliente = %s AND id_producto = %s
                """, (nivel_interes, id_cliente, id_producto))
            else:
                # Insertar nuevo
                cursor.execute("""
                    INSERT INTO interes_producto (id_cliente, id_producto, nivel_interes) 
                    VALUES (%s, %s, %s)
                """, (id_cliente, id_producto, nivel_interes))
                
        except Error as e:
            print(f"Error procesando interés producto: {e}")
    
    def _insertar_o_actualizar_interes_coleccion(self, cursor, id_cliente, id_coleccion, nivel_interes):
        """Inserta o actualiza interés en colección"""
        try:
            cursor.execute("""
                SELECT id_interes FROM interes_coleccion 
                WHERE id_cliente = %s AND id_coleccion = %s
            """, (id_cliente, id_coleccion))
            
            existe = cursor.fetchone()
            
            if existe:
                cursor.execute("""
                    UPDATE interes_coleccion 
                    SET nivel_interes = %s, fecha_interes = CURRENT_TIMESTAMP, activo = TRUE
                    WHERE id_cliente = %s AND id_coleccion = %s
                """, (nivel_interes, id_cliente, id_coleccion))
            else:
                cursor.execute("""
                    INSERT INTO interes_coleccion (id_cliente, id_coleccion, nivel_interes) 
                    VALUES (%s, %s, %s)
                """, (id_cliente, id_coleccion, nivel_interes))
                
        except Error as e:
            print(f"Error procesando interés colección: {e}")
    
    def _insertar_o_actualizar_interes_promocion(self, cursor, id_cliente, id_promocion, nivel_interes):
        """Inserta o actualizar interés en promoción"""
        try:
            cursor.execute("""
                SELECT id_interes FROM interes_promocion 
                WHERE id_cliente = %s AND id_promocion = %s
            """, (id_cliente, id_promocion))
            
            existe = cursor.fetchone()
            
            if existe:
                cursor.execute("""
                    UPDATE interes_promocion 
                    SET nivel_interes = %s, fecha_interes = CURRENT_TIMESTAMP, activo = TRUE
                    WHERE id_cliente = %s AND id_promocion = %s
                """, (nivel_interes, id_cliente, id_promocion))
            else:
                cursor.execute("""
                    INSERT INTO interes_promocion (id_cliente, id_promocion, nivel_interes) 
                    VALUES (%s, %s, %s)
                """, (id_cliente, id_promocion, nivel_interes))
                
        except Error as e:
            print(f"Error procesando interés promoción: {e}")
    
    def _generar_pdf_intereses_usuario(self, numero_telefono, cursor):
        """Genera PDF con los intereses del usuario"""
        try:
            # Obtener información del cliente
            cursor.execute("""
                SELECT nombre, email, telefono, fecha_registro 
                FROM cliente WHERE telefono = %s
            """, (numero_telefono,))
            cliente = cursor.fetchone()
            
            # Obtener productos de interés
            cursor.execute("""
                SELECT p.nombre, p.descripcion, p.precio_base, ip.nivel_interes, ip.fecha_interes
                FROM interes_producto ip
                INNER JOIN producto p ON ip.id_producto = p.id_producto
                INNER JOIN cliente c ON ip.id_cliente = c.id_cliente
                WHERE c.telefono = %s AND ip.activo = TRUE
                ORDER BY ip.nivel_interes DESC, ip.fecha_interes DESC
            """, (numero_telefono,))
            productos_interes = cursor.fetchall()
            
            # Obtener colección con mayor interés
            cursor.execute("""
                SELECT col.nombre, col.descripcion, ic.nivel_interes, ic.fecha_interes,
                       COUNT(pc.id_producto) as total_productos
                FROM interes_coleccion ic
                INNER JOIN coleccion col ON ic.id_coleccion = col.id_coleccion
                INNER JOIN cliente c ON ic.id_cliente = c.id_cliente
                LEFT JOIN productocoleccion pc ON col.id_coleccion = pc.id_coleccion
                WHERE c.telefono = %s AND ic.activo = TRUE
                GROUP BY col.id_coleccion
                ORDER BY ic.nivel_interes DESC, ic.fecha_interes DESC
                LIMIT 1
            """, (numero_telefono,))
            coleccion_principal = cursor.fetchone()
            
            # Obtener promociones de interés
            cursor.execute("""
                SELECT pr.nombre, pr.descripcion, pr.tipo_descuento, pr.valor_descuento,
                       pr.fecha_inicio, pr.fecha_fin, ipr.nivel_interes
                FROM interes_promocion ipr
                INNER JOIN promocion pr ON ipr.id_promocion = pr.id_promocion
                INNER JOIN cliente c ON ipr.id_cliente = c.id_cliente
                WHERE c.telefono = %s AND ipr.activo = TRUE AND pr.activo = TRUE
                ORDER BY ipr.nivel_interes DESC, ipr.fecha_interes DESC
            """, (numero_telefono,))
            promociones_interes = cursor.fetchall()
            
            # Crear HTML para el PDF
            html_content = self._crear_html_intereses_usuario(
                cliente, productos_interes, coleccion_principal, promociones_interes
            )
            
            # Generar PDF en memoria
            pdf_buffer = BytesIO()
            weasyprint.HTML(string=html_content).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)
            
            # Convertir a base64
            pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
            
            return pdf_base64
            
        except Exception as e:
            print(f"Error generando PDF de intereses: {e}")
            return None
    
    def _crear_html_intereses_usuario(self, cliente, productos, coleccion, promociones):
        """Crea el HTML para el PDF de intereses del usuario"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 20px; text-align: center; }}
                .section {{ margin: 20px 0; padding: 15px; border-left: 4px solid #3498db; }}
                .product {{ background-color: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .promocion {{ background-color: #fff3cd; padding: 10px; margin: 10px 0; border-radius: 5px; }}
                .interes-alto {{ border-left-color: #e74c3c; }}
                .interes-medio {{ border-left-color: #f39c12; }}
                .interes-bajo {{ border-left-color: #95a5a6; }}
                .no-data {{ text-align: center; color: #7f8c8d; font-style: italic; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Reporte de Intereses Personalizados</h1>
                <p>Cliente: {cliente['nombre'] or 'Cliente'} | Teléfono: {cliente['telefono']}</p>
                <p>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
            </div>
            
            <div class="section">
                <h2>🛍️ Productos de tu Interés</h2>
        """
        
        if productos:
            for producto in productos:
                nivel_class = f"interes-{producto['nivel_interes']}"
                html += f"""
                <div class="product {nivel_class}">
                    <h3>{producto['nombre']}</h3>
                    <p><strong>Descripción:</strong> {producto['descripcion'] or 'No disponible'}</p>
                    <p><strong>Precio:</strong> ${producto['precio_base']:.2f}</p>
                    <p><strong>Nivel de Interés:</strong> {producto['nivel_interes'].upper()}</p>
                    <p><small>Fecha de interés: {producto['fecha_interes'].strftime('%d/%m/%Y')}</small></p>
                </div>
                """
        else:
            html += '<p class="no-data">No se encontraron productos de interés registrados.</p>'
        
        html += '</div><div class="section"><h2>📱 Colección Destacada</h2>'
        
        if coleccion:
            html += f"""
            <div class="product">
                <h3>{coleccion['nombre']}</h3>
                <p><strong>Descripción:</strong> {coleccion['descripcion'] or 'No disponible'}</p>
                <p><strong>Total de productos:</strong> {coleccion['total_productos']}</p>
                <p><strong>Nivel de Interés:</strong> {coleccion['nivel_interes'].upper()}</p>
            </div>
            """
        else:
            html += '<p class="no-data">No se encontraron colecciones de interés.</p>'
        
        html += '</div><div class="section"><h2>🎉 Promociones Especiales</h2>'
        
        if promociones:
            for promo in promociones:
                descuento = f"{promo['valor_descuento']}%" if promo['tipo_descuento'] == 'porcentaje' else f"${promo['valor_descuento']}"
                html += f"""
                <div class="promocion">
                    <h3>{promo['nombre']}</h3>
                    <p><strong>Descripción:</strong> {promo['descripcion'] or 'No disponible'}</p>
                    <p><strong>Descuento:</strong> {descuento}</p>
                    <p><strong>Válida:</strong> {promo['fecha_inicio'].strftime('%d/%m/%Y')} - {promo['fecha_fin'].strftime('%d/%m/%Y')}</p>
                    <p><strong>Nivel de Interés:</strong> {promo['nivel_interes'].upper()}</p>
                </div>
                """
        else:
            html += '<p class="no-data">No se encontraron promociones de interés.</p>'
        
        html += """
            </div>
            <div style="text-align: center; margin-top: 30px; color: #7f8c8d;">
                <p>Reporte generado automáticamente por nuestro sistema de análisis de intereses</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def informacion_coleccion(self, nombre_coleccion):
        """
        Genera PDF informativo de productos de una colección específica
        """
        try:
            conexion = self.obtener_conexion_db()
            if not conexion:
                return "Error de conexión a la base de datos"
            
            cursor = conexion.cursor(dictionary=True)
            
            # Obtener información de la colección
            cursor.execute("""
                SELECT * FROM coleccion WHERE nombre = %s AND activo = TRUE
            """, (nombre_coleccion,))
            coleccion = cursor.fetchone()
            
            if not coleccion:
                cursor.close()
                conexion.close()
                return "No hay información de esta colección"
            
            # Obtener productos de la colección
            cursor.execute("""
                SELECT p.nombre, p.descripcion, p.precio_base, p.stock_global, p.imagen
                FROM producto p
                INNER JOIN productocoleccion pc ON p.id_producto = pc.id_producto
                WHERE pc.id_coleccion = %s AND p.activo = TRUE
                ORDER BY p.nombre
            """, (coleccion['id_coleccion'],))
            productos = cursor.fetchall()
            
            if not productos:
                cursor.close()
                conexion.close()
                return "No hay productos en esta colección"
            
            # Generar PDF
            pdf_path = self._generar_pdf_coleccion(coleccion, productos)
            
            cursor.close()
            conexion.close()
            
            return pdf_path
            
        except Exception as e:
            print(f"Error en informacion_coleccion: {e}")
            return f"Error procesando colección: {e}"
    
    def _generar_pdf_coleccion(self, coleccion, productos):
        """Genera PDF con información de la colección"""
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #34495e; color: white; padding: 20px; text-align: center; }}
                    .product {{ background-color: #f8f9fa; padding: 15px; margin: 15px 0; border-radius: 8px; border-left: 4px solid #3498db; }}
                    .stock-alto {{ border-left-color: #27ae60; }}
                    .stock-medio {{ border-left-color: #f39c12; }}
                    .stock-bajo {{ border-left-color: #e74c3c; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>Catálogo de Colección</h1>
                    <h2>{coleccion['nombre']}</h2>
                    <p>{coleccion['descripcion'] or 'Colección de productos seleccionados'}</p>
                    <p>Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                </div>
                
                <div style="margin: 20px 0;">
                    <h2>Productos Disponibles ({len(productos)} productos)</h2>
            """
            
            for producto in productos:
                stock_class = ""
                if producto['stock_global'] > 10:
                    stock_class = "stock-alto"
                elif producto['stock_global'] > 0:
                    stock_class = "stock-medio"
                else:
                    stock_class = "stock-bajo"
                
                html_content += f"""
                <div class="product {stock_class}">
                    <h3>{producto['nombre']}</h3>
                    <p><strong>Descripción:</strong> {producto['descripcion'] or 'No disponible'}</p>
                    <p><strong>Precio:</strong> ${producto['precio_base']:.2f}</p>
                    <p><strong>Stock:</strong> {producto['stock_global']} unidades</p>
                </div>
                """
            
            html_content += """
                </div>
                <div style="text-align: center; margin-top: 30px; color: #7f8c8d;">
                    <p>Catálogo generado automáticamente</p>
                </div>
            </body>
            </html>
            """
            
            # Generar PDF en memoria
            pdf_buffer = BytesIO()
            weasyprint.HTML(string=html_content).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)
            
            # Convertir a base64
            pdf_base64 = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
            
            return pdf_base64
            
        except Exception as e:
            print(f"Error generando PDF de colección: {e}")
            return None
    
    def informacion_promocion(self, nombre_promocion):
        """
        Genera PDF informativo de una promoción específica
        """
        try:
            conexion = self.obtener_conexion_db()
            if not conexion:
                return "Error de conexión a la base de datos"
            
            cursor = conexion.cursor(dictionary=True)
            

            # Obtener información de la promoción
            cursor.execute("""
                SELECT * FROM promocion 
                WHERE nombre = %s AND activo = TRUE 
            """, (nombre_promocion,))
            promocion = cursor.fetchone()
            # AND fecha_inicio <= CURDATE() AND fecha_fin >= CURDATE()
            
            if not promocion:
                cursor.close()
                conexion.close()
                return "No hay información de esta promoción"
            
            # Obtener productos en promoción
            cursor.execute("""
                SELECT p.nombre, p.descripcion, p.precio_base, p.stock_global
                FROM producto p
                INNER JOIN promocionproducto pp ON p.id_producto = pp.id_producto
                WHERE pp.id_promocion = %s AND p.activo = TRUE
                ORDER BY p.nombre
            """, (promocion['id_promocion'],))
            productos_promocion = cursor.fetchall()
            
            # Obtener colecciones en promoción
            cursor.execute("""
                SELECT c.nombre, c.descripcion, COUNT(pc.id_producto) as total_productos
                FROM coleccion c
                INNER JOIN promocioncoleccion pcol ON c.id_coleccion = pcol.id_coleccion
                LEFT JOIN productocoleccion pc ON c.id_coleccion = pc.id_coleccion
                WHERE pcol.id_promocion = %s AND c.activo = TRUE
                GROUP BY c.id_coleccion
                ORDER BY c.nombre
            """, (promocion['id_promocion'],))
            colecciones_promocion = cursor.fetchall()
            
            # Generar PDF
            pdf_data_base64 = self._generar_pdf_promocion(promocion, productos_promocion, colecciones_promocion)

            cursor.close()
            conexion.close()
            
            return pdf_data_base64
            
        except Exception as e:
            print(f"Error en informacion_promocion: {e}")
            return f"Error procesando promoción: {e}"
    
    def _generar_pdf_promocion(self, promocion, productos, colecciones):
        """Genera PDF con información de la promoción"""
        try:
            descuento_texto = f"{promocion['valor_descuento']}%" if promocion['tipo_descuento'] == 'porcentaje' else f"${promocion['valor_descuento']}"
            
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .header {{ background-color: #e74c3c; color: white; padding: 20px; text-align: center; }}
                    .promo-info {{ background-color: #fff3cd; padding: 20px; margin: 20px 0; border-radius: 8px; }}
                    .product {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; }}
                    .precio-original {{ text-decoration: line-through; color: #7f8c8d; }}
                    .precio-oferta {{ color: #e74c3c; font-weight: bold; font-size: 1.2em; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🎉 PROMOCIÓN ESPECIAL</h1>
                    <h2>{promocion['nombre']}</h2>
                    <h3>¡{descuento_texto} de DESCUENTO!</h3>
                </div>
                
                <div class="promo-info">
                    <h3>Detalles de la Promoción</h3>
                    <p><strong>Descripción:</strong> {promocion['descripcion'] or 'Promoción especial'}</p>
                    <p><strong>Descuento:</strong> {descuento_texto}</p>
                    <p><strong>Válida desde:</strong> {promocion['fecha_inicio'].strftime('%d/%m/%Y')}</p>
                    <p><strong>Válida hasta:</strong> {promocion['fecha_fin'].strftime('%d/%m/%Y')}</p>
                </div>
            """
            
            if productos:
                html_content += f"""
                <div style="margin: 20px 0;">
                    <h2>Productos en Promoción ({len(productos)} productos)</h2>
                """
                
                for producto in productos:
                    precio_original = producto['precio_base']
                    if promocion['tipo_descuento'] == 'porcentaje':
                        precio_oferta = precio_original * (1 - promocion['valor_descuento'] / 100)
                    else:
                        precio_oferta = precio_original - promocion['valor_descuento']
                    
                    html_content += f"""
                    <div class="product">
                        <h3>{producto['nombre']}</h3>
                        <p>{producto['descripcion'] or 'Producto en oferta especial'}</p>
                        <p><span class="precio-original">Precio normal: ${precio_original:.2f}</span></p>
                        <p><span class="precio-oferta">¡Precio promocional: ${precio_oferta:.2f}!</span></p>
                        <p><strong>Stock disponible:</strong> {producto['stock_global']} unidades</p>
                    </div>
                    """
                
                html_content += "</div>"
            
            if colecciones:
                html_content += f"""
                <div style="margin: 20px 0;">
                    <h2>Colecciones en Promoción ({len(colecciones)} colecciones)</h2>
                """
                
                for coleccion in colecciones:
                    html_content += f"""
                    <div class="product">
                        <h3>{coleccion['nombre']}</h3>
                        <p>{coleccion['descripcion'] or 'Colección completa en promoción'}</p>
                        <p><strong>Total de productos:</strong> {coleccion['total_productos']}</p>
                        <p><strong>Descuento aplicado:</strong> {descuento_texto} en toda la colección</p>
                    </div>
                    """
                
                html_content += "</div>"
            
            if not productos and not colecciones:
                html_content += '<p style="text-align: center; color: #7f8c8d;">No hay productos específicos en esta promoción.</p>'
            
            html_content += f"""
                <div style="text-align: center; margin-top: 30px; background-color: #2c3e50; color: white; padding: 15px;">
                    <h3>¡No te pierdas esta oportunidad!</h3>
                    <p>Promoción válida hasta: {promocion['fecha_fin'].strftime('%d/%m/%Y')}</p>
                </div>
            </body>
            </html>
            """
            # Generar PDF en memoria
            pdf_buffer = BytesIO()
            weasyprint.HTML(string=html_content).write_pdf(pdf_buffer)
            pdf_buffer.seek(0)
            
            # Convertir a base64
            pdf_base64 = base64.b64encode(pdf_buffer.read()).decode('utf-8')
            
            return pdf_base64
            
        except Exception as e:
            print(f"Error generando PDF de promoción: {e}")
            return None


# Ejemplo de uso:
# if __name__ == "__main__":
#     generador = GeneradorPDF()
    
#     # Verificar conexión
#     if generador.verificar_conexion_db():
#         print("✅ Conexión a base de datos exitosa")
        
#         # Ejemplo: Generar PDF de intereses para un usuario
#         pdf_base64 = generador.intereses_usuario("+59176987654")
#         if isinstance(pdf_base64, str) and len(pdf_base64) > 100:  # Es un base64 válido
#             # Guardar el PDF localmente
#             pdf_data = base64.b64decode(pdf_base64)
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             nombre_archivo = f"intereses_usuario_+59176987654_{timestamp}.pdf"
            
#             with open(nombre_archivo, "wb") as archivo:
#                 archivo.write(pdf_data)
            
#             print(f"✅ PDF de intereses guardado como: {nombre_archivo}")
#         else:
#             print(f"Resultado intereses: {pdf_base64}")
        
#         # Ejemplo: Generar PDF de colección
#         pdf_base64 = generador.informacion_coleccion("Consolas & Gaming")
#         if isinstance(pdf_base64, str) and len(pdf_base64) > 100:  # Es un base64 válido
#             # Guardar el PDF localmente
#             pdf_data = base64.b64decode(pdf_base64)
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             nombre_archivo = f"coleccion_Consolas_Gaming_{timestamp}.pdf"
            
#             with open(nombre_archivo, "wb") as archivo:
#                 archivo.write(pdf_data)
            
#             print(f"✅ PDF de colección guardado como: {nombre_archivo}")
#         else:
#             print(f"Resultado colección: {pdf_base64}")
        
#         # Ejemplo: Generar PDF de promoción
#         pdf_base64 = generador.informacion_promocion("Cyber Monday Gaming")
#         if isinstance(pdf_base64, str) and len(pdf_base64) > 100:  # Es un base64 válido
#             # Guardar el PDF localmente
#             pdf_data = base64.b64decode(pdf_base64)
#             timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
#             nombre_archivo = f"promocion_Cyber_Monday_Gaming_{timestamp}.pdf"
            
#             with open(nombre_archivo, "wb") as archivo:
#                 archivo.write(pdf_data)
            
#             print(f"✅ PDF de promoción guardado como: {nombre_archivo}")
#         else:
#             print(f"Resultado promoción: {pdf_base64}")
        
#     else:
#         print("❌ Error de conexión a base de datos")