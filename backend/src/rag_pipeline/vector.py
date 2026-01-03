from langchain_chroma import Chroma
from pathlib import Path
import os
import asyncio
from rag_pipeline.vectorize_excel import vectorize_excel
from ai_api_selector import get_embedding_model

# from vectorize_excel import vectorize_excel
# from ai_api_selector import get_embedding_model

BACKEND_DIR = str(
    next(p for p in Path(__file__).resolve().parents if p.name == "backend")
)
DATA_DIR = f"{BACKEND_DIR}/data"
DB_DIR = f"{BACKEND_DIR}/chroma_langchain_db"

all_documents = []
all_ids = []


# load and vectorize data
async def load_data():
    """Scan `DATA_DIR` for CSV/XLSX files, vectorize them and return lists.

    This coroutine iterates over files in `DATA_DIR`, calls
    `vectorize_excel` for CSV/XLSX files, and aggregates all returned
    documents and ids into two lists which are returned.

    Returns:
        tuple[list, list]: (documents, ids) where `documents` is a list of
            `Document` objects and `ids` is a list of their string ids.
    """
    documents = []
    ids = []

    if not os.path.exists(DATA_DIR):
        return documents, ids

    print("Number of files in data directory:", len(os.listdir(DATA_DIR)))
    for entry in os.scandir(DATA_DIR):
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
    """Run a query against the persisted vector store retriever.

    Args:
        query (str): The natural-language query to run.

    Returns:
        Any: The retriever's raw response (depends on configured retriever).
    """

    return retriever.invoke(query)


async def initialize_vector_store():
    """Initialize module-level document lists by loading and aggregating data.

    Awaits `load_data` and extends the module-level `all_documents` and
    `all_ids` lists so they are available for subsequent upsert to the
    vector store. This function does not perform the upsert itself.
    """
    docs, ids = await load_data()
    all_documents.extend(docs)
    all_ids.extend(ids)


embeddings = get_embedding_model()
vector_store = Chroma(
    collection_name="city_agent_collection",
    persist_directory=DB_DIR,
    embedding_function=embeddings,
)
retriever = vector_store.as_retriever(search_kwargs={"k": 4})


def add_documents_to_vector_store(documents, ids, chunk_size=5000):
    """Add documents to the vector store.

    Args:
        documents (list[Document]): List of Document objects to add.
        ids (list[str]): List of string ids corresponding to the documents.
    """
    for i in range(0, len(documents), chunk_size):
        print(
            f"Adding Document ID: {ids[i]} with content length: {len(documents[i].page_content)}"
        )
        chunk_docs = documents[i : i + chunk_size]
        chunk_ids = ids[i : i + chunk_size]
        print(f"Processing batch {i} to {i + len(chunk_docs)}...")
        vector_store.add_documents(documents=chunk_docs, ids=chunk_ids)


if __name__ == "__main__":
    asyncio.run(initialize_vector_store())
    add_documents_to_vector_store(all_documents, all_ids)
    # vector_store.add_documents(documents=all_documents, ids=all_ids)
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})
