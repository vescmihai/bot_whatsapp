"""
Script de prueba simple para verificar el sistema de envío de PDFs
Ejecutar ANTES del sistema completo para verificar que todo funciona
"""

import os
import sys
import mysql.connector

def verificar_python():
    """Verificar versión de Python"""
    print("🐍 Verificando Python...")
    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Necesitas Python 3.8+")
        return False

def verificar_dependencias():
    """Verificar que las dependencias estén instaladas"""
    print("\n📦 Verificando dependencias...")
    dependencias = [
        ('mysql.connector', 'mysql-connector-python'),
        ('win32com.client', 'pywin32'),
        ('pathlib', 'built-in'),
        ('base64', 'built-in'),
        ('json', 'built-in')
    ]
    
    todas_ok = True
    for modulo, paquete in dependencias:
        try:
            __import__(modulo)
            print(f"✅ {modulo} - OK")
        except ImportError:
            print(f"❌ {modulo} - Instalar: pip install {paquete}")
            todas_ok = False
    
    return todas_ok

def verificar_directorios():
    """Verificar y crear directorios necesarios"""
    print("\n📁 Verificando directorios...")
    directorios = [
        "C:\\EmailAutomation",
        "C:\\EmailAutomation\\logs", 
        "C:\\EmailAutomation\\temp_pdfs"
    ]
    
    for directorio in directorios:
        if os.path.exists(directorio):
            print(f"✅ {directorio} - Existe")
        else:
            try:
                os.makedirs(directorio, exist_ok=True)
                print(f"✅ {directorio} - Creado")
            except Exception as e:
                print(f"❌ {directorio} - Error: {e}")
                return False
    return True

def verificar_base_datos():
    """Verificar conexión a base de datos"""
    print("\n🗄️ Verificando base de datos...")
    try:
        config = {
            'host': 'localhost',
            'user': 'root',
            'password': '',
            'database': 'bot_productos_db',
            'charset': 'utf8mb4'
        }
        
        conexion = mysql.connector.connect(**config)
        cursor = conexion.cursor()
        
        # Verificar tabla cliente existe
        cursor.execute("SHOW TABLES LIKE 'cliente'")
        if cursor.fetchone():
            print("✅ Tabla 'cliente' - Existe")
        else:
            print("❌ Tabla 'cliente' - No existe")
            return False
        
        # Verificar campo email existe
        cursor.execute("SHOW COLUMNS FROM cliente LIKE 'email'")
        if cursor.fetchone():
            print("✅ Campo 'email' en tabla cliente - Existe")
        else:
            print("❌ Campo 'email' en tabla cliente - No existe")
            print("💡 Ejecutar: ALTER TABLE cliente ADD COLUMN email VARCHAR(255);")
            return False
        
        # Verificar clientes con email
        cursor.execute("SELECT COUNT(*) FROM cliente WHERE email IS NOT NULL AND email != ''")
        count = cursor.fetchone()[0]
        if count > 0:
            print(f"✅ Clientes con email configurado: {count}")
        else:
            print("⚠️ No hay clientes con email configurado")
            print("💡 Agregar email a algún cliente para pruebas")
        
        conexion.close()
        return True
        
    except Exception as e:
        print(f"❌ Error conectando a BD: {e}")
        return False

def verificar_outlook():
    """Verificar que Outlook esté disponible"""
    print("\n📧 Verificando Outlook...")
    try:
        import win32com.client as win32
        outlook = win32.Dispatch('outlook.application')
        print("✅ Outlook - Disponible y configurado")
        return True
    except Exception as e:
        print(f"❌ Outlook - Error: {e}")
        print("💡 Soluciones:")
        print("   - Abrir Outlook manualmente")
        print("   - Configurar una cuenta de email")
        print("   - Instalar Microsoft Outlook")
        return False

def verificar_proyecto_bot():
    """Verificar que el proyecto bot esté accesible"""
    print("\n🤖 Verificando proyecto bot...")
    
    # Rutas comunes donde podría estar el proyecto
    rutas_posibles = [
        r'C:\Users\usuario\Desktop\bot_whatsapp',
        r'C:\bot_whatsapp',
        r'C:\proyecto_bot',
        r'D:\bot_whatsapp'
    ]
    
    print("🔍 Buscando proyecto en rutas comunes...")
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            archivos_bot = ['generar_pdf.py', 'entrenamiento_fino.py']
            archivos_encontrados = [f for f in archivos_bot if os.path.exists(os.path.join(ruta, f))]
            
            if len(archivos_encontrados) == len(archivos_bot):
                print(f"✅ Proyecto bot encontrado en: {ruta}")
                print(f"   Archivos: {', '.join(archivos_encontrados)}")
                return ruta
            else:
                print(f"⚠️ Ruta parcial en {ruta} - Faltan: {set(archivos_bot) - set(archivos_encontrados)}")
    
    print("❌ Proyecto bot no encontrado en rutas comunes")
    print("💡 Necesitas:")
    print("   1. Ubicar tu proyecto bot")
    print("   2. Actualizar la línea ~15 en flujo_email_pdfs.py")
    print("   3. sys.path.append(r'RUTA_A_TU_PROYECTO')")
    return None

def verificar_archivos_script():
    """Verificar que los archivos del script estén en lugar correcto"""
    print("\n📄 Verificando archivos del script...")
    
    archivos_necesarios = [
        "C:\\EmailAutomation\\flujo_email_pdfs.py",
        "C:\\EmailAutomation\\config_email.json"
    ]
    
    for archivo in archivos_necesarios:
        if os.path.exists(archivo):
            print(f"✅ {os.path.basename(archivo)} - Existe")
        else:
            print(f"❌ {os.path.basename(archivo)} - No existe")
            return False
    
    return True

def main():
    """Ejecutar todas las verificaciones"""
    print("🔍 VERIFICACIÓN COMPLETA DEL SISTEMA")
    print("=" * 50)
    
    verificaciones = [
        ("Python", verificar_python),
        ("Dependencias", verificar_dependencias), 
        ("Directorios", verificar_directorios),
        ("Base de Datos", verificar_base_datos),
        ("Outlook", verificar_outlook),
        ("Proyecto Bot", verificar_proyecto_bot),
        ("Archivos Script", verificar_archivos_script)
    ]
    
    resultados = {}
    
    for nombre, funcion in verificaciones:
        try:
            resultado = funcion()
            resultados[nombre] = resultado
        except Exception as e:
            print(f"❌ Error en verificación {nombre}: {e}")
            resultados[nombre] = False
    
    # Resumen final
    print("\n" + "=" * 50)
    print("📊 RESUMEN DE VERIFICACIONES")
    print("=" * 50)
    
    exitosas = 0
    for nombre, resultado in resultados.items():
        estado = "✅ OK" if resultado else "❌ FALLA"
        print(f"{nombre:<20}: {estado}")
        if resultado:
            exitosas += 1
    
    print(f"\n🎯 Resultado: {exitosas}/{len(verificaciones)} verificaciones exitosas")
    
    if exitosas == len(verificaciones):
        print("🎉 ¡SISTEMA LISTO PARA USAR!")
        print("▶️ Puedes ejecutar: python flujo_email_pdfs.py")
    else:
        print("⚠️ Solucionar problemas antes de continuar")
        print("📋 Revisar los ❌ arriba para ver qué falta")

if __name__ == "__main__":
    main()