import os
import sys
import json
import logging
import base64
import mysql.connector
from datetime import datetime, timedelta
from pathlib import Path

# ⚠️ IMPORTANTE: Cambiar esta ruta por la ruta de tu proyecto bot
sys.path.append(r'C:\Users\vescm\Desktop\backend-topicos-2-main')  # ← CAMBIAR AQUÍ

from generar_pdf import GeneradorPDF
from entrenamiento_fino import EntrenamientoFino

class EnviadorEmailPDFs:
    def __init__(self, config_path="config_email.json"):
        """Inicializar el enviador de emails con PDFs"""
        self.config = self.cargar_configuracion(config_path)
        self.setup_logging()
        
        # Inicializar componentes del bot
        print("🤖 Inicializando componentes del bot...")
        self.entrenamiento_fino = EntrenamientoFino()
        self.generador_pdf = GeneradorPDF(self.entrenamiento_fino)
        
        # Configuración BD
        self.db_config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'bot_productos_db',
            'charset': 'utf8mb4'
        }
        
        print("✅ Sistema inicializado correctamente")
    
    def cargar_configuracion(self, config_path):
        """Cargar configuración desde archivo JSON"""
        config_default = {
            "email_remitente": "topicos_vescmihai@outlook.com",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "email_password": "Nahomi0609",
            "asunto_email": "📊 Tu Reporte Gaming Personalizado - Productos de tu Interés",
            "dias_actividad_minima": 7,
            "limite_clientes_por_envio": 10,
            "carpeta_pdfs_temp": "C:\\EmailAutomation\\temp_pdfs",
            "carpeta_logs": "C:\\EmailAutomation\\logs"
        }
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            return {**config_default, **config}
        except FileNotFoundError:
            # Crear archivo de configuración por defecto
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_default, f, indent=4, ensure_ascii=False)
            print(f"✅ Archivo de configuración creado: {config_path}")
            print("⚠️  IMPORTANTE: Edita config_email.json con tus datos reales")
            return config_default
    
    def setup_logging(self):
        """Configurar sistema de logs"""
        log_dir = Path(self.config['carpeta_logs'])
        log_dir.mkdir(exist_ok=True)
        
        log_file = log_dir / f"email_envio_{datetime.now().strftime('%Y%m%d')}.log"
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(__name__)
    
    def obtener_clientes_para_envio(self):
        """Obtener clientes elegibles para envío de PDFs"""
        try:
            conexion = mysql.connector.connect(**self.db_config)
            cursor = conexion.cursor(dictionary=True)
            
            # Obtener clientes con actividad reciente y email
            dias_minimos = self.config['dias_actividad_minima']
            limite = self.config['limite_clientes_por_envio']
            
            query = """
            SELECT DISTINCT c.id_cliente, c.telefono, c.nombre, c.email,
                   COUNT(DISTINCT conv.id_conversacion) as total_conversaciones,
                   MAX(conv.fecha_ultima_actividad) as ultima_actividad
            FROM cliente c
            INNER JOIN conversacion conv ON c.id_cliente = conv.id_cliente
            WHERE c.activo = TRUE 
            AND c.email IS NOT NULL 
            AND c.email != ''
            AND conv.fecha_ultima_actividad >= DATE_SUB(NOW(), INTERVAL %s DAY)
            GROUP BY c.id_cliente, c.telefono, c.nombre, c.email
            HAVING total_conversaciones >= 1
            ORDER BY ultima_actividad DESC
            LIMIT %s
            """
            
            cursor.execute(query, (dias_minimos, limite))
            clientes = cursor.fetchall()
            
            self.logger.info(f"📊 Clientes elegibles encontrados: {len(clientes)}")
            
            # Mostrar detalles de clientes encontrados
            for cliente in clientes:
                self.logger.info(f"   - {cliente['nombre']} ({cliente['email']}) - {cliente['total_conversaciones']} conversaciones")
            
            conexion.close()
            return clientes
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo clientes: {e}")
            return []
    
    def generar_pdf_cliente(self, telefono, nombre_cliente):
        """Generar PDF de intereses para un cliente específico"""
        try:
            self.logger.info(f"📄 Generando PDF para: {nombre_cliente} ({telefono})")
            
            # Generar PDF usando el sistema existente
            pdf_base64 = self.generador_pdf.intereses_usuario(telefono)
            
            if isinstance(pdf_base64, str) and len(pdf_base64) > 100:
                # Guardar PDF temporalmente
                pdf_data = base64.b64decode(pdf_base64)
                
                # Crear carpeta temporal si no existe
                temp_dir = Path(self.config['carpeta_pdfs_temp'])
                temp_dir.mkdir(exist_ok=True)
                
                # Nombre del archivo
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                telefono_limpio = telefono.replace('+', '').replace(' ', '').replace('-', '')
                nombre_archivo = f"intereses_{telefono_limpio}_{timestamp}.pdf"
                ruta_pdf = temp_dir / nombre_archivo
                
                # Guardar archivo
                with open(ruta_pdf, 'wb') as f:
                    f.write(pdf_data)
                
                self.logger.info(f"✅ PDF guardado: {ruta_pdf}")
                return str(ruta_pdf)
            else:
                self.logger.warning(f"⚠️ No se pudo generar PDF para {nombre_cliente}: {pdf_base64}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error generando PDF para {nombre_cliente}: {e}")
            return None
    
    def crear_contenido_email(self, nombre_cliente, total_conversaciones):
        """Crear contenido HTML del email"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; }}
                .container {{ max-width: 600px; margin: 0 auto; background: white; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px 20px; text-align: center; }}
                .content {{ padding: 30px 20px; background-color: #f9f9f9; }}
                .footer {{ background-color: #333; color: white; padding: 20px; text-align: center; font-size: 0.9em; }}
                .highlight {{ color: #667eea; font-weight: bold; }}
                .feature {{ background: white; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #667eea; }}
                .btn {{ background: #667eea; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎮 Tu Reporte Gaming Personalizado</h1>
                    <p style="font-size: 1.2em; margin: 0;">¡Hola <span class="highlight">{nombre_cliente}</span>!</p>
                </div>
                
                <div class="content">
                    <h2 style="color: #333;">📊 Análisis de tus Intereses Gaming</h2>
                    <p>Hemos analizado tus <strong>{total_conversaciones}</strong> conversaciones con nuestro asistente gaming y preparado un reporte completamente personalizado para ti.</p>
                    
                    <div class="feature">
                        <h3>🛍️ Productos que te Interesan</h3>
                        <p>Productos específicos identificados basados en tus consultas y preferencias.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>📱 Colecciones Recomendadas</h3>
                        <p>Conjuntos de productos gaming perfectos para tu perfil y necesidades.</p>
                    </div>
                    
                    <div class="feature">
                        <h3>🎉 Promociones Especiales</h3>
                        <p>Ofertas y descuentos exclusivos en productos de tu interés.</p>
                    </div>
                    
                    <div style="background: #e8f4fd; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0;">
                        <h3 style="color: #1976d2; margin-top: 0;">📎 Tu PDF Personalizado</h3>
                        <p>Encontrarás adjunto tu reporte completo con toda la información detallada, precios actualizados y recomendaciones específicas.</p>
                    </div>
                    
                    <h3 style="color: #333;">💬 ¿Tienes Preguntas?</h3>
                    <p>¡Estamos aquí para ayudarte! Puedes:</p>
                    <ul>
                        <li>Responder a este email con tus consultas</li>
                        <li>Contactarnos por WhatsApp para atención inmediata</li>
                        <li>Visitar nuestra tienda para ver los productos en persona</li>
                    </ul>
                </div>
                
                <div class="footer">
                    <p><strong>🤖 Reporte Generado por IA</strong></p>
                    <p>Este análisis fue creado automáticamente basado en tus interacciones con nuestro asistente gaming especializado.</p>
                    <p style="font-size: 0.8em; margin-top: 15px;">📅 Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    def enviar_email_con_pdf(self, cliente, ruta_pdf):
        """Enviar email con PDF adjunto usando Outlook"""
        try:
            import win32com.client as win32
            
            self.logger.info(f"📧 Enviando email a: {cliente['email']}")
            
            # Crear aplicación Outlook
            outlook = win32.Dispatch('outlook.application')
            mail = outlook.CreateItem(0)  # 0 = olMailItem
            
            # Configurar email
            mail.To = cliente['email']
            mail.Subject = self.config['asunto_email']
            
            # Contenido HTML
            contenido_html = self.crear_contenido_email(
                cliente['nombre'], 
                cliente['total_conversaciones']
            )
            mail.HTMLBody = contenido_html
            
            # Adjuntar PDF
            mail.Attachments.Add(ruta_pdf)
            
            # Enviar
            mail.Send()
            
            self.logger.info(f"✅ Email enviado exitosamente a: {cliente['nombre']} ({cliente['email']})")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error enviando email a {cliente['email']}: {e}")
            self.logger.error("💡 Solución: Verificar que Outlook esté abierto y configurado")
            return False
    
    def limpiar_archivos_temporales(self, max_dias=7):
        """Limpiar archivos PDF temporales antiguos"""
        try:
            temp_dir = Path(self.config['carpeta_pdfs_temp'])
            if not temp_dir.exists():
                return
            
            fecha_limite = datetime.now() - timedelta(days=max_dias)
            archivos_eliminados = 0
            
            for archivo in temp_dir.glob("*.pdf"):
                if archivo.stat().st_mtime < fecha_limite.timestamp():
                    archivo.unlink()
                    archivos_eliminados += 1
            
            if archivos_eliminados > 0:
                self.logger.info(f"🧹 Eliminados {archivos_eliminados} archivos temporales antiguos")
                
        except Exception as e:
            self.logger.error(f"❌ Error limpiando archivos temporales: {e}")
    
    def verificar_sistema(self):
        """Verificar que todos los componentes estén funcionando"""
        self.logger.info("🔍 Verificando sistema...")
        
        errores = []
        
        # Verificar conexión BD
        try:
            conexion = mysql.connector.connect(**self.db_config)
            conexion.close()
            self.logger.info("✅ Conexión a base de datos: OK")
        except Exception as e:
            errores.append(f"Base de datos: {e}")
        
        # Verificar Outlook
        try:
            import win32com.client as win32
            outlook = win32.Dispatch('outlook.application')
            self.logger.info("✅ Conexión a Outlook: OK")
        except Exception as e:
            errores.append(f"Outlook: {e}")
        
        # Verificar directorios
        for directorio in [self.config['carpeta_pdfs_temp'], self.config['carpeta_logs']]:
            if not Path(directorio).exists():
                errores.append(f"Directorio no existe: {directorio}")
            else:
                self.logger.info(f"✅ Directorio {directorio}: OK")
        
        if errores:
            self.logger.error("❌ Errores encontrados:")
            for error in errores:
                self.logger.error(f"   - {error}")
            return False
        
        self.logger.info("✅ Verificación del sistema completada - Todo OK")
        return True
    
    def ejecutar_envio_masivo(self):
        """Función principal - Ejecutar envío masivo de PDFs"""
        self.logger.info("🚀 INICIANDO ENVÍO MASIVO DE PDFs POR EMAIL")
        self.logger.info("=" * 60)
        
        # Verificar sistema
        if not self.verificar_sistema():
            self.logger.error("❌ Sistema no está listo - Abortando ejecución")
            return
        
        # Obtener clientes
        clientes = self.obtener_clientes_para_envio()
        
        if not clientes:
            self.logger.info("ℹ️ No hay clientes elegibles para envío")
            self.logger.info("💡 Sugerencias:")
            self.logger.info("   - Verificar que hay clientes con email en la BD")
            self.logger.info("   - Reducir 'dias_actividad_minima' en config")
            self.logger.info("   - Verificar que hay conversaciones recientes")
            return
        
        # Contadores
        exitosos = 0
        fallidos = 0
        
        # Procesar cada cliente
        for i, cliente in enumerate(clientes, 1):
            self.logger.info(f"📧 Procesando cliente {i}/{len(clientes)}: {cliente['nombre']}")
            
            try:
                # Generar PDF
                ruta_pdf = self.generar_pdf_cliente(cliente['telefono'], cliente['nombre'])
                
                if ruta_pdf:
                    # Enviar email
                    if self.enviar_email_con_pdf(cliente, ruta_pdf):
                        exitosos += 1
                    else:
                        fallidos += 1
                else:
                    fallidos += 1
                    self.logger.warning(f"⚠️ No se pudo procesar cliente: {cliente['nombre']}")
                    
            except Exception as e:
                self.logger.error(f"❌ Error procesando cliente {cliente['nombre']}: {e}")
                fallidos += 1
        
        # Resumen final
        self.logger.info("=" * 60)
        self.logger.info(f"📊 RESUMEN DEL ENVÍO:")
        self.logger.info(f"   ✅ Exitosos: {exitosos}")
        self.logger.info(f"   ❌ Fallidos: {fallidos}")
        self.logger.info(f"   📧 Total procesados: {len(clientes)}")
        
        if exitosos > 0:
            self.logger.info(f"   📈 Tasa de éxito: {(exitosos/len(clientes)*100):.1f}%")
        
        # Limpiar archivos temporales
        self.limpiar_archivos_temporales()
        
        self.logger.info("🎯 ENVÍO MASIVO COMPLETADO")
        
        return {
            'exitosos': exitosos,
            'fallidos': fallidos,
            'total': len(clientes)
        }

def main():
    """Función principal"""
    try:
        # Verificar que estamos en el directorio correcto
        if not os.path.exists("config_email.json"):
            print("⚠️ Ejecutando desde directorio incorrecto")
            print("💡 Cambia a: cd C:\\EmailAutomation")
            return
        
        # Crear directorio base si no existe
        base_dir = Path("C:\Users\vescm\Desktop\backend-topicos-2-main")
        base_dir.mkdir(exist_ok=True)
        (base_dir / "logs").mkdir(exist_ok=True)
        (base_dir / "temp_pdfs").mkdir(exist_ok=True)
        
        # Ejecutar envío
        enviador = EnviadorEmailPDFs()
        resultado = enviador.ejecutar_envio_masivo()
        
        # Mostrar resultado final
        if resultado:
            print(f"\n🎉 PROCESO COMPLETADO")
            print(f"✅ Exitosos: {resultado['exitosos']}")
            print(f"❌ Fallidos: {resultado['fallidos']}")
            print(f"📧 Total: {resultado['total']}")
        
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()