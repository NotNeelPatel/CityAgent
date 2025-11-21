from langchain_chroma import Chroma
import os
import asyncio
from city_agent.vectorize_excel import vectorize_excel
from city_agent.ai_api_selector import get_embedding_model


DIRECTORY_PATH = "./data/"
DB_LOCATION = "./chroma_langchain_db"
all_documents = []
all_ids = []

# load and vectorize data
async def load_data():
    documents = []
    ids = []
    
    if not os.path.exists(DIRECTORY_PATH):
        return documents, ids
    
    print("Number of files in data directory:", len(os.listdir(DIRECTORY_PATH)))
    for entry in os.scandir(DIRECTORY_PATH):
        print("Processing file:", entry.name)
        if (
            entry.name.endswith(".xlsx") or entry.name.endswith(".csv")
        ) and entry.is_file():
            # do excel things
            curr_documents, curr_ids = await vectorize_excel(entry.path)
            documents.extend(curr_documents)
            ids.extend(curr_ids)
        elif entry.name.endswith(".pdf") and entry.is_file():
            # TODO: do pdf things
            continue
        else:
            print("Skipping non-supported file:", entry.name)
    return documents, ids


def query_retriever(query: str):
    return retriever.invoke(query)

async def initialize_vector_store():
    docs,ids = await load_data()
    all_documents.extend(docs)
    all_ids.extend(ids)

embeddings = get_embedding_model()
vector_store = Chroma(
    collection_name="city_agent_collection",
    persist_directory=DB_LOCATION,
    embedding_function=embeddings,
)
retriever = vector_store.as_retriever(search_kwargs={"k": 4})

# temporary function to add chunked documents
def chunked_add_documents(documents, ids, chunk_size=5000):
        for i in range(0, len(documents), chunk_size):
            chunk_docs = documents[i : i + chunk_size]
            chunk_ids = ids[i : i + chunk_size] if ids else None
            vector_store.add_documents(documents=chunk_docs, ids=chunk_ids)

if __name__ == "__main__":
    asyncio.run(initialize_vector_store())
    #vector_store.add_documents(documents=all_documents, ids=all_ids)
    chunked_add_documents(all_documents, all_ids, chunk_size=5000)
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
