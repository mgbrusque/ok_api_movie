import psycopg2
import re

def extrair_numeros(texto):
    # Encontrar todos os números no texto
    numeros = re.findall(r'\d+', texto)
    
    # Filtrar os números que não são anos entre 1900 e 2100
    numeros = [num for num in numeros if not (1900 <= int(num) <= 2100)]
    
    # Filtrar os números 720, 1080 e 1444 que estão juntos
    numeros = [num for num in numeros if not (num == '360' or num == '480' or num == '720' or num == '1080' or num == '1440')]
    
    # Concatenar os números em uma sequência
    numeros_concatenados = ''.join(numeros)
    
    return numeros_concatenados

def mudar_numeros_por_letras(nome):
    # Substituir números entre letras pelos próprios números, exceto anos entre 1900 e 2100 e valores específicos
    nome = re.sub(r'\b(?!19\d{2}|20\d{2}|MP4|360|480|720|1080|1440)\d+\b', lambda x: x.group() if len(x.group()) != 4 else '', nome)
    
    # Substituir números específicos por letras
    nome = re.sub(r'0', 'O', nome)
    nome = re.sub(r'1', 'I', nome)
    nome = re.sub(r'3', 'E', nome)
    nome = re.sub(r'4', 'A', nome)
    
    return nome

# Configurar a conexão com o banco de dados PostgreSQL
conn = psycopg2.connect(
    host="bp5aolwbf3qrstecvtny-postgresql.services.clever-cloud.com",
    database="bp5aolwbf3qrstecvtny",
    user="upi6tqi6dxccuuerpwjg",
    password="rz7SsSKNHuN43DmC14Wq"
)

# Criar o cursor para executar comandos SQL
cursor = conn.cursor()

# Recuperar os registros da tabela "filmes" com tempo maior que 1 hora e 20 minutos
cursor.execute("SELECT id, nome FROM filmes WHERE char_length(tempo) >= 6 and nome not like ('%SERIE%') AND nome not like ('%SÉRIE%') AND nome not like ('%EP%')")
registros = cursor.fetchall()

# Atualizar os registros com a função mudar_numeros_por_letras
for registro in registros:
    numeros_concatenados = extrair_numeros(registro[1])
    if len(numeros_concatenados) >= 4:
        nome_atualizado = mudar_numeros_por_letras(registro[1])
        print(f'Nome original: {registro[1]}')
        print(f'Nome atualizado: {nome_atualizado}')
        print()
        
        # Executar o comando UPDATE para atualizar o nome na tabela "filmes"
        #cursor.execute("UPDATE filmes SET nome = %s WHERE id = %s", (nome_atualizado, registro[0]))
        #conn.commit()

# Fechar o cursor e a conexão com o banco de dados
cursor.close()
conn.close()
