import requests
from datetime import timedelta

# URL da API do OK.ru
url = "https://ok.ru/web-api/v2/video/fetchSearchResult"

# Headers simulando um navegador para evitar bloqueios
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json"
}

# Número máximo de vídeos para buscar (múltiplas páginas)
max_results = 100  # Ajuste conforme necessário
videos_per_page = 20  # Se a API retorna 20 por página
offset = 0  # Começa na primeira página
total_videos = 0  # Contador total

while total_videos < max_results:
    print(f"\n🔍 Buscando vídeos a partir do offset {offset}...\n")

    # Payload com paginação
    payload = {
        "id": 25,
        "parameters": {
            "searchQuery": "DUBLADO 1997",
            "currentStateId": "video",
            "durationType": "ANY",
            "hd": False,
            "offset": offset  # Paginação
        }
    }

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()

        # Obter vídeos da resposta
        videos = data.get("result", {}).get("videos", {}).get("list", [])

        for video in videos:
            movie = video.get("movie", {})
            video_id = movie.get("id", "N/A")
            title = movie.get("title", "Sem título")
            thumbnail = movie.get("thumbnail", {}).get("big", "Sem thumbnail")
            views = video.get("viewsCount", 0)
            likes = movie.get("likesCount", 0)
            duration_ms = movie.get("duration", 0)

            # Converter duração de milissegundos para HH:MM:SS
            duration_s = duration_ms // 1000  # Convertendo para segundos
            duration_formatted = str(timedelta(seconds=duration_s))

            # Exibir os dados formatados
            print(f"🎬 ID: {video_id}")
            print(f"📌 Título: {title}")
            print(f"🖼 Thumbnail: {thumbnail}")
            print(f"👁 Views: {views}")
            print(f"❤️ Likes: {likes}")
            print(f"⏳ Duração: {duration_formatted}")
            print("-" * 50)

            total_videos += 1

        # Se não houver mais vídeos, interrompe
        if len(videos) < videos_per_page:
            print("\n🚀 Todas as páginas foram carregadas!")
            break

        # Atualiza o offset para pegar a próxima página
        offset += videos_per_page
    else:
        print(f"Erro {response.status_code}: {response.text}")
        break  # Interrompe em caso de erro
