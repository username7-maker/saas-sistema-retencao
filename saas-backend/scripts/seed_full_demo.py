from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
import os
import random
from sqlalchemy import select, delete, func

from app.database import SessionLocal, set_current_gym_id, clear_current_gym_id
from app.core.security import hash_password
from app.core.cache import invalidate_dashboard_cache
from app.services.analytics_view_service import refresh_member_kpis_materialized_view
from app.models import (
    Gym, User, RoleEnum, Member, MemberStatus, RiskLevel,
    Checkin, CheckinSource, Assessment, MemberGoal, TrainingPlan,
    MemberConstraints, BodyCompositionEvaluation, Lead, LeadStage,
    Task, TaskStatus, TaskPriority, NPSResponse, NPSSentiment, NPSTrigger,
    RiskAlert, InAppNotification, AuditLog, Goal, AutomationRule, MessageLog
)

TAG = os.getenv("SEED_TAG", "SEED100_FULL_V1")
SLUG = os.getenv("SEED_GYM_SLUG", "academia-local")
OWNER_EMAIL = os.getenv("SEED_OWNER_EMAIL", "owner.local@test.com")
SEED_COUNT = max(10, int(os.getenv("SEED_COUNT", "100")))
rnd = random.Random(int(os.getenv("SEED_RANDOM", "20260303")))

def sent(score:int):
    return NPSSentiment.POSITIVE if score >= 9 else (NPSSentiment.NEUTRAL if score >= 7 else NPSSentiment.NEGATIVE)

def add_user(db, gid, name, email, role):
    u = db.scalar(select(User).where(User.gym_id==gid, User.email==email, User.deleted_at.is_(None)))
    if u:
        if not u.is_active:
            u.is_active = True
            db.add(u)
            db.commit()
        return u
    u = User(gym_id=gid, full_name=name, email=email, hashed_password=hash_password("senha1234"), role=role, is_active=True)
    db.add(u); db.commit(); return u

def main():
    db = SessionLocal()
    try:
        g = db.scalar(select(Gym).where(Gym.slug==SLUG, Gym.is_active.is_(True)))
        if not g: raise RuntimeError("Gym nao encontrada")
        owner = db.scalar(select(User).where(User.gym_id==g.id, User.email==OWNER_EMAIL, User.deleted_at.is_(None), User.is_active.is_(True)))
        if not owner: raise RuntimeError("Owner nao encontrado")

        set_current_gym_id(g.id)
        mng = add_user(db, g.id, "Gerente Teste", "manager.local@test.com", RoleEnum.MANAGER)
        sal = add_user(db, g.id, "Comercial Teste", "sales.local@test.com", RoleEnum.SALESPERSON)
        rec = add_user(db, g.id, "Recepcao Teste", "reception.local@test.com", RoleEnum.RECEPTIONIST)
        users = [owner, mng, sal, rec]

        mids = db.scalars(select(Member.id).where(Member.gym_id==g.id, Member.full_name.like(f"[{TAG}]%"))).all()
        if mids:
            db.execute(delete(Task).where(Task.member_id.in_(mids)))
            db.execute(delete(Lead).where(Lead.converted_member_id.in_(mids)))
            db.execute(delete(Checkin).where(Checkin.member_id.in_(mids)))
            db.execute(delete(BodyCompositionEvaluation).where(BodyCompositionEvaluation.member_id.in_(mids)))
            db.execute(delete(MemberConstraints).where(MemberConstraints.member_id.in_(mids)))
            db.execute(delete(MemberGoal).where(MemberGoal.member_id.in_(mids)))
            db.execute(delete(TrainingPlan).where(TrainingPlan.member_id.in_(mids)))
            db.execute(delete(Assessment).where(Assessment.member_id.in_(mids)))
            db.execute(delete(NPSResponse).where(NPSResponse.member_id.in_(mids)))
            db.execute(delete(RiskAlert).where(RiskAlert.member_id.in_(mids)))
            db.execute(delete(InAppNotification).where(InAppNotification.member_id.in_(mids)))
            db.execute(delete(AuditLog).where(AuditLog.member_id.in_(mids)))
            db.execute(delete(MessageLog).where(MessageLog.member_id.in_(mids)))
            db.execute(delete(Member).where(Member.id.in_(mids)))
        db.execute(delete(Task).where(Task.title.like(f"[{TAG}]%")))
        db.execute(delete(Lead).where(Lead.full_name.like(f"[{TAG}]%")))
        db.execute(delete(InAppNotification).where(InAppNotification.title.like(f"[{TAG}]%")))
        db.execute(delete(AuditLog).where(AuditLog.action.like(f"{TAG.lower()}_%")))
        db.execute(delete(MessageLog).where(MessageLog.extra_data["seed_tag"].astext==TAG))
        db.execute(delete(Goal).where(Goal.notes==TAG))
        db.execute(delete(AutomationRule).where(AutomationRule.description.like(f"%{TAG}%")))
        db.commit()

        now = datetime.now(timezone.utc)
        today = date.today()
        fns = ["Ana","Bruno","Carla","Diego","Eduarda","Felipe","Gabi","Henrique","Isabela","Joao","Karen","Lucas","Mariana","Nicolas","Olivia","Paulo","Rafa","Sabrina","Tiago","Yasmin"]
        lns = ["Silva","Souza","Santos","Oliveira","Lima","Costa","Pereira","Almeida","Gomes","Ribeiro"]
        plans = [("Plano Mensal",Decimal("139.90"),"mensal"),("Plano Semestral",Decimal("109.90"),"semestral"),("Plano Anual",Decimal("99.90"),"anual")]

        members=[]
        for i in range(1, SEED_COUNT + 1):
            jdays = rnd.randint(15,720)
            jdate = today - timedelta(days=jdays)
            r = rnd.random()
            status = MemberStatus.ACTIVE if r<0.72 else (MemberStatus.PAUSED if r<0.87 else MemberStatus.CANCELLED)
            cdate = min(today-timedelta(days=1), jdate+timedelta(days=rnd.randint(10,max(11,jdays-1)))) if status==MemberStatus.CANCELLED else None
            rr = rnd.random()
            lvl = RiskLevel.GREEN if rr<0.58 else (RiskLevel.YELLOW if rr<0.83 else RiskLevel.RED)
            score = rnd.randint(5,49) if lvl==RiskLevel.GREEN else (rnd.randint(50,75) if lvl==RiskLevel.YELLOW else rnd.randint(76,98))
            d = rnd.randint(0,6) if (status==MemberStatus.ACTIVE and lvl==RiskLevel.GREEN) else (rnd.randint(7,18) if (status==MemberStatus.ACTIVE and lvl==RiskLevel.YELLOW) else (rnd.randint(19,45) if status==MemberStatus.ACTIVE else (rnd.randint(12,55) if status==MemberStatus.PAUSED else rnd.randint(30,120))))
            lchk = now - timedelta(days=d, hours=rnd.randint(0,18))
            if lchk.date() < jdate: lchk = datetime.combine(jdate, time(9,0), tzinfo=timezone.utc)
            if cdate and lchk.date() > cdate: lchk = datetime.combine(cdate, time(8,0), tzinfo=timezone.utc)
            p, fee, _ = rnd.choice(plans)
            members.append(Member(
                gym_id=g.id, assigned_user_id=rnd.choice(users).id, full_name=f"[{TAG}] {rnd.choice(fns)} {rnd.choice(lns)} {i:03d}",
                email=f"{TAG.lower()}.aluno{i:03d}@demo.com", phone=f"11{rnd.randint(900000000,999999999)}",
                status=status, plan_name=p, monthly_fee=fee, join_date=jdate, cancellation_date=cdate, preferred_shift=rnd.choice(["morning","afternoon","evening"]),
                nps_last_score=rnd.randint(4,10), loyalty_months=max(0,(today-jdate).days//30), risk_score=score, risk_level=lvl, last_checkin_at=lchk,
                extra_data={"seed_tag":TAG, "delinquent":"true" if (status==MemberStatus.ACTIVE and rnd.random()<0.18) else "false"}
            ))
        db.add_all(members); db.commit()

        checks=[]
        for m in members:
            base = rnd.randint(8,24) if m.status==MemberStatus.ACTIVE else (rnd.randint(2,8) if m.status==MemberStatus.PAUSED else rnd.randint(0,3))
            used=set()
            for _ in range(base):
                dt=(now-timedelta(days=rnd.randint(0,90))).replace(hour=rnd.randint(6,22),minute=rnd.choice([0,10,20,30,40,50]),second=0,microsecond=0)
                if dt.date()<m.join_date or dt.isoformat() in used: continue
                used.add(dt.isoformat())
                checks.append(Checkin(gym_id=g.id, member_id=m.id, checkin_at=dt, source=rnd.choice([CheckinSource.TURNSTILE,CheckinSource.MANUAL,CheckinSource.IMPORT]), hour_bucket=dt.hour, weekday=dt.weekday(), extra_data={"seed_tag":TAG}))
            if m.status in {MemberStatus.ACTIVE, MemberStatus.PAUSED} and m.last_checkin_at:
                dt = m.last_checkin_at.replace(minute=0, second=0, microsecond=0)
                if dt.date()>=m.join_date and dt.isoformat() not in used:
                    checks.append(Checkin(gym_id=g.id, member_id=m.id, checkin_at=dt, source=CheckinSource.MANUAL, hour_bucket=dt.hour, weekday=dt.weekday(), extra_data={"seed_tag":TAG,"anchor":True}))
        db.add_all(checks); db.commit()
        assessed = rnd.sample(members, k=80)
        ass=[],
        assessments=[]; mgoals=[]; tplans=[]; mcons=[]; bevals=[]
        for m in assessed:
            n = 2 if rnd.random()<0.35 else 1
            dates=[]
            for _ in range(n):
                maxd=max(20,(today-m.join_date).days)
                dt=datetime.combine(m.join_date+timedelta(days=rnd.randint(7,maxd)), time(rnd.randint(7,20),0), tzinfo=timezone.utc)
                if dt>now: dt=now-timedelta(days=rnd.randint(1,15))
                dates.append(dt)
            dates.sort(); last=None
            for i,dt in enumerate(dates, start=1):
                h=round(rnd.uniform(155,192),2); w=round(rnd.uniform(58,110),2); bf=round(rnd.uniform(12,34),2); bmi=round(w/((h/100)**2),2)
                a=Assessment(gym_id=g.id, member_id=m.id, evaluator_id=rnd.choice(users).id, assessment_number=i, assessment_date=dt, next_assessment_due=(dt+timedelta(days=90)).date(),
                    height_cm=Decimal(str(h)), weight_kg=Decimal(str(w)), bmi=Decimal(str(bmi)), body_fat_pct=Decimal(str(bf)), lean_mass_kg=Decimal(str(round(w*(1-bf/100),2))),
                    waist_cm=Decimal(str(round(rnd.uniform(70,110),2))), hip_cm=Decimal(str(round(rnd.uniform(80,120),2))), chest_cm=Decimal(str(round(rnd.uniform(80,125),2))),
                    arm_cm=Decimal(str(round(rnd.uniform(25,45),2))), thigh_cm=Decimal(str(round(rnd.uniform(40,75),2))), resting_hr=rnd.randint(55,95),
                    blood_pressure_systolic=rnd.randint(105,145), blood_pressure_diastolic=rnd.randint(65,95), vo2_estimated=Decimal(str(round(rnd.uniform(28,52),2))),
                    strength_score=rnd.randint(35,95), flexibility_score=rnd.randint(30,95), cardio_score=rnd.randint(30,95), observations=f"Avaliacao teste {TAG}", extra_data={"seed_tag":TAG})
                assessments.append(a); last=a
            if rnd.random()<0.8:
                mcons.append(MemberConstraints(gym_id=g.id, member_id=m.id, medical_conditions=rnd.choice([None,"Hipertensao controlada","Asma leve"]), injuries=rnd.choice([None,"Dor lombar"]), medications=rnd.choice([None,"Suplementacao"]), contraindications=rnd.choice([None,"Evitar impacto alto"]), preferred_training_times=rnd.choice(["manha","tarde","noite"]), restrictions={"seed_tag":TAG}, notes=TAG))
            if last is not None:
                tplans.append(TrainingPlan(gym_id=g.id, member_id=m.id, assessment_id=last.id, created_by_user_id=rnd.choice(users).id, name=f"Plano {TAG} {m.full_name.split()[-1]}", objective=rnd.choice(["Hipertrofia","Emagrecimento","Condicionamento"]), sessions_per_week=rnd.randint(3,6), split_type=rnd.choice(["AB","ABC","Full Body"]), start_date=max(m.join_date, today-timedelta(days=rnd.randint(0,60))), end_date=today+timedelta(days=rnd.randint(30,180)), is_active=True, plan_data={"seed_tag":TAG}, notes="Plano de treino", extra_data={"seed_tag":TAG}))
                tgt=Decimal(str(round(rnd.uniform(2,12),2))); cur=Decimal(str(round(rnd.uniform(0,float(tgt)),2))); prog=int(min(100,max(0,round((float(cur)/max(float(tgt),0.1))*100))))
                mgoals.append(MemberGoal(gym_id=g.id, member_id=m.id, assessment_id=last.id, title=rnd.choice(["Reduzir gordura","Ganhar massa","Aumentar resistencia"]), description="Meta teste", category=rnd.choice(["body","performance","health"]), target_value=tgt, current_value=cur, unit=rnd.choice(["kg","%","pontos"]), target_date=today+timedelta(days=rnd.randint(30,180)), status="active", progress_pct=prog, achieved=prog>=100, achieved_at=now if prog>=100 else None, notes="meta_seed", extra_data={"seed_tag":TAG}))
                bdate=max(m.join_date, today-timedelta(days=rnd.randint(0,120)))
                bevals.append(BodyCompositionEvaluation(gym_id=g.id, member_id=m.id, evaluation_date=bdate, weight_kg=Decimal(str(round(rnd.uniform(58,110),2))), body_fat_percent=Decimal(str(round(rnd.uniform(12,34),2))), lean_mass_kg=Decimal(str(round(rnd.uniform(40,78),2))), muscle_mass_kg=Decimal(str(round(rnd.uniform(28,55),2))), body_water_percent=Decimal(str(round(rnd.uniform(45,67),2))), visceral_fat_level=Decimal(str(round(rnd.uniform(4,16),1))), bmi=Decimal(str(round(rnd.uniform(20,33),2))), basal_metabolic_rate_kcal=Decimal(str(round(rnd.uniform(1400,2400),2))), source=rnd.choice(["tezewa","manual"]), notes=TAG, report_file_url=None))
        db.add_all(assessments); db.add_all(mcons); db.add_all(mgoals); db.add_all(tplans); db.add_all(bevals); db.commit()

        leads=[]; act=[m for m in members if m.status==MemberStatus.ACTIVE]; rnd.shuffle(act); ci=0
        for i in range(1,46):
            st=rnd.choices([LeadStage.NEW,LeadStage.CONTACT,LeadStage.VISIT,LeadStage.TRIAL,LeadStage.PROPOSAL,LeadStage.WON,LeadStage.LOST], weights=[8,8,7,6,6,5,5], k=1)[0]
            conv=None
            if st==LeadStage.WON and ci < len(act): conv=act[ci].id; ci+=1
            leads.append(Lead(gym_id=g.id, owner_id=rnd.choice([owner.id,mng.id,sal.id]), converted_member_id=conv, full_name=f"[{TAG}] Lead {i:03d}", email=f"{TAG.lower()}.lead{i:03d}@demo.com", phone=f"11{rnd.randint(900000000,999999999)}", source=rnd.choice(["instagram","google","indicacao","whatsapp","site"]), stage=st, estimated_value=Decimal(str(round(rnd.uniform(120,1400),2))), acquisition_cost=Decimal(str(round(rnd.uniform(10,220),2))), last_contact_at=now-timedelta(days=rnd.randint(0,25)), notes=[{"seed_tag":TAG}], lost_reason=rnd.choice([None,"Sem retorno","Preco","Mudanca de plano"]) if st==LeadStage.LOST else None))
        db.add_all(leads); db.commit()

        tasks=[]
        for m in members:
            src="onboarding" if (today-m.join_date).days<=30 else ("plan_followup" if ("Semestral" in m.plan_name or "Anual" in m.plan_name) else "manual")
            if m.risk_level==RiskLevel.RED: src="automation"
            st=rnd.choices([TaskStatus.TODO,TaskStatus.DOING,TaskStatus.DONE,TaskStatus.CANCELLED], weights=[55,24,16,5], k=1)[0]
            due=now+timedelta(days=rnd.randint(-12,15)); done=(due+timedelta(days=rnd.randint(0,4))) if st==TaskStatus.DONE else None
            pr=TaskPriority.MEDIUM if m.risk_level==RiskLevel.GREEN else (TaskPriority.HIGH if m.risk_level==RiskLevel.YELLOW else rnd.choice([TaskPriority.HIGH,TaskPriority.URGENT]))
            tasks.append(Task(gym_id=g.id, member_id=m.id, assigned_to_user_id=m.assigned_user_id, title=f"[{TAG}] Follow-up {m.full_name.split()[-1]}", description="Tarefa de acompanhamento", priority=pr, status=st, kanban_column=st.value, due_date=due, completed_at=done, suggested_message=f"Ola {m.full_name}, vamos revisar seu progresso?", extra_data={"seed_tag":TAG,"source":src,"plan_type":"anual" if "Anual" in m.plan_name else ("semestral" if "Semestral" in m.plan_name else "mensal")}))
        for l in leads:
            if l.stage in {LeadStage.WON, LeadStage.LOST}: continue
            st=rnd.choices([TaskStatus.TODO,TaskStatus.DOING,TaskStatus.DONE], weights=[60,25,15], k=1)[0]
            tasks.append(Task(gym_id=g.id, lead_id=l.id, assigned_to_user_id=l.owner_id, title=f"[{TAG}] Contato lead {l.full_name.split()[-1]}", description="Realizar contato comercial", priority=rnd.choice([TaskPriority.MEDIUM,TaskPriority.HIGH]), status=st, kanban_column=st.value, due_date=now+timedelta(days=rnd.randint(-7,10)), completed_at=(now-timedelta(days=rnd.randint(0,7))) if st==TaskStatus.DONE else None, suggested_message=f"Oi {l.full_name}, tudo bem?", extra_data={"seed_tag":TAG,"source":"automation" if rnd.random()<0.4 else "manual"}))
        db.add_all(tasks); db.commit()

        nps=[]; last={}; act=[m for m in members if m.status==MemberStatus.ACTIVE]
        for mb in range(12):
            ms=(today.replace(day=1).replace(year=(today.year if today.month-mb>0 else today.year-1), month=((today.month-mb-1)%12)+1))
            me=(date(ms.year+1,1,1)-timedelta(days=1)) if ms.month==12 else (date(ms.year,ms.month+1,1)-timedelta(days=1))
            for m in rnd.sample(act, k=min(len(act), rnd.randint(10,18))):
                sc = rnd.randint(0,7) if m.risk_level==RiskLevel.RED else (rnd.randint(4,8) if m.risk_level==RiskLevel.YELLOW else rnd.randint(6,10))
                rd=datetime(ms.year, ms.month, rnd.randint(1,me.day), rnd.randint(8,21), rnd.choice([0,15,30,45]), tzinfo=timezone.utc)
                nps.append(NPSResponse(gym_id=g.id, member_id=m.id, score=sc, comment=rnd.choice(["Atendimento excelente","Estrutura boa","Treino funcionando","Preciso de mais acompanhamento"]), sentiment=sent(sc), sentiment_summary="Feedback sintetico de teste", trigger=rnd.choice([NPSTrigger.MONTHLY,NPSTrigger.AFTER_SIGNUP_7D,NPSTrigger.YELLOW_RISK]), response_date=rd, extra_data={"seed_tag":TAG}))
                last[str(m.id)] = sc
        db.add_all(nps)
        for m in members:
            if str(m.id) in last:
                m.nps_last_score = last[str(m.id)]
                db.add(m)
        db.commit()
        ralerts=[]
        for m in members:
            if m.risk_level not in {RiskLevel.YELLOW, RiskLevel.RED}: continue
            rs = (m.risk_level==RiskLevel.YELLOW and rnd.random()<0.22)
            ralerts.append(RiskAlert(gym_id=g.id, member_id=m.id, score=m.risk_score, level=m.risk_level, reasons={"seed_tag":TAG,"inactive_days":rnd.randint(7,40),"nps":m.nps_last_score}, action_history=[{"at":(now-timedelta(days=rnd.randint(1,8))).isoformat(),"action":rnd.choice(["contact_attempt","task_created","whatsapp_sent"])}], automation_stage=rnd.choice(["stage_1","stage_2","stage_3"]), resolved=rs, resolved_by_user_id=owner.id if rs else None, resolved_at=(now-timedelta(days=rnd.randint(1,10))) if rs else None, created_at=now-timedelta(days=rnd.randint(0,14))))
        db.add_all(ralerts)

        notes=[]
        for i in range(1,141):
            m=rnd.choice(members); u=rnd.choice(users); rd=(now-timedelta(days=rnd.randint(0,12))) if rnd.random()<0.45 else None
            notes.append(InAppNotification(gym_id=g.id, member_id=m.id, user_id=u.id, title=f"[{TAG}] Notificacao {i:03d}", message=rnd.choice(["Membro em risco requer acompanhamento.","Lead sem contato ha mais de 3 dias.","Meta mensal abaixo do esperado.","Nova avaliacao fisica recomendada."]), category=rnd.choice(["retention","crm","system"]), read_at=rd, extra_data={"seed_tag":TAG}))
        db.add_all(notes); db.commit()

        acts=[("member_created","member"),("member_updated","member"),("lead_created","lead"),("lead_updated","lead"),("task_created","task"),("task_updated","task"),("nps_response_created","nps"),("risk_alert_created","risk_alert"),("import_members","import"),("automation_executed","automation")]
        logs=[]
        for _ in range(200):
            ac,en=rnd.choice(acts); m=rnd.choice(members); l=rnd.choice(leads); eid=m.id if en=="member" else (l.id if en=="lead" else None)
            logs.append(AuditLog(gym_id=g.id, user_id=rnd.choice(users).id, member_id=m.id if rnd.random()<0.45 else None, action=f"{TAG.lower()}_{ac}", entity=en, entity_id=eid, ip_address=f"10.0.0.{rnd.randint(2,240)}", user_agent="seed-script/1.0", details={"seed_tag":TAG}, created_at=now-timedelta(days=rnd.randint(0,30), hours=rnd.randint(0,23))))
        db.add_all(logs); db.commit()

        ms=today.replace(day=1); me=(date(ms.year+1,1,1)-timedelta(days=1)) if ms.month==12 else (date(ms.year,ms.month+1,1)-timedelta(days=1))
        goals=[
            Goal(gym_id=g.id,name="Meta MRR",metric_type="mrr",comparator="gte",target_value=Decimal("12000.00"),period_start=ms,period_end=me,alert_threshold_pct=80,is_active=True,notes=TAG),
            Goal(gym_id=g.id,name="Meta Novos Alunos",metric_type="new_members",comparator="gte",target_value=Decimal("35.00"),period_start=ms,period_end=me,alert_threshold_pct=75,is_active=True,notes=TAG),
            Goal(gym_id=g.id,name="Meta Churn",metric_type="churn_rate",comparator="lte",target_value=Decimal("5.00"),period_start=ms,period_end=me,alert_threshold_pct=90,is_active=True,notes=TAG),
            Goal(gym_id=g.id,name="Meta NPS",metric_type="nps_avg",comparator="gte",target_value=Decimal("8.00"),period_start=ms,period_end=me,alert_threshold_pct=85,is_active=True,notes=TAG),
            Goal(gym_id=g.id,name="Meta Ativos",metric_type="active_members",comparator="gte",target_value=Decimal("90.00"),period_start=ms,period_end=me,alert_threshold_pct=80,is_active=True,notes=TAG),
        ]
        db.add_all(goals); db.commit()

        rules=[
            AutomationRule(gym_id=g.id,name=f"[{TAG}] Inatividade 14d",description=f"Regra teste {TAG}",trigger_type="inactivity_days",trigger_config={"min_days":14},action_type="create_task",action_config={"title":"Aluno inativo: {nome}","priority":"high"},is_active=True,executions_count=rnd.randint(0,12),last_executed_at=now-timedelta(days=rnd.randint(1,7))),
            AutomationRule(gym_id=g.id,name=f"[{TAG}] NPS baixo",description=f"Regra teste {TAG}",trigger_type="nps_score",trigger_config={"max_score":6},action_type="notify",action_config={"title":"NPS baixo: {nome}","message":"Acompanhar nota baixa"},is_active=True,executions_count=rnd.randint(0,10),last_executed_at=now-timedelta(days=rnd.randint(1,10))),
            AutomationRule(gym_id=g.id,name=f"[{TAG}] Lead parado",description=f"Regra teste {TAG}",trigger_type="lead_stale",trigger_config={"stale_days":7},action_type="create_task",action_config={"title":"Lead parado: {nome}","priority":"high"},is_active=True,executions_count=rnd.randint(0,10),last_executed_at=now-timedelta(days=rnd.randint(1,10))),
            AutomationRule(gym_id=g.id,name=f"[{TAG}] Risco vermelho",description=f"Regra teste {TAG}",trigger_type="risk_level_change",trigger_config={"levels":["red"]},action_type="notify",action_config={"title":"Alerta vermelho: {nome}","message":"Acionar retencao"},is_active=True,executions_count=rnd.randint(0,8),last_executed_at=now-timedelta(days=rnd.randint(1,12))),
        ]
        db.add_all(rules); db.commit()

        msgs=[]
        for i in range(1,101):
            m=rnd.choice(members); r=rnd.choice(rules); ch=rnd.choice(["whatsapp","email"]); rc=m.phone if ch=="whatsapp" else (m.email or f"seed{i}@demo.com")
            msgs.append(MessageLog(gym_id=g.id, member_id=m.id, automation_rule_id=r.id, channel=ch, recipient=rc, template_name=rnd.choice(["reactivation","onboarding","nps_followup"]), content="Mensagem automatica de teste.", status=rnd.choice(["sent","delivered","read","failed"]), error_detail=None, extra_data={"seed_tag":TAG,"attempt":i}, created_at=now-timedelta(days=rnd.randint(0,30), hours=rnd.randint(0,23))))
        db.add_all(msgs); db.commit()

        try: refresh_member_kpis_materialized_view(db)
        except Exception as e: print(f"WARN: materialized view: {e}")
        invalidate_dashboard_cache("all","members","checkins","leads","nps","risk","tasks","financial",gym_id=g.id)

        out={
            "users":db.scalar(select(func.count()).select_from(User).where(User.gym_id==g.id, User.deleted_at.is_(None))),
            "members":db.scalar(select(func.count()).select_from(Member).where(Member.gym_id==g.id, Member.deleted_at.is_(None))),
            "checkins":db.scalar(select(func.count()).select_from(Checkin).where(Checkin.gym_id==g.id)),
            "assessments":db.scalar(select(func.count()).select_from(Assessment).where(Assessment.gym_id==g.id, Assessment.deleted_at.is_(None))),
            "body_composition":db.scalar(select(func.count()).select_from(BodyCompositionEvaluation).where(BodyCompositionEvaluation.gym_id==g.id)),
            "member_goals":db.scalar(select(func.count()).select_from(MemberGoal).where(MemberGoal.gym_id==g.id, MemberGoal.deleted_at.is_(None))),
            "training_plans":db.scalar(select(func.count()).select_from(TrainingPlan).where(TrainingPlan.gym_id==g.id, TrainingPlan.deleted_at.is_(None))),
            "leads":db.scalar(select(func.count()).select_from(Lead).where(Lead.gym_id==g.id, Lead.deleted_at.is_(None))),
            "tasks":db.scalar(select(func.count()).select_from(Task).where(Task.gym_id==g.id, Task.deleted_at.is_(None))),
            "nps_responses":db.scalar(select(func.count()).select_from(NPSResponse).where(NPSResponse.gym_id==g.id)),
            "risk_alerts":db.scalar(select(func.count()).select_from(RiskAlert).where(RiskAlert.gym_id==g.id)),
            "notifications":db.scalar(select(func.count()).select_from(InAppNotification).where(InAppNotification.gym_id==g.id)),
            "audit_logs":db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.gym_id==g.id)),
            "goals":db.scalar(select(func.count()).select_from(Goal).where(Goal.gym_id==g.id)),
            "automation_rules":db.scalar(select(func.count()).select_from(AutomationRule).where(AutomationRule.gym_id==g.id)),
            "message_logs":db.scalar(select(func.count()).select_from(MessageLog).where(MessageLog.gym_id==g.id)),
        }
        print("SEED_OK"); print(f"SEED_TAG={TAG}")
        for k,v in out.items(): print(f"{k}={v}")
    finally:
        clear_current_gym_id(); db.close()

if __name__=="__main__":
    main()
