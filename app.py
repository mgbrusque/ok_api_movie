from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import requests
import psycopg2
import os
import random
import yt_dlp
load_dotenv()

app = Flask(__name__)

def get_conn():
    return psycopg2.connect(  
        host=os.environ.get("DB_HOST"),
        database=os.environ.get("DB_DATABASE"),
        user=os.environ.get("DB_USER"),
        password=os.environ.get("DB_PASSWORD"),
        port=os.environ.get("DB_PORT"),
    )

def tempo_para_minutos(txt):
    """
    Recebe strings tipo '01:28:12', '14:16', '00:01' e devolve minutos inteiros.
    Se falhar, retorna None.
    """
    if not txt:
        return None
    partes = txt.split(':')
    try:
        if len(partes) == 3:
            h, m, _ = map(int, partes)
            return h*60 + m
        if len(partes) == 2:
            m, _ = map(int, partes)
            return m
        return int(partes[0])
    except ValueError:
        return None
    
def buscar_videos_bd(query, offset=0, limit=20, faixa="", ordem="nome_asc"):
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
    """
    cur.execute(sql_dados, tuple(params))

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
        minutos = tempo_para_minutos(row[2])
        resultado.append({
            "id": row[0],
            "title": row[1],
            "duration": row[2],
            "thumbnail": row[3],
            "likes": 0,
            "views": None,
            "minutos": minutos
        })

    # --- filtro de faixa ---
    faixas = {
        "0-20":  (0,20),
        "21-60": (21,60),
        "61-90": (61,90),
        "91-120":(91,120),
        "121-160":(121,160),
        "161-200":(161,200),
        "201+":  (201, 10**9)
    }
    if faixa in faixas:
        lo, hi = faixas[faixa]
        resultado = [v for v in resultado if v["minutos"] is not None and lo <= v["minutos"] <= hi]

    # --- ordenação ---
    if ordem == "tempo_desc":
        resultado.sort(key=lambda v: v["minutos"] or -1, reverse=True)
    elif ordem == "tempo_asc":
        resultado.sort(key=lambda v: v["minutos"] or 10**9)
    elif ordem == "nome_desc":
        resultado.sort(key=lambda v: v["title"].lower(), reverse=True)
    elif ordem == "random":
        random.shuffle(resultado)
    else:  # nome_asc
        resultado.sort(key=lambda v: v["title"].lower())

    total_count = len(resultado)
    resultado   = resultado[offset:offset+limit]

    # remove chave 'minutos' antes de devolver
    for v in resultado:
        v.pop("minutos", None)

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



def extrair_link_download(video_id: str, prefer_height: int | None = None):
    """
    Usa yt_dlp para extrair um link direto (mp4/webm) do OK.ru sem baixar o arquivo.
    Se só houver manifestos HLS/DASH, retorna streaming=True para o front avisar.
    """
    video_url = f"https://ok.ru/video/{video_id}"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "format": "bestvideo+bestaudio/best",
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(video_url, download=False)
    if not info:
        raise RuntimeError("Nao foi possivel obter info do video.")

    formats = info.get("formats") or []

    def is_stream_manifest(fmt):
        proto = (fmt.get("protocol") or "").lower()
        ext = (fmt.get("ext") or "").lower()
        return "m3u8" in proto or "dash" in proto or ext == "m3u8"

    # Prefere arquivos diretos (http/https) em mp4/webm.
    def is_direct(fmt):
        if not fmt.get("url"):
            return False
        if is_stream_manifest(fmt):
            return False
        ext = (fmt.get("ext") or "").lower()
        proto = (fmt.get("protocol") or "").lower()
        if "m3u8" in proto or "dash" in proto:
            return False
        return ext in {"mp4", "webm", "mov", "m4v"}

    diretos = [f for f in formats if is_direct(f)]

    def pick_direct(fmts, target_height=None):
        if not fmts:
            return None
        if target_height:
            abaixo = [f for f in fmts if (f.get("height") or 0) <= target_height]
            abaixo = sorted(abaixo, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)
            if abaixo:
                return abaixo[0]
            acima = sorted(fmts, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0))
            return acima[0]
        return sorted(fmts, key=lambda f: (f.get("height") or 0, f.get("tbr") or 0), reverse=True)[0]

    escolhido = pick_direct(diretos, prefer_height)
    if escolhido:
        return {
            "url": escolhido["url"],
            "title": info.get("title", ""),
            "ext": escolhido.get("ext"),
            "streaming": False,
            "height": escolhido.get("height"),
        }

    # Fallback: HLS/DASH manifest (necessario usar downloader que suporte m3u8/dash).
    manifestos = [f for f in formats if f.get("url") and is_stream_manifest(f)]
    manifestos = sorted(
        manifestos,
        key=lambda f: (f.get("height") or 0, f.get("tbr") or 0),
        reverse=True,
    )
    if manifestos:
        escolhido = manifestos[0]
        return {
            "url": escolhido["url"],
            "title": info.get("title", ""),
            "ext": escolhido.get("ext"),
            "streaming": True,
            "height": escolhido.get("height"),
        }

    url = info.get("url")
    if url:
        return {"url": url, "title": info.get("title", ""), "streaming": True}

    raise RuntimeError("Nao foi possivel encontrar URL de download.")

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
    faixa  = request.form.get("duration_bd", "")
    ordem  = request.form.get("order_bd", "")

    videos = []
    total_api = 0
    total_bd = 0

    # Busca na API
    if fonte in ["API"]:
        resultado_api = buscar_videos(query, offset, duration, hd_quality)
        videos.extend(resultado_api["videos"])
        total_api = resultado_api["totalCount"]

    # Busca no banco com total
    if fonte in ["BD"]:
        resultado_bd = buscar_videos_bd(query, offset, faixa=faixa, ordem=ordem)
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

@app.route('/download/<video_id>', methods=['GET'])
def download(video_id):
    try:
        prefer = request.args.get("h")
        prefer_height = int(prefer) if prefer and prefer.isdigit() else None
        data = extrair_link_download(video_id, prefer_height)
        if data.get("streaming"):
            return jsonify({"error": "Download direto nao disponivel (apenas streaming HLS/DASH)."}), 404
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
