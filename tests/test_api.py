import json
from uuid import uuid4
from sqlalchemy import select,func
from app.models.entities import Message,ChatTurn,ProviderCall,LearningSession
from app.ai.providers.base import ProviderResult,ProviderError
from app.ai.router import RoutedResult,RoutingError
from app.api import routes


def chat_body(session_id,**kw): return {'session_id':session_id,'request_id':str(uuid4()),'message':'Why is StudentID → DeptID → DeptName transitive?','provider':'auto',**kw}

def test_health_and_mock_session(client,session_id):
    assert client.get('/api/v1/health').status_code==200
    r=client.post('/api/v1/chat',json=chat_body(session_id))
    assert r.status_code==200,r.text
    assert r.json()['is_mock'] and r.json()['provider_used']=='mock'
    assert not r.json()['fallback_used']
    history=client.get(f'/api/v1/sessions/{session_id}/messages').json()
    assert [m['role'] for m in history]==['user','assistant']

def test_idempotency_prevents_duplicate_messages_and_usage(client,session_id,test_db):
    body=chat_body(session_id)
    a=client.post('/api/v1/chat',json=body);b=client.post('/api/v1/chat',json=body)
    assert a.status_code==b.status_code==200
    assert a.json()==b.json()
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(Message))==2
        assert db.scalar(select(func.count()).select_from(ProviderCall))==1
    body['message']='A different request'
    assert client.post('/api/v1/chat',json=body).status_code==409

def test_failure_rolls_back_transcript_and_same_id_can_retry(client,session_id,test_db,monkeypatch):
    original=routes.generate_with_routing
    def failed(*args): raise RoutingError(ProviderError('timeout','Try again',True),[{'provider':'gemini','status':'failed'}])
    monkeypatch.setattr(routes,'generate_with_routing',failed)
    body=chat_body(session_id)
    r=client.post('/api/v1/chat',json=body)
    assert r.status_code==503
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(Message))==0
        assert db.scalar(select(func.count()).select_from(ChatTurn))==0
    monkeypatch.setattr(routes,'generate_with_routing',original)
    assert client.post('/api/v1/chat',json=body).status_code==200

def test_switching_provider_keeps_memory_and_recent_turns(client,session_id,monkeypatch):
    seen=[]
    def generate(provider,system,messages,*args):
        seen.append((provider,system,messages))
        return RoutedResult(ProviderResult('Next, decompose the table.',provider,model='test-double'),False,[])
    monkeypatch.setattr(routes,'generate_with_routing',generate)
    assert client.patch(f'/api/v1/sessions/{session_id}/memory',json={'learning_objective':'Decompose into 3NF','misconceptions':['Confused partial and transitive dependency']}).status_code==200
    a=client.post('/api/v1/chat',json=chat_body(session_id,provider='anthropic'))
    b=client.post('/api/v1/chat',json=chat_body(session_id,provider='openai',message='Which table should I split first?'))
    assert a.status_code==b.status_code==200
    assert b.json()['provider_changed'] and b.json()['previous_provider']=='anthropic'
    assert len(seen[1][2])==3
    assert 'Decompose into 3NF' in seen[1][1] and 'Confused partial' in seen[1][1]
    assert seen[1][2][-1]['content']=='Which table should I split first?'
    history=client.get(f'/api/v1/sessions/{session_id}/messages').json()
    assert [h['role'] for h in history]==['user','assistant','user','assistant']

def test_context_compacts_and_full_history_remains(client,session_id):
    for i in range(8):
        r=client.post('/api/v1/chat',json=chat_body(session_id,message=f'Question {i}: tell me about 3NF.'))
        assert r.status_code==200,r.text
        assert r.json()['context']['context_bytes']<=r.json()['context']['budget_bytes']
    assert len(client.get(f'/api/v1/sessions/{session_id}/messages').json())==16
    memory=client.get(f'/api/v1/sessions/{session_id}/memory').json()
    assert memory['completed_turns']==8 and memory['recap']

def test_source_upload_and_context_retrieval(client,session_id,monkeypatch):
    notes='Third Normal Form. A transitive dependency occurs when StudentID determines DeptID and DeptID determines DeptName.'
    r=client.post('/api/v1/documents',data={'session_id':session_id},files={'file':('dbms.txt',notes,'text/plain')})
    assert r.status_code==201,r.text
    assert r.json()['retrieval']=='lexical' and not r.json()['embeddings_created']
    reply=client.post('/api/v1/chat',json=chat_body(session_id))
    assert reply.status_code==200,reply.text
    assert reply.json()['context']['source_chunks']

def test_practice_checks_and_progress(client,session_id):
    r=client.post('/api/v1/practice/attempts',json={'session_id':session_id,'question_id':'buyer-power','answer':'Supplier power'})
    assert r.status_code==201 and r.json()['feedback']['correct'] is False
    next_q=r.json()['feedback']['follow_up'];assert next_q['id']=='supplier-power' and 'answer' not in next_q
    r=client.post('/api/v1/practice/attempts',json={'session_id':session_id,'question_id':'supplier-power','answer':'Supplier power'})
    assert r.json()['feedback']['correct'] is True
    progress=client.get(f'/api/v1/sessions/{session_id}/progress').json()
    assert progress['attempts']==2 and not progress['mastery_calibrated']
    assert 'Buyer vs supplier power' not in client.get(f'/api/v1/sessions/{session_id}/memory').json()['learning_state'].get('weak_concepts',[])

def test_invalid_requests_and_origin_are_rejected(client,session_id):
    assert client.post('/api/v1/chat',json=chat_body(session_id,message='   ')).status_code==422
    assert client.post('/api/v1/chat',json=chat_body(session_id,provider='unknown')).status_code==422
    assert client.post('/api/v1/demo/session',json={},headers={'Origin':'https://unexpected.example'}).status_code==403

def test_legacy_messages_are_retained_when_new_turns_are_added(client,session_id,test_db):
    from datetime import datetime,timedelta
    now=datetime.now()
    with test_db() as db:
        db.add_all([Message(session_id=session_id,role='user',content='Legacy question',created_at=now-timedelta(seconds=2)),
                    Message(session_id=session_id,role='assistant',content='Legacy answer',provider='mock',created_at=now-timedelta(seconds=1))])
        db.commit()
    r=client.post('/api/v1/chat',json=chat_body(session_id))
    assert r.status_code==200,r.text
    rows=client.get(f'/api/v1/sessions/{session_id}/messages').json()
    assert len(rows)==4 and rows[0]['content']=='Legacy question' and rows[1]['content']=='Legacy answer'


def test_invalid_csv_and_video_are_actionable_errors(client,session_id):
    r=client.post('/api/v1/practice/data',data={'grouping':'month','aggregation':'sum','chart':'line'},
        files={'file':('bad.csv','date,region,sales\n"unclosed','text/csv')})
    assert r.status_code==422
    r=client.post('/api/v1/videos/segments',json={'session_id':session_id,'video_id':'M7lc1UVf-VE',
        'title':'API test fixture','topic':'Test only','start_seconds':20,'end_seconds':10,
        'evidence':'Synthetic test of interval validation; not a learning recommendation.'})
    assert r.status_code==422
