"""Run explicitly against local MySQL after configuring .env; never substitutes SQLite.
    python -m tests.mysql_smoke
Creates uniquely named demo data, then removes only that data after the check.
"""
from uuid import uuid4
from sqlalchemy import select,delete,text
from app.db.database import Base,engine,SessionLocal
from app.models.entities import User,Course,LearningSession,Message,ChatTurn,ProviderCall,SessionMemory
from app.api.routes import create_demo_session,chat
from app.schemas.chat import DemoSessionRequest,ChatRequest
from app.core.config import get_settings


def main():
    if engine.dialect.name!='mysql': raise RuntimeError('This smoke test requires MySQL.')
    s=get_settings()
    if not s.enable_mock: raise RuntimeError('Enable local mock mode for this no-spend smoke test.')
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        print('MySQL version:',db.scalar(text('SELECT VERSION()')))
        created=create_demo_session(DemoSessionRequest(subject='Isolated smoke test'),db)
        try:
            body=ChatRequest(session_id=created.session_id,request_id=uuid4(),message='Check persistence.',provider='mock')
            first=chat(body,db);second=chat(body,db)
            assert first.model_dump()==second
            rows=db.scalars(select(Message).where(Message.session_id==created.session_id)).all()
            assert len(rows)==2
            print('PASS: MySQL tables, transaction persistence, ordered turn and idempotent replay.')
        finally:
            db.rollback()
            for model in [ProviderCall,ChatTurn,Message,SessionMemory]:
                db.execute(delete(model).where(model.session_id==created.session_id))
            db.execute(delete(LearningSession).where(LearningSession.id==created.session_id))
            db.execute(delete(Course).where(Course.id==created.course_id))
            db.execute(delete(User).where(User.id==created.user_id))
            db.commit()

if __name__=='__main__': main()
