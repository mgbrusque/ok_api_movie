import requests
import psycopg2
import datetime

# Estabelecer a conexão com o banco de dados PostgreSQL
conn = psycopg2.connect(
    host="bp5aolwbf3qrstecvtny-postgresql.services.clever-cloud.com",
    database="bp5aolwbf3qrstecvtny",
    user="upi6tqi6dxccuuerpwjg",
    password="rz7SsSKNHuN43DmC14Wq"
)

# Configurar autocommit para False
conn.autocommit = False

# Crie um cursor para executar as consultas
cur = conn.cursor()

url = "https://ok.ru/web-api/v2/login/doLogin"

querystring = {"": ["", ""]}

payload = {
    "parameters": {
        "login": "moitaum@gmail.com",
        "password": "speaker1A"
    }
}
headers = {"Content-Type": "application/json"}

response = requests.request("POST", url, json=payload, headers=headers, params=querystring)

cookies = response.cookies

# Consultar os termos e filtros na tabela "pesquisa"
cur.execute("select termo, filtro from pesquisa group by termo, filtro ")
termos_rows = cur.fetchall()

# Obter a data atual (sem a hora)
data_atual = datetime.datetime.now().date()
idserver = 100  # Valor fixo para idserver

for termos_row in termos_rows:
    termos = termos_row[0].split(",")  # Separar os termos por vírgula
    filter = termos_row[1].strip()  # Obter o filtro e remover espaços em branco
    #print(termos)
    #print(filter)

    for search_text in termos:
        url = "https://ok.ru/web-api/v2/search/portal"

        duration = 'LONG'
        when = filter if filter in ['HOUR', 'DAY', 'WEEK', 'MONTH', 'YEAR'] else ''
        hd = 'OFF'

        firstindex = 0
        total_count_results = 0

        registros_inserir = []

        for idx_playload in range(0, 1000, 50):  # range até 1000
            payload = {
                "parameters": {
                    "query": search_text.strip(),  # Remover espaços em branco antes e depois do termo
                    "filters": {
                        "st.cmd": "searchResult",
                        "st.mode": "Movie",
                        "st.query": search_text.strip(),  # nome
                        "st.grmode": "Groups",  # grupo de pesquisa
                        "st.vln": duration,  # duração "LONG, SHORT, VAZIO"
                        "screen": "GLOBAL_SEARCH_VIDEO",
                        "st.vcr": when,  # tempo de pesquisa ultima "HOUR, DAY, WEEK, MONTH, YEAR, VAZIO"
                        "st.vqt": hd  # qualidade HD "ON, OFF"
                    },
                    "chunk": {
                        "firstIndex": idx_playload,
                        "offset": 0,
                        "count": 50
                    }
                }
            }

            headers = {"cookie": "bci={}; _statid={}; JSESSIONID={}; AUTHCODE={}; LASTSRV=ok.ru; vdt={}".format(
                cookies.get('bci'), cookies.get('_statid'), cookies.get('JSESSIONID'), cookies.get('AUTHCODE'),
                cookies.get('vdt'))}

            response = requests.request("POST", url, json=payload, headers=headers, params=querystring)

            dados = response.json()

            total_count = dados['result']['video']['movies']['totalCount']

            try:
                count_results = len(dados['result']['video']['movies']['results'])
                # total_count_results += count_results
            except:
                break

            idx = 0
            for i in dados['result']['video']['movies']['results']:
                if idx < count_results:
                    titulo = i['movie']['info']['title']
                    id = i['movie']['info']['id']
                    duracao_minutos = (i['movie']['info']['duration'] / 1000 / 60)
                    horas = duracao_minutos // 60
                    minutos = duracao_minutos % 60
                    segundos = int((duracao_minutos % 1) * 60)
                    formato_tempo = "{:02d}:{:02d}:{:02d}".format(int(horas), int(minutos), int(segundos))
                    tempo = (formato_tempo)
                    imagem = i['movie']['info']['thumbnail']['big']

                    ordernum = 0

                    # Adicionar o registro na lista de inserção
                    registros_inserir.append((id, titulo.upper().replace("[", " ").replace("]", " ").replace("(", " ").replace(")", " ").replace(".", " ").replace(",", "-").replace("'", "").replace('"', ''), tempo, imagem, idserver, ordernum, data_atual))
                idx += 1

        # Inserir os registros na tabela "filmes" usando ON CONFLICT
        cur.executemany("""
            INSERT INTO filmes (id, nome, tempo, imagem, idserver, ordernum, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id) DO UPDATE
            SET nome = EXCLUDED.nome, tempo = EXCLUDED.tempo, imagem = EXCLUDED.imagem,
                idserver = EXCLUDED.idserver, ordernum = EXCLUDED.ordernum, created_at = EXCLUDED.created_at
            """, registros_inserir)

# Commit as alterações no banco de dados
conn.commit()

# Fechar o cursor e a conexão com o banco de dados
cur.close()
conn.close()
