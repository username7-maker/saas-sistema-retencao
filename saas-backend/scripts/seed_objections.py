from pathlib import Path
import sys

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models import ObjectionResponse


DEFAULT_OBJECTIONS = [
    {
        "trigger_keywords": ["tecnofit", "outro sistema", "ja uso", "ja tenho sistema"],
        "objection_summary": "Complementaridade com sistema atual",
        "response_template": (
            "O AI GYM OS nao substitui seu sistema operacional. Ele complementa a operacao com BI, retencao "
            "e automacoes que normalmente o ERP da academia nao entrega."
        ),
    },
    {
        "trigger_keywords": ["caro", "preco", "valor", "investimento", "custo"],
        "objection_summary": "Custo versus ROI",
        "response_template": (
            "O investimento precisa ser comparado com a receita em risco. Em geral, recuperar alguns alunos "
            "ja paga o projeto e transforma churn em caixa preservado."
        ),
    },
    {
        "trigger_keywords": ["nao tenho tempo", "sem tempo", "muito ocupado", "complicado"],
        "objection_summary": "Falta de tempo para operar",
        "response_template": (
            "A proposta do AI GYM OS e reduzir trabalho manual. O sistema identifica risco, sugere acoes e "
            "automatiza boa parte do acompanhamento."
        ),
    },
    {
        "trigger_keywords": ["vou pensar", "preciso ver", "depois", "nao sei"],
        "objection_summary": "Postergar decisao",
        "response_template": (
            "Faz sentido avaliar com calma, mas churn continua acontecendo todos os dias. Posso te mostrar "
            "em 15 minutos o impacto financeiro para decidir com base em numeros."
        ),
    },
    {
        "trigger_keywords": ["minha equipe", "time nao vai usar", "pessoal nao aprende"],
        "objection_summary": "Baixa adesao da equipe",
        "response_template": (
            "O sistema foi desenhado para a equipe operar o minimo possivel. A maior parte do valor vem da "
            "automacao e de dashboards com acoes objetivas."
        ),
    },
    {
        "trigger_keywords": ["nao funciona", "nao acredito", "prova", "resultado"],
        "objection_summary": "Prova de resultado",
        "response_template": (
            "A melhor forma de validar e olhar para os seus dados. Podemos usar seu diagnostico para mostrar "
            "o potencial de recuperacao e o retorno esperado."
        ),
    },
    {
        "trigger_keywords": ["contrato", "fidelidade", "preso", "amarrado"],
        "objection_summary": "Receio contratual",
        "response_template": (
            "A conversa comercial pode ser estruturada com flexibilidade. O foco e demonstrar retorno rapido "
            "e reduzir o risco da decisao para a academia."
        ),
    },
    {
        "trigger_keywords": ["academi", "pequen", "poucos alunos"],
        "objection_summary": "Academia pequena demais",
        "response_template": (
            "Mesmo academias menores sofrem com churn e perda de recorrencia. O AI GYM OS ajuda justamente a "
            "priorizar os alunos certos e preservar receita com menos equipe."
        ),
    },
]


def main() -> None:
    db = SessionLocal()
    created = 0
    updated = 0
    try:
        for item in DEFAULT_OBJECTIONS:
            existing = db.scalar(
                select(ObjectionResponse).where(
                    ObjectionResponse.gym_id.is_(None),
                    ObjectionResponse.objection_summary == item["objection_summary"],
                )
            )
            if existing:
                existing.trigger_keywords = item["trigger_keywords"]
                existing.response_template = item["response_template"]
                existing.is_active = True
                db.add(existing)
                updated += 1
            else:
                db.add(ObjectionResponse(gym_id=None, is_active=True, **item))
                created += 1
        db.commit()
        print(f"Seed concluido: {created} criadas, {updated} atualizadas.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
