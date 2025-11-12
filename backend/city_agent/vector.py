from langchain_ollama import OllamaEmbeddings
from langchain_openai import AzureOpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import os
import asyncio
import pandas as pd  # to read csv
from vectorize_excel import vectorize_excel
from dotenv import load_dotenv # amilesh needs this to load his env, TODO: figure out why
from ai_api_selector import get_embedding_model


load_dotenv()


DIRECTORY_PATH = "./city_agent/data/"
DB_LOCATION = "./chroma_langchain_db"
all_documents = []
all_ids = []

# load and vectorize data
async def load_data(all_documents, all_ids):
    print("Loading data from directory:", DIRECTORY_PATH)
    if not os.path.exists(DIRECTORY_PATH):
        return all_documents, all_ids
    
    for entry in os.scandir(DIRECTORY_PATH):
        if (entry.name.endswith('.xlsx') or entry.name.endswith('.csv')) and entry.is_file():
            # do excel things
            documents, ids = vectorize_excel(entry.path)
            all_documents.extend(documents)
            all_ids.extend(ids)   
        elif entry.name.endswith('.pdf') and entry.is_file():
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

           
# df = pd.read_csv("./city_agent/data/4_Rates_fees_and_charges.csv", encoding="cp1252")

    
# add_documents = not os.path.exists(DB_LOCATION)

# if add_documents:
#     documents = []
#     ids = []

#     for i, row in df.iterrows():
#         department = row[0]
#         committee = row[2]
#         service_area = row[4]
#         description = row[6]
#         fee_2024 = row[12]
#         fee_2025 = row[13]
#         increase = row[15]
#         effective_start = row[17]
#         colsearch = row[18]

#         # Build readable text for embedding/search
#         page_content = colsearch or " > ".join(
#             [p for p in [department, committee, service_area, description] if p]
#         )

#         metadata = {
#             "department": department,
#             "committee": committee,
#             "service_area": service_area,
#             "description": description,
#             "fee_2024": fee_2024,
#             "fee_2025": fee_2025,
#             "increase": increase,
#             "effective_starting": effective_start,
#         }
#         doc = Document(page_content=page_content, metadata=metadata, id=str(i))
#         ids.append(str(i))
#        documents.append(doc)

