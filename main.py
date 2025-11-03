from ollama import Client
from argparse import ArgumentParser

DEFAULT_HOST = "https://rcsllm.carleton.ca/rcsapi"

parser = ArgumentParser(description="Ollama API Client Example")
parser.add_argument("--host", type=str, help="Ollama server host", required=False, default=DEFAULT_HOST)
parser.add_argument("--model", type=str, help="Model to use for requests", required=False, default="gpt-oss:120b")
parser.add_argument("--prompt", type=str, help="Prompt to send to the model", required=False, default="What is an LLM and how are you compared to other models?")
parser.add_argument("--stream", action="store_true", help="Stream the response", required=False, default=True)
parser.add_argument("--api_key", type=str, help="API Key for authentication", required=True)
parser.add_argument("--list_models", action="store_true", help="List available models", required=False, default=False)


if __name__ == "__main__":
    args = parser.parse_args()
    api_key = args.api_key
    custom_header = {"x-api-key": api_key} if api_key else {}
    ollama_client = Client(host=args.host, headers=custom_header)
    
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
            {"role": "user", "content": args.prompt}
        ],
        stream=stream
    )

    if stream:
        for chunk in response:
            print(chunk['message']['content'], end="", flush=True)
    else:
        print(response['message']['content'])
