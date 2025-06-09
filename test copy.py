import requests

url = "https://ok.ru/web-api/v2/video/fetchSearchResult"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json"
}

payload = {
    "id": 25,
    "parameters": {
        "searchQuery": "dublagem clássica",
        "currentStateId": "video",
        "durationType": "ANY",
        "hd": False,
        "videosOffset": 0,
        "filters": {
            "st.cmd": "searchResult",
            "st.mode": "Movie",
            "st.gmode": "Groups",
            "st.query": "dublagem clássica",
            "st.vcr": "today"  # últimos 60 minutos
        }
    }
}

response = requests.post(url, headers=headers, json=payload)

print(f"Status code: {response.status_code}")

if response.status_code == 200:
    data = response.json()

    videos = data.get("result", {}).get("videos", {}).get("list", [])
    total_count = data.get("result", {}).get("videos", {}).get("totalCount", 0)

    print(f"🔢 Total de vídeos disponíveis: {total_count}")
    print(f"📦 Vídeos recebidos nesta requisição: {len(videos)}")

    for video in videos[:5]:  # Mostra só os 5 primeiros
        movie = video.get("movie", {})
        title = movie.get("title", "Sem título")
        duration = movie.get("duration", 0)
        print(f"🎬 {title} - duração (ms): {duration}")
else:
    print("⚠️ Erro na requisição:")
    print(response.text)
