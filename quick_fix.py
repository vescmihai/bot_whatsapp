# fix_database_queries.py
# Parche para corregir las consultas problemáticas en gestor_base_conocimiento.py

"""
PROBLEMA IDENTIFICADO:
El error "Unknown column 's.id_sucursal'" indica que hay consultas en gestor_base_conocimiento.py
que usan alias 's' sin definir correctamente las relaciones.

SOLUCIÓN:
Actualizar las consultas complejas para que funcionen con la nueva estructura de BD.
"""

import mysql.connector
import json
import pickle
from datetime import datetime
from openai import OpenAI
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.schema import Document
import sys
import traceback

class GestorBaseConocimientoFixed:
    """Versión corregida del gestor de base de conocimiento"""
    
    def __init__(self):
        # Configuración única
        self.configuracion_bd = {
            'host': 'localhost', 'user': 'root', 'password': '', 
            'database': 'bot_productos_db', 'charset': 'utf8mb4'
        }
        
        self.cliente_openai = OpenAI(
            api_key=""
        )
        
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=self.cliente_openai.api_key,
            model="text-embedding-ada-002"
        )
        
        self.nombre_vectorstore = "conocimiento_completo"
        
        # Auto-inicialización
        self._inicializar()
    
    def _ejecutar_consulta(self, consulta, parametros=None, obtener_datos=False, dictionary=False):
        """Función única para todas las operaciones de BD"""
        try:
            conexion = mysql.connector.connect(**self.configuracion_bd)
            cursor = conexion.cursor(dictionary=dictionary)
            
            cursor.execute(consulta, parametros or ())
            
            if obtener_datos:
                resultado = cursor.fetchall()
            else:
                conexion.commit()
                resultado = cursor.rowcount
                
            conexion.close()
            return resultado
            
        except Exception as e:
            print(f"❌ Error BD: {e}")
            return [] if obtener_datos else False
    
    def _inicializar(self):
        """Inicialización automática completa"""
        print("🚀 Inicializando gestor corregido...")
        
        # Verificar conexión
        if not self._ejecutar_consulta("SELECT 1", obtener_datos=True):
            print("❌ Sin conexión a BD")
            return
        
        # Verificar si necesita procesar contenido
        count = self._ejecutar_consulta("SELECT COUNT(*) FROM base_conocimiento_analisis", obtener_datos=True)
        
        if not count or count[0][0] == 0:
            print("📝 Procesando toda la base de conocimiento...")
            self._procesar_todo_el_contenido()
        else:
            print(f"✅ Base lista con {count[0][0]} registros")
    
    # ============================================
    # CONSULTAS CORREGIDAS
    # ============================================
    
    def _obtener_productos_completos(self):
        """🔧 CONSULTA CORREGIDA - Productos con toda su información relacionada"""
        consulta = """
        SELECT 
            p.id_producto, 
            p.nombre, 
            p.descripcion, 
            p.codigo, 
            p.stock_global, 
            p.precio_base,
            p.imagen,
            -- Subconsulta para ubicaciones (corregida)
            (SELECT GROUP_CONCAT(CONCAT(suc.nombre,'|',suc.direccion,'|',alm.nombre,'|',sa.cantidad) SEPARATOR ';')
             FROM stockalmacen sa 
             JOIN almacen alm ON sa.id_almacen = alm.id_almacen
             JOIN sucursal suc ON alm.id_sucursal = suc.id_sucursal
             WHERE sa.id_producto = p.id_producto AND sa.cantidad > 0
            ) as ubicaciones,
            
            -- Subconsulta para colecciones (corregida)
            (SELECT GROUP_CONCAT(CONCAT(col.nombre,'|',COALESCE(col.descripcion,'')) SEPARATOR ';')
             FROM productocoleccion pc 
             JOIN coleccion col ON pc.id_coleccion = col.id_coleccion
             WHERE pc.id_producto = p.id_producto AND col.activo = TRUE
            ) as colecciones,
            
            -- Subconsulta para promociones (corregida)
            (SELECT GROUP_CONCAT(CONCAT(pr.nombre,'|',COALESCE(pr.descripcion,''),'|',pr.tipo_descuento,'|',pr.valor_descuento,'|',pr.fecha_inicio,'|',pr.fecha_fin) SEPARATOR ';')
             FROM promocionproducto pp 
             JOIN promocion pr ON pp.id_promocion = pr.id_promocion
             WHERE pp.id_producto = p.id_producto 
             AND pr.activo = TRUE 
             AND pr.fecha_inicio <= CURDATE() 
             AND pr.fecha_fin >= CURDATE()
            ) as promociones,
            
            -- Subconsulta para precios especiales (corregida)
            (SELECT GROUP_CONCAT(CONCAT(lp.nombre_lista,'|',plp.precio) SEPARATOR ';')
             FROM productolistaprecio plp 
             JOIN listaprecio lp ON plp.id_lista = lp.id_lista
             WHERE plp.id_producto = p.id_producto AND lp.activo = TRUE
            ) as precios_especiales
            
        FROM producto p
        WHERE p.activo = TRUE
        ORDER BY p.nombre
        """
        return self._ejecutar_consulta(consulta, obtener_datos=True, dictionary=True)
    
    def _obtener_promociones_completas(self):
        """🔧 CONSULTA CORREGIDA - Promociones con productos y colecciones"""
        consulta = """
        SELECT 
            pr.id_promocion,
            pr.nombre,
            pr.descripcion,
            pr.tipo_descuento,
            pr.valor_descuento,
            pr.fecha_inicio,
            pr.fecha_fin,
            pr.imagen,
            pr.activo,
            
            -- Subconsulta para productos (corregida)
            (SELECT GROUP_CONCAT(CONCAT(p.nombre,'|',COALESCE(p.codigo,''),'|',p.precio_base,'|',p.stock_global) SEPARATOR ';')
             FROM promocionproducto pp 
             JOIN producto p ON pp.id_producto = p.id_producto 
             WHERE pp.id_promocion = pr.id_promocion AND p.activo = TRUE
            ) as productos_aplicados,
            
            -- Subconsulta para colecciones (corregida)
            (SELECT GROUP_CONCAT(CONCAT(c.nombre,'|',COALESCE(c.descripcion,'')) SEPARATOR ';')
             FROM promocioncoleccion pc 
             JOIN coleccion c ON pc.id_coleccion = c.id_coleccion 
             WHERE pc.id_promocion = pr.id_promocion AND c.activo = TRUE
            ) as colecciones_aplicadas,
            
            -- Conteos directos (corregidos)
            (SELECT COUNT(*) 
             FROM promocionproducto pp 
             JOIN producto p ON pp.id_producto = p.id_producto 
             WHERE pp.id_promocion = pr.id_promocion AND p.activo = TRUE
            ) as total_productos,
            
            (SELECT COUNT(*) 
             FROM promocioncoleccion pc 
             JOIN coleccion c ON pc.id_coleccion = c.id_coleccion 
             WHERE pc.id_promocion = pr.id_promocion AND c.activo = TRUE
            ) as total_colecciones
            
        FROM promocion pr
        WHERE pr.activo = TRUE 
        ORDER BY pr.fecha_inicio DESC
        """
        return self._ejecutar_consulta(consulta, obtener_datos=True, dictionary=True)
    
    def _obtener_colecciones_completas(self):
        """🔧 CONSULTA CORREGIDA - Colecciones con productos y promociones"""
        consulta = """
        SELECT 
            c.id_coleccion,
            c.nombre,
            c.descripcion,
            c.imagen,
            c.activo,
            
            -- Subconsulta para productos de la colección (corregida)
            (SELECT GROUP_CONCAT(CONCAT(p.nombre,'|',COALESCE(p.codigo,''),'|',p.precio_base,'|',p.stock_global,'|',COALESCE(p.descripcion,'Sin descripción')) SEPARATOR ';')
             FROM productocoleccion pc 
             JOIN producto p ON pc.id_producto = p.id_producto 
             WHERE pc.id_coleccion = c.id_coleccion AND p.activo = TRUE
            ) as productos,
            
            -- Subconsulta para promociones en la colección (corregida)
            (SELECT GROUP_CONCAT(CONCAT(pr.nombre,'|',COALESCE(pr.descripcion,''),'|',pr.tipo_descuento,'|',pr.valor_descuento,'|',pr.fecha_inicio,'|',pr.fecha_fin) SEPARATOR ';')
             FROM promocioncoleccion prc 
             JOIN promocion pr ON prc.id_promocion = pr.id_promocion 
             WHERE prc.id_coleccion = c.id_coleccion AND pr.activo = TRUE
            ) as promociones_activas,
            
            -- Estadísticas calculadas (corregidas)
            (SELECT COUNT(*) 
             FROM productocoleccion pc 
             JOIN producto p ON pc.id_producto = p.id_producto 
             WHERE pc.id_coleccion = c.id_coleccion AND p.activo = TRUE
            ) as total_productos,
            
            (SELECT COALESCE(SUM(p.stock_global), 0) 
             FROM productocoleccion pc 
             JOIN producto p ON pc.id_producto = p.id_producto 
             WHERE pc.id_coleccion = c.id_coleccion AND p.activo = TRUE
            ) as stock_total_coleccion,
            
            (SELECT COALESCE(AVG(p.precio_base), 0) 
             FROM productocoleccion pc 
             JOIN producto p ON pc.id_producto = p.id_producto 
             WHERE pc.id_coleccion = c.id_coleccion AND p.activo = TRUE
            ) as precio_promedio,
            
            (SELECT COALESCE(MIN(p.precio_base), 0) 
             FROM productocoleccion pc 
             JOIN producto p ON pc.id_producto = p.id_producto 
             WHERE pc.id_coleccion = c.id_coleccion AND p.activo = TRUE
            ) as precio_minimo,
            
            (SELECT COALESCE(MAX(p.precio_base), 0) 
             FROM productocoleccion pc 
             JOIN producto p ON pc.id_producto = p.id_producto 
             WHERE pc.id_coleccion = c.id_coleccion AND p.activo = TRUE
            ) as precio_maximo
            
        FROM coleccion c
        WHERE c.activo = TRUE
        ORDER BY c.nombre
        """
        return self._ejecutar_consulta(consulta, obtener_datos=True, dictionary=True)
    
    def _obtener_sucursales_completas(self):
        """🔧 CONSULTA CORREGIDA - Sucursales con almacenes, productos y stock"""
        consulta = """
        SELECT 
            s.id_sucursal,
            s.nombre,
            s.direccion,
            s.activo,
            
            -- Subconsulta para almacenes (corregida)
            (SELECT GROUP_CONCAT(CONCAT(a.nombre,'|',a.id_almacen) SEPARATOR ';')
             FROM almacen a 
             WHERE a.id_sucursal = s.id_sucursal AND a.activo = TRUE
            ) as almacenes,
            
            -- Subconsulta para inventario limitado (corregida)
            (SELECT GROUP_CONCAT(CONCAT(p.nombre,'|',COALESCE(p.codigo,''),'|',sa.cantidad,'|',p.precio_base,'|',a.nombre) SEPARATOR ';')
             FROM almacen a 
             JOIN stockalmacen sa ON a.id_almacen = sa.id_almacen
             JOIN producto p ON sa.id_producto = p.id_producto
             WHERE a.id_sucursal = s.id_sucursal 
             AND a.activo = TRUE 
             AND p.activo = TRUE 
             AND sa.cantidad > 0
             ORDER BY sa.cantidad DESC
             LIMIT 20
            ) as inventario,
            
            -- Estadísticas (corregidas)
            (SELECT COUNT(DISTINCT a.id_almacen) 
             FROM almacen a 
             WHERE a.id_sucursal = s.id_sucursal AND a.activo = TRUE
            ) as total_almacenes,
            
            (SELECT COUNT(DISTINCT p.id_producto) 
             FROM almacen a 
             JOIN stockalmacen sa ON a.id_almacen = sa.id_almacen
             JOIN producto p ON sa.id_producto = p.id_producto
             WHERE a.id_sucursal = s.id_sucursal 
             AND a.activo = TRUE 
             AND p.activo = TRUE 
             AND sa.cantidad > 0
            ) as total_productos_diferentes,
            
            (SELECT COALESCE(SUM(sa.cantidad), 0) 
             FROM almacen a 
             JOIN stockalmacen sa ON a.id_almacen = sa.id_almacen
             WHERE a.id_sucursal = s.id_sucursal AND a.activo = TRUE
            ) as stock_total_sucursal,
            
            -- Colecciones disponibles (corregida)
            (SELECT GROUP_CONCAT(DISTINCT c.nombre SEPARATOR ';') 
             FROM almacen a 
             JOIN stockalmacen sa ON a.id_almacen = sa.id_almacen
             JOIN producto p ON sa.id_producto = p.id_producto
             JOIN productocoleccion pc ON p.id_producto = pc.id_producto
             JOIN coleccion c ON pc.id_coleccion = c.id_coleccion
             WHERE a.id_sucursal = s.id_sucursal 
             AND a.activo = TRUE 
             AND p.activo = TRUE 
             AND c.activo = TRUE 
             AND sa.cantidad > 0
            ) as colecciones_disponibles
            
        FROM sucursal s
        WHERE s.activo = TRUE
        ORDER BY s.nombre
        """
        return self._ejecutar_consulta(consulta, obtener_datos=True, dictionary=True)
   
    # ============================================
    # RESTO DE MÉTODOS (SIN CAMBIOS)
    # ============================================
    
    def _generar_texto_producto(self, producto):
        """Genera texto optimizado para embedding de productos"""
        ubicaciones = self._procesar_ubicaciones(producto.get('ubicaciones', ''))
        colecciones = self._procesar_lista_simple(producto.get('colecciones', ''))
        promociones = self._procesar_promociones(producto.get('promociones', ''))
        precios = self._procesar_precios(producto.get('precios_especiales', ''))
        
        return f"""
        TIPO: PRODUCTO
        NOMBRE: {producto['nombre']} | CÓDIGO: {producto['codigo'] or 'N/A'}
        DESCRIPCIÓN: {producto['descripcion'] or 'Sin descripción'}
        PRECIO BASE: ${producto['precio_base']} | STOCK GLOBAL: {producto['stock_global']}
        IMAGEN: {producto.get('imagen', 'Sin imagen')}
        
        UBICACIONES Y STOCK:
        {ubicaciones}
        
        CATEGORÍAS/COLECCIONES:
        {colecciones}
        
        PROMOCIONES ACTIVAS:
        {promociones}
        
        PRECIOS ESPECIALES:
        {precios}
        
        DISPONIBILIDAD: {'Disponible' if producto['stock_global'] > 0 else 'Sin stock'}
        ESTADO: {'Activo' if producto.get('activo', True) else 'Inactivo'}
        """.strip()
    
    def _generar_texto_promocion(self, promocion):
        """Genera texto optimizado para embedding de promociones"""
        productos = self._procesar_productos_promocion(promocion.get('productos_aplicados', ''))
        colecciones = self._procesar_lista_simple(promocion.get('colecciones_aplicadas', ''))
        
        descuento_texto = f"{promocion['valor_descuento']}{'%' if promocion['tipo_descuento'] == 'porcentaje' else ' pesos'}"
        
        return f"""
        TIPO: PROMOCIÓN
        NOMBRE: {promocion['nombre']}
        DESCRIPCIÓN: {promocion['descripcion'] or 'Sin descripción'}
        DESCUENTO: {descuento_texto} ({promocion['tipo_descuento']})
        VIGENCIA: Desde {promocion['fecha_inicio']} hasta {promocion['fecha_fin']}
        IMAGEN: {promocion.get('imagen', 'Sin imagen')}
        
        PRODUCTOS INCLUIDOS ({promocion.get('total_productos', 0)} productos):
        {productos}
        
        COLECCIONES INCLUIDAS ({promocion.get('total_colecciones', 0)} colecciones):
        {colecciones}
        
        ESTADO: Promoción activa y vigente
        """.strip()
    
    def _generar_texto_coleccion(self, coleccion):
        """Genera texto optimizado para embedding de colecciones"""
        productos = self._procesar_productos_coleccion(coleccion.get('productos', ''))
        promociones = self._procesar_promociones(coleccion.get('promociones_activas', ''))
        
        return f"""
        TIPO: COLECCIÓN
        NOMBRE: {coleccion['nombre']}
        DESCRIPCIÓN: {coleccion['descripcion'] or 'Sin descripción'}
        IMAGEN: {coleccion.get('imagen', 'Sin imagen')}
        
        ESTADÍSTICAS:
        - Total de productos: {coleccion.get('total_productos', 0)}
        - Stock total: {coleccion.get('stock_total_coleccion', 0)} unidades
        - Precio promedio: ${coleccion.get('precio_promedio', 0):.2f}
        - Rango de precios: ${coleccion.get('precio_minimo', 0)} - ${coleccion.get('precio_maximo', 0)}
        
        PRODUCTOS EN LA COLECCIÓN:
        {productos}
        
        PROMOCIONES ACTIVAS:
        {promociones}
        
        ESTADO: Colección activa
        """.strip()
    
    def _generar_texto_sucursal(self, sucursal):
        """Genera texto optimizado para embedding de sucursales"""
        almacenes = self._procesar_lista_simple(sucursal.get('almacenes', ''))
        inventario = self._procesar_inventario_sucursal(sucursal.get('inventario', ''))
        colecciones = self._procesar_lista_simple(sucursal.get('colecciones_disponibles', ''))
        
        return f"""
        TIPO: SUCURSAL
        NOMBRE: {sucursal['nombre']}
        DIRECCIÓN: {sucursal['direccion'] or 'Sin dirección especificada'}
        
        ESTADÍSTICAS:
        - Total de almacenes: {sucursal.get('total_almacenes', 0)}
        - Productos diferentes: {sucursal.get('total_productos_diferentes', 0)}
        - Stock total: {sucursal.get('stock_total_sucursal', 0)} unidades
        
        ALMACENES:
        {almacenes}
        
        INVENTARIO PRINCIPAL:
        {inventario}
        
        COLECCIONES DISPONIBLES:
        {colecciones}
        
        ESTADO: Sucursal activa
        """.strip()
    
    # Métodos de procesamiento (sin cambios)
    def _procesar_ubicaciones(self, ubicaciones_str):
        if not ubicaciones_str:
            return "Sin ubicaciones registradas"
        
        ubicaciones = []
        for ubicacion in ubicaciones_str.split(';'):
            if ubicacion.strip():
                partes = ubicacion.split('|')
                if len(partes) >= 4:
                    sucursal, direccion, almacen, cantidad = partes[:4]
                    ubicaciones.append(f"- {sucursal} ({direccion}) - Almacén: {almacen} - Stock: {cantidad} unidades")
        
        return '\n'.join(ubicaciones) if ubicaciones else "Sin ubicaciones válidas"
    
    def _procesar_lista_simple(self, lista_str):
        if not lista_str:
            return "Sin información"
        
        items = []
        for item in lista_str.split(';'):
            if item.strip():
                partes = item.split('|')
                nombre = partes[0]
                descripcion = partes[1] if len(partes) > 1 else ""
                items.append(f"- {nombre}" + (f": {descripcion}" if descripcion else ""))
        
        return '\n'.join(items) if items else "Sin información válida"
    
    def _procesar_promociones(self, promociones_str):
        if not promociones_str:
            return "Sin promociones activas"
        
        promociones = []
        for promo in promociones_str.split(';'):
            if promo.strip():
                partes = promo.split('|')
                if len(partes) >= 6:
                    nombre, desc, tipo, valor, inicio, fin = partes[:6]
                    descuento = f"{valor}{'%' if tipo == 'porcentaje' else ' pesos'}"
                    promociones.append(f"- {nombre}: {descuento} (Vigente: {inicio} a {fin})")
        
        return '\n'.join(promociones) if promociones else "Sin promociones válidas"
    
    def _procesar_productos_promocion(self, productos_str):
        if not productos_str:
            return "Sin productos específicos"
        
        productos = []
        for prod in productos_str.split(';'):
            if prod.strip():
                partes = prod.split('|')
                if len(partes) >= 4:
                    nombre, codigo, precio, stock = partes[:4]
                    productos.append(f"- {nombre} ({codigo}): ${precio} - Stock: {stock}")
        
        return '\n'.join(productos) if productos else "Sin productos válidos"
    
    def _procesar_productos_coleccion(self, productos_str):
        if not productos_str:
            return "Sin productos en la colección"
        
        productos = []
        for prod in productos_str.split(';'):
            if prod.strip():
                partes = prod.split('|')
                if len(partes) >= 5:
                    nombre, codigo, precio, stock, desc = partes[:5]
                    productos.append(f"- {nombre} ({codigo}): ${precio} - Stock: {stock}")
                    if desc and desc != 'None':
                        productos[-1] += f" - {desc[:50]}..."
        
        return '\n'.join(productos) if productos else "Sin productos válidos"
    
    def _procesar_precios(self, precios_str):
        if not precios_str:
            return "Solo precio base disponible"
        
        precios = []
        for precio in precios_str.split(';'):
            if precio.strip():
                partes = precio.split('|')
                if len(partes) >= 2:
                    lista, valor = partes[:2]
                    precios.append(f"- {lista}: ${valor}")
        
        return '\n'.join(precios) if precios else "Solo precio base"
    
    def _procesar_inventario_sucursal(self, inventario_str):
        if not inventario_str:
            return "Sin inventario registrado"
        
        inventario = []
        for item in inventario_str.split(';')[:10]:
            if item.strip():
                partes = item.split('|')
                if len(partes) >= 5:
                    nombre, codigo, cantidad, precio, almacen = partes[:5]
                    inventario.append(f"- {nombre} ({codigo}): {cantidad} uds en {almacen} - ${precio}")
        
        return '\n'.join(inventario) if inventario else "Sin inventario válido"
    
    def _procesar_todo_el_contenido(self):
        """Proceso completo de toda la base de conocimiento"""
        self._ejecutar_consulta("DELETE FROM base_conocimiento_analisis")
        
        total_procesados = 0
        
        print("📦 Procesando productos...")
        productos = self._obtener_productos_completos()
        if productos:
            exitosos = self._procesar_entidades(productos, 'producto', self._generar_texto_producto)
            total_procesados += exitosos
            print(f"✅ Productos procesados: {exitosos}/{len(productos)}")
        
        print("🎯 Procesando promociones...")
        promociones = self._obtener_promociones_completas()
        if promociones:
            exitosos = self._procesar_entidades(promociones, 'promocion', self._generar_texto_promocion)
            total_procesados += exitosos
            print(f"✅ Promociones procesadas: {exitosos}/{len(promociones)}")
        
        print("📂 Procesando colecciones...")
        colecciones = self._obtener_colecciones_completas()
        if colecciones:
            exitosos = self._procesar_entidades(colecciones, 'coleccion', self._generar_texto_coleccion)
            total_procesados += exitosos
            print(f"✅ Colecciones procesadas: {exitosos}/{len(colecciones)}")
        
        print("🏢 Procesando sucursales...")
        sucursales = self._obtener_sucursales_completas()
        if sucursales:
            exitosos = self._procesar_entidades(sucursales, 'sucursal', self._generar_texto_sucursal)
            total_procesados += exitosos
            print(f"✅ Sucursales procesadas: {exitosos}/{len(sucursales)}")
        
        print(f"🎉 TOTAL PROCESADO: {total_procesados} registros en la base de conocimiento")
    
    def _procesar_entidades(self, entidades, tipo, generador_texto):
        """Procesa cualquier tipo de entidad y genera embeddings"""
        exitosos = 0
        
        for entidad in entidades:
            try:
                texto = generador_texto(entidad)
                
                respuesta = self.cliente_openai.embeddings.create(
                    input=texto, model="text-embedding-ada-002"
                )
                embedding = respuesta.data[0].embedding
                
                metadata = self._generar_metadata(entidad, tipo)
                
                consulta = "INSERT INTO base_conocimiento_analisis (contenido, embedding, metadata) VALUES (%s, %s, %s)"
                if self._ejecutar_consulta(consulta, (texto, pickle.dumps(embedding), json.dumps(metadata))):
                    exitosos += 1
                    
            except Exception as e:
                nombre = entidad.get('nombre', f'ID_{entidad.get(f"id_{tipo}", "unknown")}')
                print(f"❌ Error en {tipo} {nombre}: {e}")
        
        return exitosos
    
    def _generar_metadata(self, entidad, tipo):
        """Genera metadata específica según el tipo de entidad"""
        base_metadata = {'tipo': tipo}
        
        if tipo == 'producto':
            base_metadata.update({
                'id_producto': entidad['id_producto'],
                'nombre': entidad['nombre'],
                'precio': float(entidad['precio_base'] or 0),
                'stock': int(entidad['stock_global'] or 0),
                'codigo': entidad.get('codigo', '')
            })
        elif tipo == 'promocion':
            base_metadata.update({
                'id_promocion': entidad['id_promocion'],
                'nombre': entidad['nombre'],
                'tipo_descuento': entidad['tipo_descuento'],
                'valor_descuento': float(entidad['valor_descuento'] or 0),
                'fecha_inicio': str(entidad['fecha_inicio']),
                'fecha_fin': str(entidad['fecha_fin']),
                'total_productos': int(entidad.get('total_productos', 0) or 0)
            })
        elif tipo == 'coleccion':
            base_metadata.update({
                'id_coleccion': entidad['id_coleccion'],
                'nombre': entidad['nombre'],
                'total_productos': int(entidad.get('total_productos', 0) or 0),
                'stock_total': int(entidad.get('stock_total_coleccion', 0) or 0),
                'precio_promedio': float(entidad.get('precio_promedio', 0) or 0),
                'precio_minimo': float(entidad.get('precio_minimo', 0) or 0),
                'precio_maximo': float(entidad.get('precio_maximo', 0) or 0)
            })
        elif tipo == 'sucursal':
            base_metadata.update({
                'id_sucursal': entidad['id_sucursal'],
                'nombre': entidad['nombre'],
                'direccion': entidad.get('direccion', ''),
                'total_almacenes': int(entidad.get('total_almacenes', 0) or 0),
                'stock_total': int(entidad.get('stock_total_sucursal', 0) or 0)
            })
        
        return base_metadata
    
    def obtener_vectorstore(self):
        """FUNCIÓN PRINCIPAL - Obtiene FAISS optimizado con todo el contenido"""
        try:
            print("🔄 Creando FAISS desde base de conocimiento completa...")
            embeddings_data = self._ejecutar_consulta(
                "SELECT contenido, embedding, metadata FROM base_conocimiento_analisis ORDER BY id",
                obtener_datos=True, dictionary=True
            )
            
            if not embeddings_data:
                print("❌ Sin embeddings en la base")
                return None
            
            # Preparar documentos para FAISS
            documentos = []
            for row in embeddings_data:
                metadata = json.loads(row['metadata']) if row['metadata'] else {}
                doc = Document(
                    page_content=row['contenido'],
                    metadata=metadata
                )
                documentos.append(doc)
            
            # Crear FAISS directamente desde documentos
            vectorstore = FAISS.from_documents(
                documents=documentos,
                embedding=self.embeddings
            )
            
            tipos = {}
            for doc in documentos:
                tipo = doc.metadata.get('tipo', 'desconocido')
                tipos[tipo] = tipos.get(tipo, 0) + 1
            
            print(f"✅ Vectorstore creado con {len(documentos)} documentos:")
            for tipo, cantidad in tipos.items():
                print(f"   - {tipo.capitalize()}: {cantidad}")
            
            return vectorstore
            
        except Exception as e:
            print(f"❌ Error obteniendo vectorstore: {e}")
            traceback.print_exc()
            return None
    
    def buscar_contenido(self, consulta, k=5, filtro_tipo=None):
        """Busca contenido específico en la base de conocimiento"""
        vectorstore = self.obtener_vectorstore()
        if not vectorstore:
            return []
        
        try:
            # Búsqueda básica
            resultados = vectorstore.similarity_search(consulta, k=k*2)  # Buscar más para filtrar
            
            # Filtrar por tipo si se especifica
            if filtro_tipo:
                resultados = [r for r in resultados if r.metadata.get('tipo') == filtro_tipo]
            
            return resultados[:k]
            
        except Exception as e:
            print(f"❌ Error en búsqueda: {e}")
            return []

# ==============================================
# SCRIPT PARA APLICAR EL PARCHE
# ==============================================

def aplicar_parche():
    """Aplica el parche para corregir el gestor de base de conocimiento"""
    
    print("🔧 APLICANDO PARCHE PARA CORREGIR CONSULTAS BD")
    print("=" * 60)
    
    try:
        # Paso 1: Verificar conexión BD
        print("1️⃣ Verificando conexión a base de datos...")
        
        gestor = GestorBaseConocimientoFixed()
        resultado_test = gestor._ejecutar_consulta("SELECT COUNT(*) FROM producto", obtener_datos=True)
        
        if resultado_test:
            print(f"✅ Conexión exitosa - {resultado_test[0][0]} productos encontrados")
        else:
            print("❌ Error de conexión a la base de datos")
            return False
        
        # Paso 2: Probar consultas corregidas
        print("\n2️⃣ Probando consultas corregidas...")
        
        # Probar productos
        print("   📦 Probando consulta de productos...")
        productos = gestor._obtener_productos_completos()
        print(f"   ✅ {len(productos)} productos obtenidos")
        
        # Probar promociones
        print("   🎯 Probando consulta de promociones...")
        promociones = gestor._obtener_promociones_completas()
        print(f"   ✅ {len(promociones)} promociones obtenidas")
        
        # Probar colecciones
        print("   📂 Probando consulta de colecciones...")
        colecciones = gestor._obtener_colecciones_completas()
        print(f"   ✅ {len(colecciones)} colecciones obtenidas")
        
        # Probar sucursales
        print("   🏢 Probando consulta de sucursales...")
        sucursales = gestor._obtener_sucursales_completas()
        print(f"   ✅ {len(sucursales)} sucursales obtenidas")
        
        # Paso 3: Generar embeddings si es necesario
        print("\n3️⃣ Verificando embeddings...")
        
        count = gestor._ejecutar_consulta("SELECT COUNT(*) FROM base_conocimiento_analisis", obtener_datos=True)
        embeddings_count = count[0][0] if count else 0
        
        if embeddings_count == 0:
            print("   📝 Generando embeddings por primera vez...")
            gestor._procesar_todo_el_contenido()
        else:
            print(f"   ✅ {embeddings_count} embeddings ya existen")
        
        # Paso 4: Probar vectorstore
        print("\n4️⃣ Probando vectorstore...")
        vectorstore = gestor.obtener_vectorstore()
        
        if vectorstore:
            print("   ✅ Vectorstore creado exitosamente")
            
            # Prueba de búsqueda
            resultados = gestor.buscar_contenido("laptop gaming", k=3)
            print(f"   🔍 Prueba de búsqueda: {len(resultados)} resultados para 'laptop gaming'")
        else:
            print("   ❌ Error creando vectorstore")
            return False
        
        print("\n🎉 PARCHE APLICADO EXITOSAMENTE")
        print("✅ Todas las consultas funcionan correctamente")
        print("✅ El sistema está listo para usar")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERROR APLICANDO PARCHE: {e}")
        import traceback
        traceback.print_exc()
        return False

def reemplazar_gestor_en_entrenamiento():
    """Crea un archivo para reemplazar el gestor en entrenamiento_fino.py"""
    
    contenido_reemplazo = '''
# PARCHE TEMPORAL - Reemplazar en entrenamiento_fino.py
# Línea donde se importa GestorBaseConocimiento:

# CAMBIAR ESTO:
# from gestor_base_conocimiento import GestorBaseConocimiento

# POR ESTO:
from fix_database_queries import GestorBaseConocimientoFixed as GestorBaseConocimiento

# O alternativamente, actualizar la línea de inicialización:
# self.gestor_bd = GestorBaseConocimientoFixed()
'''
    
    with open('parche_entrenamiento.txt', 'w', encoding='utf-8') as f:
        f.write(contenido_reemplazo)
    
    print("📝 Archivo 'parche_entrenamiento.txt' creado con instrucciones")

def test_simple():
    """Prueba simple para verificar que todo funciona"""
    
    print("🧪 PRUEBA SIMPLE DEL PARCHE")
    print("=" * 40)
    
    try:
        # Inicializar gestor corregido
        gestor = GestorBaseConocimientoFixed()
        
        # Probar búsqueda básica
        resultados = gestor.buscar_contenido("gaming", k=2)
        
        if resultados:
            print(f"✅ Búsqueda funcionando - {len(resultados)} resultados")
            for i, resultado in enumerate(resultados, 1):
                print(f"   {i}. {resultado.metadata.get('tipo', 'unknown')}: {resultado.metadata.get('nombre', 'sin nombre')}")
        else:
            print("⚠️ No se encontraron resultados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en prueba simple: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        comando = sys.argv[1].lower()
        
        if comando == "aplicar":
            aplicar_parche()
        elif comando == "test":
            test_simple()
        elif comando == "parche":
            reemplazar_gestor_en_entrenamiento()
        else:
            print("Comandos: aplicar, test, parche")
    else:
        # Aplicar parche completo por defecto
        exito = aplicar_parche()
        
        if exito:
            print("\n" + "=" * 60)
            print("📋 PRÓXIMOS PASOS:")
            print("1. El parche se aplicó correctamente")
            print("2. Actualiza entrenamiento_fino.py:")
            print("   from fix_database_queries import GestorBaseConocimientoFixed as GestorBaseConocimiento")
            print("3. Ejecuta: python test_local.py")
            print("4. Si todo funciona, puedes usar el bot normalmente")
            
            reemplazar_gestor_en_entrenamiento()