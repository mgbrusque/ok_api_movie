import requests

# URL da API do OK.ru
url = "https://ok.ru/web-api/v2/video/fetchSearchResult"

# Headers simulando um navegador para evitar bloqueios
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json"
}

# Testar diferentes offsets manualmente
for offset in [0, 20, 40, 60]:
    print(f"\n🔍 Buscando vídeos com offset {offset}...\n")

    payload = {
        "id": 25,
        "parameters": {
            "searchQuery": "DUBLADO 1996",
            "currentStateId": "video",
            "durationType": "ANY",
            "hd": False,
            "videosOffset": offset  # Enviando paginação
        }
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        videos = data.get("result", {}).get("videos", {}).get("list", [])

        print(f"📌 {len(videos)} vídeos retornados com offset {offset}.")

        for i, video in enumerate(videos[:3]):  # Apenas 3 para não poluir a tela
            print(f"{i+1}. {video['movie']['id']} - {video['movie']['title']}")

    else:
        print(f"❌ Erro {response.status_code}: {response.text}")
