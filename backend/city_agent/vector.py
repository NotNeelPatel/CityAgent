from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
import pandas as pd  # to read csv

df = pd.read_csv(
    "./city_agent/data/1_Operating_overview_expenditure.csv", encoding="cp1252"
)

embeddings = OllamaEmbeddings(
    model="embeddinggemma:300m", base_url=os.getenv("OLLAMA_API_BASE")
)
db_location = "./chroma_langchain_db"
add_documents = not os.path.exists(db_location)

if add_documents:
    documents = []
    ids = []

    for i, row in df.iterrows():
        document = Document(
            page_content=row[0],
            metadata={"Total": row[2]},
            id=str(i),
        )
        ids.append(str(i))
        documents.append(document)

vector_store = Chroma(
    collection_name="Operating_overview_expenditure",
    persist_directory=db_location,
    embedding_function=embeddings,
)

if add_documents:
    vector_store.add_documents(documents=documents, ids=ids)

retriever = vector_store.as_retriever(search_kwargs={"k": 5})
