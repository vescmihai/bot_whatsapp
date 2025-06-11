import mysql.connector
import json
import os
import base64
from datetime import datetime
from generar_pdf import GeneradorPDF
from entrenamiento_fino import EntrenamientoFino

class EnvioPDFsEmails:
    def __init__(self):
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'bot_productos_db',
            'charset': 'utf8mb4'
        }
        
        self.entrenamiento_fino = EntrenamientoFino()
        self.generador_pdf = GeneradorPDF(self.entrenamiento_fino)
        self.carpeta_salida = "emails_automaticos"
        
        if not os.path.exists(self.carpeta_salida):
            os.makedirs(self.carpeta_salida)
    
    def procesar_clientes_para_email(self):
        """Genera PDFs y prepara archivo para Power Automate"""
        print("🚀 Iniciando proceso de emails automáticos...")
        
        # 1. Obtener clientes con email
        clientes = self._obtener_clientes_con_email()
        if not clientes:
            return self._crear_resultado_vacio()
        
        # 2. Generar PDFs y preparar datos
        datos_envio = []
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        for cliente in clientes:
            try:
                # Generar PDF
                pdf_base64 = self.generador_pdf.intereses_usuario(cliente['telefono'])
                
                if isinstance(pdf_base64, str) and len(pdf_base64) > 100:
                    # Guardar PDF
                    archivo_pdf = self._guardar_pdf(cliente, pdf_base64, timestamp)
                    
                    # Preparar datos para email
                    datos_envio.append({
                        'nombre': cliente['nombre'] or f"Cliente {cliente['telefono']}",
                        'email': cliente['email'],
                        'telefono': cliente['telefono'],
                        'archivo_pdf': archivo_pdf,
                        'asunto': f"📊 Tu Reporte Gaming Personalizado - {datetime.now().strftime('%d/%m/%Y')}",
                        'estado': 'pendiente'
                    })
                    
                    print(f"✅ PDF generado: {cliente['nombre']} ({cliente['email']})")
                
            except Exception as e:
                print(f"❌ Error con cliente {cliente['telefono']}: {e}")
        
        # 3. Crear archivo de control para PAD
        return self._crear_archivo_control(datos_envio, timestamp)
    
    def _obtener_clientes_con_email(self):
        """Obtiene clientes activos con email configurado"""
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT DISTINCT c.id_cliente, c.telefono, c.nombre, c.email
                FROM cliente c
                INNER JOIN conversacion conv ON c.id_cliente = conv.id_cliente
                WHERE c.activo = TRUE 
                AND c.email IS NOT NULL 
                AND c.email != ''
                AND c.email LIKE '%@%'
                AND conv.fecha_inicio >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
                ORDER BY c.fecha_registro DESC
            """)
            
            clientes = cursor.fetchall()
            conexion.close()
            
            print(f"📧 Encontrados {len(clientes)} clientes con email")
            return clientes
            
        except Exception as e:
            print(f"❌ Error obteniendo clientes: {e}")
            return []
    
    def _guardar_pdf(self, cliente, pdf_base64, timestamp):
        """Guarda PDF en archivo y retorna ruta"""
        try:
            pdf_data = base64.b64decode(pdf_base64)
            telefono_limpio = cliente['telefono'].replace('+', '').replace(' ', '').replace('-', '')
            nombre_archivo = f"pdf_{telefono_limpio}_{timestamp}.pdf"
            ruta_completa = os.path.abspath(os.path.join(self.carpeta_salida, nombre_archivo))
            
            with open(ruta_completa, "wb") as f:
                f.write(pdf_data)
            
            return ruta_completa
            
        except Exception as e:
            print(f"❌ Error guardando PDF: {e}")
            return None
    
    def _crear_archivo_control(self, datos_envio, timestamp):
        """Crea archivo JSON para Power Automate Desktop"""
        try:
            archivo_control = os.path.join(self.carpeta_salida, f"envios_{timestamp}.json")
            
            resultado = {
                'timestamp': timestamp,
                'fecha_proceso': datetime.now().isoformat(),
                'total_clientes': len(datos_envio),
                'clientes': datos_envio,
                'carpeta_pdfs': os.path.abspath(self.carpeta_salida)
            }
            
            with open(archivo_control, 'w', encoding='utf-8') as f:
                json.dump(resultado, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Archivo de control creado: {archivo_control}")
            return archivo_control
            
        except Exception as e:
            print(f"❌ Error creando archivo de control: {e}")
            return None
    
    def _crear_resultado_vacio(self):
        """Crea resultado cuando no hay clientes"""
        print("⚠️ No se encontraron clientes con email para procesar")
        return None

def main():
    """Función principal"""
    enviador = EnvioPDFsEmails()
    archivo_control = enviador.procesar_clientes_para_email()
    
    if archivo_control:
        print(f"🎯 Proceso completado. Archivo para PAD: {archivo_control}")
        return archivo_control
    else:
        print("❌ No se pudo completar el proceso")
        return None

if __name__ == "__main__":
    main()