import csv
from datetime import datetime, timedelta
import random

# Vamos fingir que hoje é 10 de Fevereiro de 2026
HOJE = datetime(2026, 2, 10)

def criar_dados_falsos():
    nomes = ["Alice", "Bruno", "Caio", "Debora", "Erick", "Fabia", "Guto", "Hanna"]
    sobrenomes = ["Silva", "Santos", "Oliveira", "Souza", "Costa"]

    with open('alunos_teste.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        # Cabeçalho que o Python vai ler depois
        writer.writerow(['name', 'email', 'last_checkin'])

        for i in range(20):
            nome_completo = f"{random.choice(nomes)} {random.choice(sobrenomes)} {i}"
            email = f"aluno{i}@academia.com"

            # Criando alunos com tempos de ausência diferentes
            # Alguns foram ontem, outros há 20 dias
            dias_atras = random.randint(0, 25)
            data_checkin = HOJE - timedelta(days=dias_atras)

            writer.writerow([nome_completo, email, data_checkin.strftime('%Y-%m-%d')])

    print("✅ Sucesso! O arquivo 'alunos_teste.csv' foi criado na raiz.")

if __name__ == "__main__":
    criar_dados_falsos()
