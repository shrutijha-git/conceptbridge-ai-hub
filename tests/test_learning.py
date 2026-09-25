import pytest
from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import mysql
from app.db.database import Base
from app.learning.practice import analyze_sales, assess
from app.rag.retrieval import split_chunks
from app.schemas.chat import VideoCreate
from pydantic import ValidationError
from uuid import uuid4

def test_mysql_schema_compiles_all_tables():
    for table in Base.metadata.sorted_tables:
        sql=str(CreateTable(table).compile(dialect=mysql.dialect()))
        assert 'CREATE TABLE' in sql

def test_calculations_are_exact_and_invalid_rows_are_reported():
    text='date,region,sales\n2026-01-01,North,0.1\n2026-01-02,North,0.2\n2026-02-02,South,10\n2026-02-30,North,100\n'
    r=analyze_sales(text)
    assert r['total']=='10.3' and r['monthly_totals'][0]['total']=='0.3'
    assert r['excluded_rows']==1

def test_csv_quotes_and_malformed_rows():
    r=analyze_sales('date,region,sales\n2026-01-01,"North, East","1,000.50"\n')
    assert r['total']=='1000.50' and r['category_totals'][0]['category']=='North, East'
    with pytest.raises(ValueError): analyze_sales('date,region,sales\n2026-01-01,North,10,extra\n')

def test_numeric_tolerance_and_no_code_execution_claim():
    assert assess('margin-1','20.005')['correct'] is True
    assert assess('margin-1','25')['correct'] is False
    f=assess('python-distinct','def second_largest(numbers):\n    return sorted(numbers)[-2]')
    assert f['correct'] is None and f['verdict']=='needs-practice' and f['code_executed'] is False

def test_chunks_keep_page_numbers():
    chunks=split_chunks([(3,'Third normal form '*100)])
    assert len(chunks)>1 and all(p==3 for p,_ in chunks)

def test_video_intervals_validate_without_fabricated_resources():
    with pytest.raises(ValidationError):
        VideoCreate(session_id=uuid4(),video_id='invalid',title='Test',topic='3NF',start_seconds=100,end_seconds=50,evidence='Test evidence supplied by a curator.')
