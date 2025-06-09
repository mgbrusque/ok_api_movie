import requests
from bs4 import BeautifulSoup

# URL da requisição
url = "https://ok.ru/profile/582429885532/video/uploaded?cmd=FriendVideoMoviesRedesignRBlock&gwt.requested=5fc0fc02T1747215554957&st.cmd=userFriendVideoNew&st.friendId=582429885532&st.fetchType=UPLOADED&"

# Headers com cookies de sessão válidos
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Accept": "*/*",
    "Referer": "https://ok.ru/",
    "Content-Type": "application/x-www-form-urlencoded",
    "Cookie": (
        "nbp=1; TZD=-6.1135; CDN=; TZ=-6; viewport=1050; LASTSRV=ok.ru; "
        "_dc_gtm_UA-188421184-1=1; JSESSIONID=af3379c4bfa8563a9421d88510e45a95bcf301a0c54b80d.351ffb6a; "
        "AUTHCODE=tr6lc112NYnF7Q6XXxWz7opykjpy6VCx8YqOYpmix9SDQspVUjL70c4pWZi6aaOtkZrbuHY70vFRKe_BUqx8p9U0uR7xwMxNybwFmHF2uQYCF58B2s15k1hctfkdkdYbuuMexEWIihtXSMoawA_5; "
        "_ym_uid=1747428955369840455; _ga=GA1.2.1706929892.1747428955; _gid=GA1.2.626961530.1747428955; "
        "msg_conf=2468555756792551; _statid=43fa588b-ef48-451b-ba12-39122f301158; TD=1135; "
        "bci=-2471863981935566784; tmr_lvid=5e4d0f9c7e5ed649ea925426287c6bc9; "
        "_ga_GEGXS3ELM6=GS2.1.s1747428954$o1$g0$t1747428970$j0$l0$h0; _ym_d=1747428955; "
        "_ym_isad=1; tmr_lvidTS=1747428954821"
    )
}

# Requisição POST
response = requests.post(url, headers=headers)

if response.status_code == 200:
    print("✅ Sucesso na requisição!")

    # Parse do HTML com BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')
    video_cards = soup.select('.video-card')

    resultados = []

    for card in video_cards:
        try:
            titulo = card.select_one('.video-card_n').get_text(strip=True)
            duracao = card.select_one('.video-card_duration').get_text(strip=True)
            imagem = card.select_one('img.video-card_img')['src']

            resultados.append({
                'titulo': titulo,
                'duracao': duracao,
                'imagem': imagem
            })
        except Exception as e:
            print(f"❌ Erro ao processar card: {e}")

    # Exibe os vídeos encontrados
    for r in resultados:
        print(f"\n🎬 {r['titulo']}\n⏱  {r['duracao']}\n🖼  {r['imagem']}")
else:
    print(f"❌ Erro {response.status_code}: {response.text}")
