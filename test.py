import requests
import json

# URL da API do OK.ru
url = "https://ok.ru/web-api/v2/video/fetchSearchResult"

# Headers simulando um navegador para evitar bloqueios
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json"
}

# Payload com os parâmetros de busca
payload = {
    "id": 25,
    "parameters": {
        "searchQuery": "DUBLADO 1997 fenomeno",
        "currentStateId": "video",  
        "durationType": "ANY", 
        "hd": False
    }
}

# Fazendo a requisição POST
response = requests.post(url, json=payload, headers=headers)

# Verificando a resposta
if response.status_code == 200:
    data = response.json()

    # Exibindo o JSON formatado para melhor visualização
    print(json.dumps(data, indent=4, ensure_ascii=False))
else:
    print(f"Erro {response.status_code}: {response.text}")
