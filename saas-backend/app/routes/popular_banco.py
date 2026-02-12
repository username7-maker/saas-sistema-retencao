from app.database import SessionLocal, engine, Base
from app import models
from datetime import datetime, timedelta
import uuid

# Garante que as tabelas existam
Base.metadata.create_all(bind=engine)

db = SessionLocal()

def criar_dados():
    print("Iniciando criação de dados de teste...")
    try:
        # 1. Criar 5 alunos "Green" (Saudáveis)
        for i in range(5):
            membro = models.Member(
                id=uuid.uuid4(),
                name=f"Aluno Green {i}",
                email=f"green{i}@teste.com",
                last_checkin=datetime.now() - timedelta(days=2),
                status=models.MemberStatus.ACTIVE,
                risk_score=10,
                risk_level=models.RiskLevel.GREEN
            )
            db.add(membro)

        # 2. Criar 3 alunos "Red" (Sumidos há mais de 30 dias)
        for i in range(3):
            membro = models.Member(
                id=uuid.uuid4(),
                name=f"Aluno Red {i}",
                email=f"red{i}@teste.com",
                last_checkin=datetime.now() - timedelta(days=45),
                status=models.MemberStatus.ACTIVE,
                risk_score=90,
                risk_level=models.RiskLevel.RED
            )
            db.add(membro)
        
        db.commit()
        print("✅ Banco populado com sucesso! 5 Green e 3 Red criados.")
    except Exception as e:
        print(f"❌ Erro ao popular banco: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    criar_dados()