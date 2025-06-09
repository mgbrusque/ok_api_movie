from flask import Flask, render_template, request, jsonify
import requests

app = Flask(__name__)

# Função para converter milissegundos em HH:MM:SS
def formatar_duracao(ms):
    segundos = ms // 1000
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos = segundos % 60
    return f"{horas:02}:{minutos:02}:{segundos:02}"

# Função para buscar vídeos da API OK.ru
def buscar_videos(query, offset, duration="", hd_quality=""):
    url = "https://ok.ru/web-api/v2/video/fetchSearchResult"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json"
    }

    payload = {
        "id": 25,
        "parameters": {
            "searchQuery": query,
            "currentStateId": "video",
            "durationType": duration or "ANY",
            "hd": hd_quality == "ON",
            "videosOffset": offset,
            "filters": {
                "st.cmd": "searchResult",
                "st.mode": "Movie",
                "st.gmode": "Groups",
                "st.query": query
            }
        }
    }

    if duration:
        payload["parameters"]["filters"]["st.vln"] = duration

    #print(f"🔍 Enviando requisição para a API com offset {offset}...")  # LOG

    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        data = response.json()
        videos = data.get("result", {}).get("videos", {}).get("list", [])
        total_count = data.get("result", {}).get("videos", {}).get("totalCount", 0)

        #print(f"✅ API respondeu: {len(videos)} vídeos encontrados. Total disponível: {total_count}")  # LOG

        resultado = []
        for video in videos:
            movie = video.get("movie", {})
            duracao_ms = movie.get("duration", 0)
            resultado.append({
                "id": movie.get("id", ""),
                "title": movie.get("title", "Sem título"),
                "thumbnail": movie.get("thumbnail", {}).get("big", ""),
                "views": video.get("viewsCount", 0),
                "likes": movie.get("likesCount", 0),
                "duration": formatar_duracao(duracao_ms)
            })
        
        return {"videos": resultado, "totalCount": total_count}
    
    #print(f"⚠️ Erro ao buscar vídeos: {response.status_code} - {response.text}")  # LOG
    return {"videos": [], "totalCount": 0}

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/buscar', methods=['POST'])
def buscar():
    query = request.form.get("query", "")
    offset = int(request.form.get("offset", 0))
    duration = request.form.get("duration", "")
    hd_quality = request.form.get("hd", "")
    offset = int(request.form.get("offset", 0))

    #print(f"🔄 Cliente requisitou: query='{query}', offset={offset}")  # LOG

    resultado = buscar_videos(query, offset, duration, hd_quality)

    #print(f"📌 Enviando {len(resultado['videos'])} vídeos para o cliente.")  # LOG

    return jsonify(resultado)

if __name__ == '__main__':
    app.run(debug=True)
