import mysql.connector
import json
import os
import base64
from datetime import datetime
from generar_pdf import GeneradorPDF
from entrenamiento_fino import EntrenamientoFino

class GeneradorPDFsMasivo:
    def __init__(self):
        # Configuración de BD
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'bot_productos_db',
            'charset': 'utf8mb4'
        }
        
        # Inicializar generadores
        self.entrenamiento_fino = EntrenamientoFino()
        self.generador_pdf = GeneradorPDF(self.entrenamiento_fino)
        
        # Carpeta de salida
        self.carpeta_pdfs = "pdfs_para_envio"
        if not os.path.exists(self.carpeta_pdfs):
            os.makedirs(self.carpeta_pdfs)
    
    def obtener_clientes_activos(self):
        """Obtiene todos los clientes activos que tienen conversaciones"""
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor(dictionary=True)
            
            # Obtener clientes con conversaciones recientes (últimos 30 días)
            cursor.execute("""
                SELECT DISTINCT c.id_cliente, c.telefono, c.nombre, c.email
                FROM cliente c
                INNER JOIN conversacion conv ON c.id_cliente = conv.id_cliente
                WHERE c.activo = TRUE 
                AND conv.fecha_inicio >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                ORDER BY c.fecha_registro DESC
            """)
            
            clientes = cursor.fetchall()
            conexion.close()
            return clientes
            
        except Exception as e:
            print(f"❌ Error obteniendo clientes: {e}")
            return []
    
    def generar_pdfs_todos_clientes(self):
        """Genera PDFs para todos los clientes activos"""
        print("🚀 Iniciando generación masiva de PDFs...")
        
        clientes = self.obtener_clientes_activos()
        if not clientes:
            print("⚠️ No se encontraron clientes activos")
            return []
        
        archivos_generados = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        for cliente in clientes:
            try:
                telefono = cliente['telefono']
                nombre_cliente = cliente['nombre'] or f"Cliente_{telefono}"
                email = cliente.get('email', '')
                
                print(f"📄 Generando PDF para: {nombre_cliente} ({telefono})")
                
                # Generar PDF de intereses
                pdf_base64 = self.generador_pdf.intereses_usuario(telefono)
                
                if isinstance(pdf_base64, str) and len(pdf_base64) > 100:
                    # Guardar PDF en archivo
                    pdf_data = base64.b64decode(pdf_base64)
                    
                    # Limpiar teléfono para nombre de archivo
                    telefono_limpio = telefono.replace('+', '').replace(' ', '').replace('-', '')
                    nombre_archivo = f"intereses_{telefono_limpio}_{timestamp}.pdf"
                    ruta_archivo = os.path.join(self.carpeta_pdfs, nombre_archivo)
                    
                    with open(ruta_archivo, "wb") as archivo:
                        archivo.write(pdf_data)
                    
                    # Información del archivo generado
                    info_archivo = {
                        'telefono': telefono,
                        'nombre_cliente': nombre_cliente,
                        'email': email,
                        'archivo_pdf': ruta_archivo,
                        'nombre_archivo': nombre_archivo,
                        'tamaño_kb': len(pdf_data) // 1024,
                        'fecha_generacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    archivos_generados.append(info_archivo)
                    print(f"✅ PDF generado: {nombre_archivo} ({info_archivo['tamaño_kb']} KB)")
                    
                else:
                    print(f"❌ Error generando PDF para {nombre_cliente}: {pdf_base64}")
                    
            except Exception as e:
                print(f"❌ Error procesando cliente {cliente.get('nombre', 'N/A')}: {e}")
        
        # Generar archivo de control para Power Automate
        self.generar_archivo_control(archivos_generados)
        
        print(f"🎉 Proceso completado: {len(archivos_generados)} PDFs generados")
        return archivos_generados
    
    def generar_archivo_control(self, archivos_info):
        """Genera archivo CSV con información para Power Automate"""
        try:
            archivo_control = os.path.join(self.carpeta_pdfs, "control_envios.csv")
            
            with open(archivo_control, "w", encoding="utf-8") as f:
                # Encabezados
                f.write("telefono,nombre_cliente,email,archivo_pdf,nombre_archivo,tamaño_kb,fecha_generacion\n")
                
                # Datos
                for info in archivos_info:
                    f.write(f"{info['telefono']},{info['nombre_cliente']},{info['email']},{info['archivo_pdf']},{info['nombre_archivo']},{info['tamaño_kb']},{info['fecha_generacion']}\n")
            
            print(f"✅ Archivo de control generado: {archivo_control}")
            
        except Exception as e:
            print(f"❌ Error generando archivo de control: {e}")

def main():
    """Función principal para ejecutar desde Power Automate"""
    generador = GeneradorPDFsMasivo()
    archivos = generador.generar_pdfs_todos_clientes()
    
    # Crear resumen
    resumen = {
        'total_generados': len(archivos),
        'fecha_proceso': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'carpeta_salida': generador.carpeta_pdfs
    }
    
    # Guardar resumen en JSON
    with open(os.path.join(generador.carpeta_pdfs, "resumen_proceso.json"), "w") as f:
        json.dump(resumen, f, indent=2)
    
    print(f"📊 Resumen guardado en resumen_proceso.json")
    return resumen

if __name__ == "__main__":
    main()