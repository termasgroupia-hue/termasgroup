from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_core.documents import Document
from langchain.agents import create_react_agent
from langchain.agents.agent_toolkits import create_retriever_tool
from langchain_community.llms import HuggingFaceEndpoint
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import pandas as pd
import os

# Inicializar FastAPI
app = FastAPI()

# Cargar Excel optimizado
documentos = []
ruta_excel = "proveedores.xlsx"

if os.path.exists(ruta_excel):
    try:
        xls = pd.read_excel(ruta_excel, sheet_name=None, skiprows=2)
        for nombre_hoja, tabla in xls.items():
            if tabla.empty or tabla.columns.isnull().any():
                continue
            tabla.dropna(how="all", inplace=True)
            tabla.dropna(axis=1, how="all", inplace=True)
            tabla = tabla.head(100)  # Limitar a 100 filas por hoja
            for _, row in tabla.iterrows():
                contenido = f"Categoría: {nombre_hoja}\n" + "\n".join(
                    [f"{col}: {row[col]}" for col in tabla.columns if pd.notna(row[col])]
                )
                documentos.append(Document(page_content=contenido))
        print(f"✅ Se cargaron {len(documentos)} documentos.")
    except Exception as e:
        print("❌ Error al procesar el Excel:", e)
else:
    print("⚠️ No se encontró el archivo proveedores.xlsx.")

# Crear retriever si hay documentos
retriever = None
if documentos:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    docs_divididos = splitter.split_documents(documentos)
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(docs_divididos, embeddings)
    retriever = vectorstore.as_retriever()

# Crear agente con herramientas
llm = HuggingFaceEndpoint(
    repo_id="mistralai/Mistral-7B-Instruct-v0.2",
    temperature=0.5,
    huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN")
)

tools = []
if retriever:
    herramienta = create_retriever_tool(
        retriever,
        name="buscador_proveedores",
        description="Busca información sobre proveedores en distintas categorías"
    )
    tools.append(herramienta)

agente = create_react_agent(llm=llm, tools=tools)

# Endpoint POST /preguntar
@app.post("/preguntar")
async def preguntar(request: Request):
    datos = await request.json()
    pregunta = datos.get("pregunta", "")
    if not pregunta:
        return JSONResponse(content={"error": "No se recibió ninguna pregunta"}, status_code=400)
    respuesta = agente.invoke(pregunta)
    return JSONResponse(content={"respuesta": respuesta})

# Ejecutar servidor con Uvicorn en Render
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
