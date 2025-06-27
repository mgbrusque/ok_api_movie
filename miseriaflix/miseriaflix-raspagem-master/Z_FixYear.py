import psycopg2

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

# Recuperar os valores do campo "anotroca" da tabela "ano"
cursor.execute("SELECT anotroca FROM ano")
valores_anotroca = [row[0] for row in cursor.fetchall()]

# Percorrer os registros da tabela "filmes"
for registro in registros:
    nome_atualizado = registro[1]  # Nome inicialmente atualizado com o valor original
    
    # Percorrer a lista de valores do campo "anotroca" da tabela "ano"
    for valor in valores_anotroca:
        # Verificar se o valor está presente no campo "nome"
        if valor in nome_atualizado:
            # Obter o valor correspondente do campo "ano" da tabela "ano"
            cursor.execute("SELECT ano FROM ano WHERE anotroca = %s", (valor,))
            resultado = cursor.fetchone()
            ano_substituto = resultado[0] if resultado else ""
            
            # Substituir o valor no campo "nome" pelo valor correspondente no campo "ano"
            nome_atualizado = nome_atualizado.replace(valor, ano_substituto)
    
    print(f'Nome original: {registro[1]}')
    print(f'Nome atualizado: {nome_atualizado}')
    print()
    
    # Executar o comando UPDATE para atualizar o campo "nome" na tabela "filmes"
    #cursor.execute("UPDATE filmes SET nome = %s WHERE nome = %s", (nome_atualizado, registro[1]))
    #conn.commit()

# Fechar o cursor e a conexão com o banco de dados
cursor.close()
conn.close()
