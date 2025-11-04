from langchain_ollama import OllamaEmbeddings
from langchain_openai import AzureOpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
import pandas as pd  # to read csv

USE_AZURE = True

df = pd.read_csv("./city_agent/data/4_Rates_fees_and_charges.csv", encoding="cp1252")
if (USE_AZURE):
    embeddings = AzureOpenAIEmbeddings(
        model="text-embedding-ada-002",
        api_key=os.getenv("AZURE_API_KEY_EMBEDDING"),
        azure_endpoint=os.getenv("AZURE_API_BASE_EMBEDDING"),
        api_version=os.getenv("AZURE_API_VERSION_EMBEDDING"),
    )
else:
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text:v1.5", base_url=os.getenv("OLLAMA_API_BASE")
    )

db_location = "./chroma_langchain_db"
add_documents = not os.path.exists(db_location)

if add_documents:
    documents = []
    ids = []

    for i, row in df.iterrows():
        department = row[0]
        committee = row[2]
        service_area = row[4]
        description = row[6]
        fee_2024 = row[12]
        fee_2025 = row[13]
        increase = row[15]
        effective_start = row[17]
        colsearch = row[18]

        # Build readable text for embedding/search
        page_content = colsearch or " > ".join(
            [p for p in [department, committee, service_area, description] if p]
        )

        metadata = {
            "department": department,
            "committee": committee,
            "service_area": service_area,
            "description": description,
            "fee_2024": fee_2024,
            "fee_2025": fee_2025,
            "increase": increase,
            "effective_starting": effective_start,
        }
        doc = Document(page_content=page_content, metadata=metadata, id=str(i))
        ids.append(str(i))
        documents.append(doc)

vector_store = Chroma(
    collection_name="Operating_overview_expenditure",
    persist_directory=db_location,
    embedding_function=embeddings,
)

if add_documents:
    vector_store.add_documents(documents=documents, ids=ids)

retriever = vector_store.as_retriever(search_kwargs={"k": 4})


def query_retriever(query: str):
    return retriever.invoke(query)

