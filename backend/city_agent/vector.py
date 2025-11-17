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


embeddings = get_embedding_model()
vector_store = Chroma(
    collection_name="city_agent_collection",
    persist_directory=DB_LOCATION,
    embedding_function=embeddings,
)
async def initialize_vector_store():
    docs,ids = await load_data()
    all_documents.extend(docs)
    all_ids.extend(ids)
    
if __name__ == "__main__":
    asyncio.run(initialize_vector_store())
    vector_store.add_documents(documents=all_documents, ids=all_ids)
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})