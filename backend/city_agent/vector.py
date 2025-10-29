from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
import pandas as pd  # to read csv

df = pd.read_csv("./city_agent/data/4_Rates_fees_and_charges.csv", encoding="cp1252")

embeddings = OllamaEmbeddings(
    model="embeddinggemma:300m", base_url=os.getenv("OLLAMA_API_BASE")
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
        fee_2023 = row[10]
        fee_2024 = row[12]
        fee_2025 = row[14]
        increase = row[16]
        effective_start = row[18]
        colsearch = row[20]

        # Build readable text for embedding/search
        page_content = colsearch or " > ".join(
            [p for p in [department, committee, service_area, description] if p]
        )

        metadata = {
            "department": department,
            "committee": committee,
            "service_area": service_area,
            "description": description,
            "fee_2023": fee_2023,
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

retriever = vector_store.as_retriever(search_kwargs={"k": 20})
