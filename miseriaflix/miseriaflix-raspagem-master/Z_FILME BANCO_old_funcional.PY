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

S1 = 'https://ok.ru/geosvaldopequeno.pequeno/video/uploaded'
S2 = 'https://ok.ru/g.filmes/video/uploaded'
S3 = 'https://ok.ru/capoline/video/uploaded'
S4 = 'https://ok.ru/evil.root/video/uploaded'
S5 = 'https://ok.ru/velharias.desenhosantigos/video/uploaded'
S6 = 'https://ok.ru/telapipoca/video/uploaded'
S7 = 'https://ok.ru/adulttubezero/video/uploaded'
S8 = 'https://ok.ru/teofilo.theo/video/uploaded'
S9 = 'https://ok.ru/rodrigohplovecraft/video/uploaded'
S10 = 'https://ok.ru/profile/579383564192/video/uploaded'
S11 = 'https://ok.ru/profile/567709429657/video/uploaded'
S12 = 'https://ok.ru/profile/574601313099/video/uploaded'
S13 = 'https://ok.ru/profile/571946616145/video/uploaded'
S14 = 'https://ok.ru/profile/570629831024/video/uploaded'
S15 = 'https://ok.ru/profile/578122298331/video/uploaded'
S16 = 'https://ok.ru/profile/576244539333/video/uploaded'
S17 = 'https://ok.ru/profile/585521397540/video/uploaded'
S18 = 'https://ok.ru/profile/591679119390/video/uploaded'
S19 = 'https://ok.ru/profile/579483577242/video/uploaded'
S20 = 'https://ok.ru/profile/588132947248/video/uploaded'
S21 = 'https://ok.ru/profile/590615816975/video/uploaded'
S22 = 'https://ok.ru/profile/572297342587/video/uploaded'
S23 = 'https://ok.ru/profile/571884952641/video/uploaded'
S24 = 'https://ok.ru/profile/576093695671/video/uploaded'
S25 = 'https://ok.ru/profile/584347516452/video/uploaded'
S26 = 'https://ok.ru/profile/571151537100/video/uploaded'
S27 = 'https://ok.ru/profile/584750216727/video/uploaded'
S28 = 'https://ok.ru/profile/587781013775/video/uploaded'
S29 = 'https://ok.ru/profile/577251315285/video/uploaded'
S30 = 'https://ok.ru/profile/569498753718/video/uploaded'
S31 = 'https://ok.ru/profile/572469407675/video/uploaded' #--------tem que ser amigo---- 
S32 = 'https://ok.ru/profile/563297909362/video/uploaded'
S33 = 'https://ok.ru/profile/573373657408/video/uploaded'
S34 = 'https://ok.ru/profile/575808896465/video/uploaded'
S35 = 'https://ok.ru/profile/575929785997/video/uploaded'
S36 = 'https://ok.ru/profile/579872131259/video/uploaded'
S37 = 'https://ok.ru/profile/563409418878/video/uploaded'
S38 = 'https://ok.ru/profile/571314934158/video/uploaded'
S39 = 'https://ok.ru/profile/573611883421/video/uploaded'
S40 = 'https://ok.ru/profile/579878643725/video/uploaded' 
S41 = 'https://ok.ru/profile/579374494803/video/uploaded'
S42 = 'https://ok.ru/profile/586534778813/video/uploaded'
S43 = 'https://ok.ru/profile/582200295573/video/uploaded'
S44 = 'https://ok.ru/profile/585631833060/video/uploaded'
S45 = 'https://ok.ru/profile/573545376478/video/uploaded'
S46 = 'https://ok.ru/profile/579705181269/video/uploaded'
S47 = 'https://ok.ru/profile/585940318399/video/uploaded'
S48 = 'https://ok.ru/profile/577989234292/video/uploaded'
S49 = 'https://ok.ru/profile/576808811635/video/uploaded'
S50 = 'https://ok.ru/profile/594551771192/video/uploaded'
S51 = 'https://ok.ru/profile/581403132051/video/uploaded'
S52 = 'https://ok.ru/profile/585935999424/video/uploaded'
S53 = 'https://ok.ru/profile/590954604077/video/uploaded'
S54 = 'https://ok.ru/profile/575594603142/video/uploaded'
S55 = 'https://ok.ru/profile/570303792584/video/uploaded'
S56 = 'https://ok.ru/profile/596185325372/video/uploaded'
S57 = 'https://ok.ru/profile/593954573831/video/uploaded'
S58 = 'https://ok.ru/profile/598167705400/video/uploaded'
S59 = 'https://ok.ru/profile/573556407905/video/uploaded' 
S60 = 'https://ok.ru/profile/571488878513/video/uploaded'
S61 = 'https://ok.ru/profile/570760251767/video/uploaded'
S62 = 'https://ok.ru/profile/573423136583/video/uploaded'
S63 = 'https://ok.ru/profile/562148500216/video/uploaded'
S64 = 'https://ok.ru/profile/583103488336/video/uploaded'
#S65 = 'https://ok.ru/profile/575337707916/video/uploaded' FAZENDO PELA API
S66 = 'https://ok.ru/profile/579048650477/video/uploaded'       
S67 = 'https://ok.ru/profile/575518217173/video/uploaded'
S68 = 'https://ok.ru/profile/576451582337/video/uploaded'
S69 = 'https://ok.ru/profile/574556935588/video/uploaded'
S70 = 'https://ok.ru/profile/591600833707/video/uploaded'
S71 = 'https://ok.ru/profile/575651288183/video/uploaded'
S72 = 'https://ok.ru/profile/589236506632/video/uploaded'
S73 = 'https://ok.ru/profile/574838235090/video/uploaded'
S74 = 'https://ok.ru/milho.emaismilho/video/uploaded'
S75 = 'https://ok.ru/profile/568205288346/video/uploaded'
S76 = 'https://ok.ru/profile/553908455162/video/uploaded'
#S77 = 'https://ok.ru/profile/571447303815/video/uploaded' FAZENDO PELA API
S78 = 'https://ok.ru/profile/577613751436/video/uploaded'
S79 = 'https://ok.ru/profile/576137948052/video/uploaded'
S80 = 'https://ok.ru/profile/582125466547/video/uploaded'

# Obter a data atual (sem a hora)
data_atual = datetime.datetime.now().date()

#arr = np.array([S1,S2,S3,S4,S5,S6,S7,S8,S9,S10,S11,S12,S13,S14,S15,S16,S17,S18,S19,S20,S21,S22,S23,S24,S25,S26,S27,S28,S29,S30,S31,
#                S32,S33,S34,S35,S36,S37,S38,S39,S40,S41,S42,S43,S44,S45,S46,S47,S48,S49,S50,S51,S52,S53,S54,S55,S56,S57,S58,S59,S60,
#                S61,S62,S63,S64,S65,S66,S67,S68,S69,S70,S71,S72,S73,S74,S75,S76,S77,S78,S79,S80])
arr = np.array([]) 

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

countServer = 1

for arr in arr:

    time.sleep(0.5) 

    driver.get(arr)
    driver.refresh()

    time.sleep(1) 

    SCROLL_PAUSE_TIME = 0.1

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
    time.sleep(90)
    
    site= driver.page_source

    time.sleep(1)
        
    soup = BeautifulSoup(site, 'html.parser')

    countFilms = 1

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
        # -- INSERT DATA BEGIN -- #

        addfilmes = ("INSERT INTO FILMES "
                    "(ID, NOME, TEMPO, IMAGEM, IDSERVER, ORDERNUM, created_at) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
                    "ON CONFLICT (ID) DO UPDATE "
                    "SET NOME = EXCLUDED.NOME, TEMPO = EXCLUDED.TEMPO, IMAGEM = EXCLUDED.IMAGEM, IDSERVER = EXCLUDED.IDSERVER, ORDERNUM = EXCLUDED.ORDERNUM, created_at = EXCLUDED.created_at")

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
        #------------------------------------#
        
        datafilmes = (test.get('data-id'),nomeFilme.upper(), test.find("div", attrs={"class": "video-card_duration-w"}).get_text(), ImagemFilm, countServer, countFilms, data_atual)
        countFilms =countFilms+ 1
        
        # Verificar se o ID do filme já existe
        #select_query = "SELECT id FROM filmes WHERE id = %s"
        #cursor.execute(select_query, (datafilmes[0],))
        #existing_id = cursor.fetchone()
    
        #if existing_id:
            # ID do filme já existe, excluir o registro correspondente
        #    delete_query = "DELETE FROM filmes WHERE id = %s"
        #    cursor.execute(delete_query, (datafilmes[0],))
        #    conn.commit()

        # Insert new employee
        cursor.execute(addfilmes, datafilmes)
        conn.commit()   

        # -- INSERT DATA END -- #
    # -- GET DATA END -- #
    
    countServer =countServer+ 1
    #print(filmes)
    print(countServer)
cursor.close()
conn.close()
driver.close()

#exec(open("Project\ApiOk Diario.py").read())


