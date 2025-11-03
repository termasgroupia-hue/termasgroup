from fastapi import FastAPI, Request
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
import pandas as pd
import os

# Inicializar FastAPI
app = FastAPI()

# Cargar datos desde Excel si existe (comentado para evitar consumo de memoria)
documentos = []
# ruta_excel = "proveedores.xlsx"

# if os.path.exists(ruta_excel):
#     print("📄 Cargando datos desde proveedores.xlsx...")
#     try:
#         xls = pd.read_excel(ruta_excel, sheet_name=None, skiprows=2)
#         for nombre_hoja, tabla in xls.items():
#             if tabla.empty or tabla.columns.isnull().any():
#                 continue
#             tabla.dropna(how="all", inplace=True)
#             tabla.dropna(axis=1, how="all", inplace=True)
#             for _, row in tabla.iterrows():
#                 contenido = f"Categoría: {nombre_hoja}\n" + "\n".join(
#                     [f"{col}: {row[col]}" for col in tabla.columns if pd.notna(row[col])]
#                 )
#                 documentos.append(Document(page_content=contenido))
#         print(f"✅ Se cargaron {len(documentos)} documentos.")
#     except Exception as e:
#         print("❌ Error al procesar el Excel:", e)
# else:
#     print("⚠️ No se encontró el archivo proveedores.xlsx. El sistema funcionará sin contexto.")

print("⚠️ Carga de Excel desactivada temporalmente para pruebas. El sistema funcionará sin contexto.")
documentos = []  # Carga vacía para evitar uso de memoria

# Crear vectorstore si hay documentos
if documentos:
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/paraphrase-MiniLM-L3-v2")
    documentos = documentos[:1000]
    vectorstore = FAISS.from_documents(documentos, embeddings)
    retriever = vectorstore.as_retriever()
else:
    retriever = None

# Inicializar modelo LLM
llm = OllamaLLM(model="mistral")

# Endpoint principal
@app.post("/preguntar")
async def preguntar(request: Request):
    data = await request.json()
    pregunta = data.get("pregunta", "").strip()

    if not pregunta:
        return {"respuesta": "No se recibió ninguna pregunta válida."}

    try:
        if retriever:
            contexto = retriever.invoke(pregunta, k=5)
            contenido = "\n\n".join([doc.page_content for doc in contexto])
        else:
            contenido = "No hay datos cargados desde el Excel. Responde solo con conocimiento general."

        prompt = f"""Eres un asistente experto en proveedores. Usa la siguiente información para responder de forma clara y útil:

{contenido}

Pregunta: {pregunta}
Respuesta:"""

        respuesta = llm.invoke(prompt)
        return {"respuesta": respuesta}

    except Exception as e:
        print("❌ Error durante la generación:", e)
        return {"respuesta": "Hubo un problema al generar la respuesta."}
