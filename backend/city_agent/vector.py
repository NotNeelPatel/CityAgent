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
async def load_data(all_documents, all_ids):
    if not os.path.exists(DIRECTORY_PATH):
        return all_documents, all_ids

    for entry in os.scandir(DIRECTORY_PATH):
        print("Processing file:", entry.name)
        if (
            entry.name.endswith(".xlsx") or entry.name.endswith(".csv")
        ) and entry.is_file():
            # do excel things
            documents, ids = await vectorize_excel(entry.path)
            all_documents.extend(documents)
            all_ids.extend(ids)
            break
        elif entry.name.endswith(".pdf") and entry.is_file():
            # TODO: do pdf things
            return
        else:
            print("Skipping non-supported file:", entry.name)
    return all_documents, all_ids


def query_retriever(query: str):
    return retriever.invoke(query)


embeddings = get_embedding_model()
vector_store = Chroma(
    collection_name="city_agent_collection",
    persist_directory=DB_LOCATION,
    embedding_function=embeddings,
)
all_documents, all_ids = asyncio.run(load_data(all_documents, all_ids))

vector_store.add_documents(documents=all_documents, ids=all_ids)
retriever = vector_store.as_retriever(search_kwargs={"k": 4})
