
import requests
import json
import mysql.connector
import pickle
import os
import io
from datetime import datetime
from openai import OpenAI
from gestor_base_conocimiento import GestorBaseConocimiento
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document

class EntrenamientoFino:
    def __init__(self):
        # Tu configuración original
        self.api_key = ""
        self.endpoint = 'https://api.openai.com/v1/chat/completions'
        
        self.cliente_openai = OpenAI(api_key=self.api_key)
        self.gestor_bd = GestorBaseConocimiento()
        
        self.headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }
        
        # 🔥 CAMBIO PRINCIPAL: Usar la nueva función optimizada
        print("⚡ Cargando base de conocimiento...")
        self.base_conocimiento = self.gestor_bd.obtener_vectorstore()  # ← CAMBIO AQUÍ
        
        # Variables para QA
        self.llm = None
        self.qa = None
        
        if self.base_conocimiento:
            print("✅ EntrenamientoFino inicializado - LISTO PARA USAR")
        else:
            print("❌ Error inicializando base de conocimiento")
    
    def configurar_qa(self):
        """Tu configuración original - SIN CAMBIOS."""
        try:
            if self.base_conocimiento is None:
                print("❌ Base de conocimiento no disponible")
                return False
            
            # Tu modelo único
            self.llm = ChatOpenAI(
                openai_api_key=self.api_key,
                model_name="gpt-4-turbo",
                temperature=0.2
            )
            
            # Tu configuración original
            self.qa = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.base_conocimiento.as_retriever(
                    search_kwargs={
                        "k": 10,
                        "fetch_k": 20,
                        "lambda_mult": 0.8
                    }
                ),
                return_source_documents=True
            )
            
            print("✅ RetrievalQA configurado")
            return True
            
        except Exception as e:
            print(f"❌ Error configurando QA: {e}")
            return False
    
    def obtener_informacion_modelo(self, roleOf_system, roelOf_user):
        """Función actualizada con invoke en lugar de __call__"""
        try:
            # Configurar QA si es necesario
            if self.qa is None:
                if not self.configurar_qa():
                    return {
                        "status": "error",
                        "message": "No se pudo configurar el sistema QA"
                    }
            
            # Procesar consulta - CAMBIO AQUÍ: usar invoke en lugar de __call__
            query_completa = f"{roleOf_system}\n\nConsulta: {roelOf_user}"
            resultado = self.qa.invoke({"query": query_completa})  # ← CAMBIO PRINCIPAL
            
            return {
                "status": "success",
                "message": "Consulta procesada correctamente",
                "data": resultado.get('result', ''),
                "productos_encontrados": len(resultado.get('source_documents', []))
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": "Error interno del servidor",
                "error_details": str(e)
            }
        
# def main():
#     print("🎮 BOT PRODUCTOS GAMER")
#     print("=" * 40)
    
#     # Inicializar
#     entrenador = EntrenamientoFino()
    
#     # Role system para productos gamer
#     role_system = """
#     Eres un experto en productos gaming. Responde sobre productos gamer disponibles.
#     Usa emojis gaming y sé entusiasta pero profesional.
#     """
    
#     print("✅ Bot listo! Escribe 'salir' para terminar\n")
    
#     while True:
#         pregunta = input("🎮 Pregunta: ").strip()
        
#         if pregunta.lower() == 'salir':
#             break
            
#         if pregunta:
#             resultado = entrenador.obtener_informacion_modelo(role_system, pregunta)
            
#             if resultado['status'] == 'success':
#                 print(f"\n🤖 Respuesta:\n{resultado['data']}")
#                 print(f"📊 Productos encontrados: {resultado['productos_encontrados']}\n")
#             else:
#                 print(f"❌ Error: {resultado['message']}\n")

# if __name__ == "__main__":
#     main()