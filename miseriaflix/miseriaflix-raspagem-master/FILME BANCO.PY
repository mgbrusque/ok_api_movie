from cmath import exp
import numpy as np
import time
from urllib.parse import urldefrag
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
import psycopg2
import re
import datetime

# Obter a data atual (sem a hora)
data_atual = datetime.datetime.now().date()

    # -- LOGIN BEGIN -- #
login = 'moitaum@gmail.com'
senha = 'speaker1A'

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service)

driver.set_window_position(-10000,0)
driver.get('https://ok.ru/profile/579383564192/video/uploaded')

time.sleep(5.0)

driver.find_element(By.LINK_TEXT,"Sign in").click()

time.sleep(5.0)

driver.find_element(By.NAME,"st.email").send_keys(login)
driver.find_element(By.NAME,"st.password").send_keys(senha)

time.sleep(1)# WAIT INSERT LOGIN AND PASS 

driver.find_element(By.XPATH,'//*[@id="hook_Block_LoginPopupReact"]/auth-login-popup/div/div[2]/div/div[2]/form/div/div[1]/div[3]/div/button').click()
# -- LOGIN END -- #

# Estabelecer a conexão com o banco de dados PostgreSQL
conn = psycopg2.connect(
    host="bp5aolwbf3qrstecvtny-postgresql.services.clever-cloud.com",
    database="bp5aolwbf3qrstecvtny",
    user="upi6tqi6dxccuuerpwjg",
    password="rz7SsSKNHuN43DmC14Wq"
)
cursor = conn.cursor()

cursor.execute("SELECT id, server FROM server t1 where t1.active = 1")
link_data = cursor.fetchall()

print(link_data)

#for arr in arr:
for link_id, link in link_data:

    countServer = link_id
    print(link_id)
    print(link)
    
    time.sleep(0.5) 

    driver.get(link)
    driver.refresh()

    time.sleep(1) 

    SCROLL_PAUSE_TIME = 0.5

    # # -- SCROLL BEGIN  -- #
    #Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        try:
            # Scroll down to bottom
            sitescroll = driver.page_source
            time.sleep(SCROLL_PAUSE_TIME)
            soup = BeautifulSoup(sitescroll, 'html.parser')
            scrollsoup = soup.find("a", attrs={"class": "js-show-more link-show-more"})
            scrollid = scrollsoup.get('id')
            b = "//*[@id='"+scrollid+"']"
            element = driver.find_element(By.XPATH,b)
            driver.execute_script("arguments[0].click();", element)
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait to load page
            time.sleep(SCROLL_PAUSE_TIME)

            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        except:
            print("")
    # -- SCROLL END -- #

    # -- GET DATA BEGIN -- #
    time.sleep(30)
    
    site= driver.page_source

    time.sleep(1)
        
    soup = BeautifulSoup(site, 'html.parser')

    countFilms = 1

    dados_filmes = []
    filmes = []
    for test in soup.find_all("div", attrs={"class": "video-card js-movie-card"}): 
        dado_filme = [] 
        dado_filme.append(test.get('data-id'))#id do filme
        dado_filme.append(test.find("a", attrs={"class": "video-card_n ellip"}).get_text())#nome 
        dado_filme.append(test.find("div", attrs={"class": "video-card_duration-w"}).get_text())#tempo 
        if len(test.find_all("img")) == 0:
            dado_filme.append("Error")
            ImagemFilm= "Error" #https://img.freepik.com/vetores-premium/poster-de-cinema-realista-pipoca-balde-fita-de-filme-de-claquete-e-bobina-pipoca-voando-em-movimento_208581-1714.jpg
        else: 
            dado_filme.append(test.img['src'])#imagem 
            ImagemFilm=test.img['src']
        filmes.append(dado_filme)
        
        # RETIRA CARACTERES QUE NÃO PRECISO #
        emoji_pattern = re.compile("["
                        u"\U0001F600-\U0001F64F"  # emoticons
                        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
                        u"\U0001F680-\U0001F6FF"  # transport & map symbols
                        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                        u"\U00002500-\U00002BEF"  # chinese char
                        u"\U00002702-\U000027B0"
                        u"\U00002702-\U000027B0"
                        u"\U000024C2-\U0001F251"
                        u"\U0001f926-\U0001f937"
                        u"\U00010000-\U0010ffff"
                        u"\u2640-\u2642" 
                        u"\u2600-\u2B55"
                        u"\u200d"
                        u"\u23cf"
                        u"\u23e9"
                        u"\u231a"
                        u"\ufe0f"  # dingbats
                        u"\u3030"
                                    "]+", re.UNICODE)
        nomeFilme = (emoji_pattern.sub(r'', test.find("a", attrs={"class": "video-card_n ellip"}).get_text())) # no emoji

        dados_filmes.append((test.get('data-id'), nomeFilme.upper(), test.find("div", attrs={"class": "video-card_duration-w"}).get_text(), ImagemFilm, countServer, countFilms, data_atual))
        countFilms =countFilms+ 1
    # -- GET DATA END -- #

    # Insert new employee
    cursor.executemany("""
        INSERT INTO filmes (id, nome, tempo, imagem, idserver, ordernum, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE
        SET nome = EXCLUDED.nome, tempo = EXCLUDED.tempo, imagem = EXCLUDED.imagem,
            idserver = EXCLUDED.idserver, ordernum = EXCLUDED.ordernum, created_at = EXCLUDED.created_at
        """, dados_filmes)
    conn.commit()   
cursor.close()
conn.close()
driver.close()

#exec(open("Project\ApiOk Diario.py").read())


