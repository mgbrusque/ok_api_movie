import logging
import random
from typing import Dict, List, Tuple

from services.db import get_conn
from utils.media import tempo_para_minutos, normalize_image_url

FAIXAS_MINUTOS: Dict[str, Tuple[int, int]] = {
    "0-20": (0, 20),
    "21-60": (21, 60),
    "61-90": (61, 90),
    "91-120": (91, 120),
    "121-160": (121, 160),
    "161-200": (161, 200),
    "201+": (201, 10**9),
}


def buscar_videos_bd(query: str, offset: int = 0, limit: int = 20, faixa: str = "", ordem: str = "nome_asc"):
    """
    Busca vídeos no banco aplicando filtros, ordenação e paginação.
    """
    conn = get_conn()
    cur = conn.cursor()

    palavras = query.lower().split()
    like_clauses = " AND ".join(["LOWER(nome) LIKE %s" for _ in palavras]) or "TRUE"
    params = [f"%{p}%" for p in palavras] or []

    cur.execute(
        f"""
        SELECT id, nome, tempo, imagem
        FROM filmes
        WHERE {like_clauses}
        """,
        tuple(params),
    )
    rows = cur.fetchall()

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM filmes
        WHERE {like_clauses}
        """,
        tuple(params),
    )
    total_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    resultado: List[dict] = []
    for row in rows:
        minutos = tempo_para_minutos(row[2])
        resultado.append(
            {
                "id": row[0],
                "title": row[1],
                "duration": row[2],
                "thumbnail": normalize_image_url(row[3]),
                "likes": 0,
                "views": None,
                "minutos": minutos,
            }
        )

    if faixa in FAIXAS_MINUTOS:
        lo, hi = FAIXAS_MINUTOS[faixa]
        resultado = [v for v in resultado if v["minutos"] is not None and lo <= v["minutos"] <= hi]

    if ordem == "tempo_desc":
        resultado.sort(key=lambda v: v["minutos"] or -1, reverse=True)
    elif ordem == "tempo_asc":
        resultado.sort(key=lambda v: v["minutos"] or 10**9)
    elif ordem == "nome_desc":
        resultado.sort(key=lambda v: v["title"].lower(), reverse=True)
    elif ordem == "random":
        random.shuffle(resultado)
    else:
        resultado.sort(key=lambda v: v["title"].lower())

    total_count = len(resultado)
    resultado = resultado[offset : offset + limit]

    for v in resultado:
        v.pop("minutos", None)

    logging.debug("buscar_videos_bd: retornando %s itens (total filtrado %s)", len(resultado), total_count)
    return {"videos": resultado, "totalCount": total_count}
