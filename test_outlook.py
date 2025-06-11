# Crear archivo test_outlook.py
# Copiar y pegar este código:

import win32com.client as win32

try:
    outlook = win32.Dispatch('outlook.application')
    mail = outlook.CreateItem(0)
    
    mail.To = "vescmihai@gmail.com"  # CAMBIAR POR TU EMAIL
    mail.Subject = "🧪 Prueba de Automatización"
    mail.Body = "Si recibes este email, la automatización funciona correctamente."
    
    print("📧 Enviando email de prueba...")
    mail.Send()
    print("✅ Email enviado correctamente!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("💡 Solución: Asegurar que Outlook esté abierto y configurado")