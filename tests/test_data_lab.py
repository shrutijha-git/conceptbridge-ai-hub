from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from app.db.database import Base, get_db
from app.main import create_app
from app.models.entities import DataAnalysis, LearningSession


CSV = 'date,region,sales\n2026-01-01,North,0.1\n2026-01-02,South,0.2\n2026-02-01,North,10\n'


def upload(client, session_id=None, **choices):
    form = {'grouping': 'month', 'aggregation': 'sum', 'chart': 'bar', **choices}
    if session_id is not None:
        form['session_id'] = session_id
    return client.post('/api/v1/practice/data', data=form,
                       files={'file': ('sales.csv', CSV, 'text/csv')})


def test_saved_result_survives_new_app_and_preserves_decimals(client, session_id, test_db):
    response = upload(client, session_id)
    assert response.status_code == 200, response.text
    saved = response.json()
    assert saved['filename'] == 'sales.csv'
    assert saved['calculated_reference']['monthly_totals'][0]['total'] == '0.3'
    assert saved['calculated_reference']['total'] == '10.3'
    assert saved['choices']['chart'] == 'bar'
    assert saved['session_id'] == session_id
    assert saved['created_at'].endswith('Z')

    # A new FastAPI instance and ORM connection must read from the database,
    # independently of browser state or the old app instance.
    app = create_app(initialize_database=False)
    def database():
        with test_db() as db:
            yield db
    app.dependency_overrides[get_db] = database
    with TestClient(app) as reopened:
        assert reopened.get(f'/api/v1/sessions/{session_id}/data-analyses').json() == [saved]


def test_saved_history_keeps_sessions_separate_and_latest_first(client, session_id):
    other = client.post('/api/v1/demo/session', json={
        'degree': 'MBA', 'subject': 'Analytics', 'topic': 'Other session',
    }).json()['session_id']
    first = upload(client, session_id).json()
    second = upload(client, session_id, grouping='region', chart='pie').json()
    separate = upload(client, other).json()
    url = f'/api/v1/sessions/{session_id}/data-analyses'
    assert client.get(url).json() == [second, first]
    assert client.get(url + '?limit=1').json() == [second]
    assert second['feedback']['verdict'] == 'needs-practice'
    assert client.get(f'/api/v1/sessions/{other}/data-analyses').json() == [separate]
    assert client.get(url + '?limit=101').status_code == 422


def test_invalid_requests_do_not_create_saved_results(client, session_id, test_db):
    assert upload(client, str(uuid4())).status_code == 404
    assert upload(client, session_id, chart='unknown').status_code == 422
    assert upload(client, session_id, date_column='x' * 256).status_code == 422
    invalid = client.post('/api/v1/practice/data', data={
        'session_id': session_id, 'grouping': 'month', 'aggregation': 'sum', 'chart': 'bar',
    }, files={'file': ('bad.csv', 'not a dataset', 'text/csv')})
    assert invalid.status_code == 422
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(DataAnalysis)) == 0
    assert client.get(f'/api/v1/sessions/{uuid4()}/data-analyses').status_code == 404


def test_original_sessionless_api_remains_a_calculation_only(client, test_db):
    response = upload(client)
    assert response.status_code == 200
    assert response.json()['calculated_reference']['total'] == '10.3'
    assert 'analysis_id' not in response.json()
    with test_db() as db:
        assert db.scalar(select(func.count()).select_from(DataAnalysis)) == 0


def test_additive_table_creation_keeps_existing_session(client, session_id, test_db):
    with test_db() as db:
        engine = db.get_bind()
        DataAnalysis.__table__.drop(engine)
        Base.metadata.create_all(engine)
        assert db.get(LearningSession, session_id) is not None
    assert upload(client, session_id).status_code == 200
