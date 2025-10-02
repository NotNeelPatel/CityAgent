# Simple python program to test the RCS Ollama servers
# Tested on Neel's Ollama server

import asyncio
from ollama import AsyncClient

# Local to my network, change to different server if needed
HOST='http://10.0.0.165:11434'

client = AsyncClient(
    host=HOST
    )

async def chat():
    message = {'role': 'user', 
               'content': 'What is Carleton University?'
               }
    async for part in await client.chat(model='gemma3:12b', messages=[message], stream=True):
        print(part['message']['content'], end='', flush=True)

asyncio.run(chat())
