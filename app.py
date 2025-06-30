from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests
import psycopg2
import os
load_dotenv()

app = Flask(__name__)

def get_conn():
    return psycopg2.connect(  
        host="bq2dwmholieihd7cnpxx-postgresql.services.clever-cloud.com",
        database="bq2dwmholieihd7cnpxx",
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port="50013"
    )

def buscar_videos_bd(query, offset=0, limit=20):
    conn = get_conn()
    cur = conn.cursor()

    # Consulta os vídeos com paginação
    # Divide a query em palavras
    palavras = query.lower().split()
    like_clauses = " AND ".join(["LOWER(nome) LIKE %s" for _ in palavras])
    params = [f"%{p}%" for p in palavras]

    # Consulta com cláusulas múltiplas
    sql_dados = f"""
        SELECT id, nome, tempo, imagem
        FROM filmes
        WHERE {like_clauses}
        ORDER BY nome
        OFFSET %s LIMIT %s
    """
    cur.execute(sql_dados, (*params, offset, limit))
    rows = cur.fetchall()

    # Consulta o total de resultados (sem offset)
    sql_total = f"""
        SELECT COUNT(*)
        FROM filmes
        WHERE {like_clauses}
    """
    cur.execute(sql_total, tuple(params))
    total_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    resultado = []
    for row in rows:
        resultado.append({
            "id": row[0],
            "title": row[1],
            "duration": row[2],
            "thumbnail": row[3],
            "likes": 0,
            "views": None
        })

    return {"videos": resultado, "totalCount": total_count}

# Função para converter milissegundos em HH:MM:SS
def formatar_duracao(ms):
    segundos = ms // 1000
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos = segundos % 60
    return f"{horas:02}:{minutos:02}:{segundos:02}"

# Função para buscar vídeos da API OK.ru
def buscar_videos(query, offset, duration="", hd_quality=""):
    import json  # só por garantia
    url = "https://ok.ru/web-api/v2/video/fetchSearchResult"
    headers = {
        "User-Agent": "Mozilla/5.0",
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

    print("\n🔍 Enviando requisição com payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    response = requests.post(url, json=payload, headers=headers)

    print(f"\n📡 Status da resposta: {response.status_code}")
    print("📄 Conteúdo bruto da resposta:")
    print(response.text[:3000])  # limita pra não explodir o terminal

    if response.status_code != 200:
        print("❌ Erro na requisição.")
        return {"videos": [], "totalCount": 0}

    try:
        data = response.json()
    except Exception as e:
        print(f"❌ Erro ao fazer parse do JSON: {e}")
        return {"videos": [], "totalCount": 0}

    resultado = []

    # Tenta pegar vídeos
    video_list = data.get("result", {}).get("videos", {}).get("list", [])
    total_count = data.get("result", {}).get("videos", {}).get("totalCount", 0)

    if video_list:
        print(f"✅ Encontrado {len(video_list)} vídeos.")
        for video in video_list:
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

    # Tenta pegar canais/álbuns
    channel_list = data.get("result", {}).get("channels", {}).get("list", [])
    total_count = data.get("result", {}).get("channels", {}).get("totalCount", 0)

    if channel_list:
        print(f"📁 Encontrado {len(channel_list)} canais/álbuns.")
        for channel in channel_list:
            album = channel.get("album", {})
            resultado.append({
                "id": album.get("id", ""),
                "title": album.get("name", "Sem título"),
                "thumbnail": album.get("imageUrl", ""),
                "views": album.get("views", 0),
                "likes": 0,
                "duration": f"{album.get('videoCount', 0)} vídeos"
            })
        return {"videos": resultado, "totalCount": total_count}

    print("⚠️ Nenhum vídeo ou canal retornado.")
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
    fonte = request.form.get("fonte", "API")

    videos = []
    total_api = 0
    total_bd = 0

    # Busca na API
    if fonte in ["API", "AMBOS"]:
        resultado_api = buscar_videos(query, offset, duration, hd_quality)
        videos.extend(resultado_api["videos"])
        total_api = resultado_api["totalCount"]

    # Busca no banco com total
    if fonte in ["BD", "AMBOS"]:
        resultado_bd = buscar_videos_bd(query, offset)
        videos.extend(resultado_bd["videos"])
        total_bd = resultado_bd["totalCount"]

    # Remove duplicados por ID
    unicos = {}
    for video in videos:
        if video["id"] not in unicos:
            unicos[video["id"]] = video

    videos_unicos = list(unicos.values())

    return jsonify({
        "videos": videos_unicos,
        "totalCount": total_api + total_bd
    })

if __name__ == "__main__":
    app.run(debug=True)