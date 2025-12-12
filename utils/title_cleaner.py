import re
import unicodedata
from datetime import datetime
from typing import List, Tuple

from guessit import guessit
from rapidfuzz import fuzz

# Tokens/tags comuns em releases PT/EN que não pertencem ao título.
PTBR_TAGS = {
    "dublado", "dub", "dual", "audio", "áudio", "legendado", "leg", "sub", "subs",
    "pt-br", "ptbr", "portugues", "português", "brazilian", "br",
    "1080p", "720p", "2160p", "4k", "webrip", "webdl", "web-dl", "brrip", "hdrip",
    "x264", "x265", "hevc", "aac", "h264", "h265", "hdr", "uhd", "remaster", "remastered",
    "rarbg", "yts", "complete", "completo", "filme", "movie"
}

YEAR_RE = re.compile(r"(?<!\d)(19\d{2}|20\d{2})(?!\d)")
DOMAIN_RE = re.compile(r"\b[\w-]+\.(com|net|org|br|info|biz|xyz)\b", re.IGNORECASE)


def extract_year(text: str) -> int | None:
    """Extrai ano plausível (1900..ano_atual+1)."""
    if not text:
        return None
    now = datetime.now().year + 1
    match = YEAR_RE.search(text)
    if match:
        yr = int(match.group(1))
        if 1900 <= yr <= now:
            return yr
    return None


def _remove_bracket_blocks(text: str) -> str:
    """Remove blocos [](){} substituindo por espaço."""
    return re.sub(r"\[[^\]]*\]|\([^)]*\)|\{[^}]*\}", " ", text)


def _normalize_separators(text: str) -> str:
    """Remove decorações e normaliza separadores antes de tokenizar."""
    t = re.sub(r"https?://\S+", " ", text)
    t = DOMAIN_RE.sub(" ", t)

    # Percorre caractere a caractere mantendo apenas letras/dígitos; converte demais em espaço.
    cleaned = []
    for ch in t:
        cat = unicodedata.category(ch)
        if cat[0] in ("L", "N"):  # Letter or Number
            cleaned.append(ch)
        elif ch in {"'", "’"}:
            cleaned.append(ch)
        else:
            cleaned.append(" ")

    t = "".join(cleaned)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def strip_accents(text: str) -> str:
    """Remove acentos, útil para fallback ASCII."""
    return "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")


def clean_ptbr_tags(text: str) -> tuple[str, int | None]:
    """Remove tags de release/PT-BR sem mexer em substrings de palavras."""
    if not text:
        return "", None
    year = extract_year(text)
    t = _remove_bracket_blocks(text)
    t = _normalize_separators(t)

    cleaned_tokens: List[str] = []
    for tok in t.split():
        low = tok.lower()
        if low in PTBR_TAGS:
            continue
        if DOMAIN_RE.match(low):
            continue
        if len(low) == 1 and not low.isdigit():
            continue
        cleaned_tokens.append(tok)

    cleaned = " ".join(cleaned_tokens)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned, year


def generate_candidates(raw: str) -> Tuple[List[str], int | None]:
    """Gera candidatos de título a partir do nome bruto."""
    base, year = clean_ptbr_tags(raw)
    candidates = []
    if base:
        candidates.append(base)

    # Versão mais agressiva (só letras/números/aspas/sinais básicos).
    aggressive = re.sub(r"[^A-Za-z0-9' :\\-]+", " ", base).strip()
    if aggressive and aggressive != base:
        candidates.append(aggressive)

    # Usando guessit para tentar extrair o título.
    try:
        parsed = guessit(raw)
        g_title = parsed.get("title")
        g_year = parsed.get("year") or year
        if g_year:
            year = g_year
        if g_title:
            g_title_clean = _normalize_separators(g_title)
            if g_title_clean:
                candidates.append(g_title_clean)
    except Exception as exc:
        print(f"[title] guessit error: {exc}", flush=True)

    # Fallback ASCII sem acentos.
    ascii_candidates = []
    for c in list(candidates):
        ascii_c = strip_accents(c)
        if ascii_c and ascii_c.lower() != c.lower():
            ascii_candidates.append(ascii_c)
    candidates.extend(ascii_candidates)

    # Dedup preservando ordem e removendo genéricos.
    seen = set()
    final = []
    for c in candidates:
        if not c:
            continue
        low = c.lower().strip()
        # ignora candidatos genéricos vindos do guessit (ex: "filme")
        if low in PTBR_TAGS or low in {"filme", "movie"}:
            continue
        if low not in seen:
            seen.add(low)
            final.append(c)
    return final, year


def score_tmdb_result(candidate: str, year: int | None, item: dict) -> float:
    """Calcula score de similaridade + ajuste por ano + penalização de ruído."""
    tmdb_title = item.get("title") or item.get("name") or ""
    sim = fuzz.token_set_ratio(candidate, tmdb_title)
    score = sim

    release = (item.get("release_date") or item.get("first_air_date") or "")[:4]
    if year and release.isdigit():
        if int(release) == year:
            score += 25
        else:
            score -= 15

    # Penaliza candidato ainda com tags técnicas.
    noise = sum(1 for tag in PTBR_TAGS if re.search(rf"\\b{re.escape(tag)}\\b", candidate, re.IGNORECASE))
    score -= 5 * noise
    return score
