from typing import Optional


def tempo_para_minutos(txt: Optional[str]) -> Optional[int]:
    """
    Converte strings como '01:28:12', '14:16' ou '00:01' em minutos inteiros.
    Retorna None caso o formato seja inválido.
    """
    if not txt:
        return None
    partes = txt.split(":")
    try:
        if len(partes) == 3:
            h, m, _ = map(int, partes)
            return h * 60 + m
        if len(partes) == 2:
            m, _ = map(int, partes)
            return m
        return int(partes[0])
    except ValueError:
        return None


def normalize_image_url(url: Optional[str]) -> str:
    """Normaliza URLs de imagem mantendo absolutas e ajustando esquemas ausentes."""
    if not url:
        return ""

    url = url.strip()
    if url.startswith("http://") or url.startswith("https://"):
        return url
    if url.startswith("//"):
        # Trate URLs sem esquema, ex.: //i.mycdn.me/...
        return f"https:{url}"

    return url


def formatar_duracao(ms: int) -> str:
    """Converte milissegundos em HH:MM:SS."""
    segundos = ms // 1000
    horas = segundos // 3600
    minutos = (segundos % 3600) // 60
    segundos = segundos % 60
    return f"{horas:02}:{minutos:02}:{segundos:02}"
