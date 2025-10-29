from ollama import Client
from argparse import ArgumentParser

#api_key = "<your_api_key_here>" #or provide via parser argument

api_key = ""

host = 'https://134.117.214.87/rcsapi'

parser = ArgumentParser(description="Ollama API Client Example")

parser.add_argument("--model", type=str, help="Model to use for requests", required=False, default="gpt-oss:120b")

parser.add_argument("--stream", action="store_true", help="Stream the response", required=False, default=True)

parser.add_argument("--api_key", type=str, help="API Key for authentication", required=False, default=api_key)

parser.add_argument("--list_models", action="store_true", help="List available models", required=False, default=False)

if __name__ == "__main__":
    args = parser.parse_args()
    api_key = args.api_key
    custom_header = {"x-api-key": api_key} if api_key else {}
    ollama_client = Client(host=host, headers=custom_header, verify=False)
    if args.list_models:
        models = ollama_client.list()
        print("Available models:")
        for model in models.models:
            print(f"- {model.model}")
        exit(0)
    stream = args.stream
    response = ollama_client.chat(
        model=args.model,
        messages=[
            {"role": "user", "content": "What is Carleton University?"}
        ],
        stream=stream
    )
    if stream:
        for chunk in response:
            print(chunk['message']['content'], end="", flush=True)
    else:
        print(response['message']['content'])
