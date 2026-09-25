import re
from sqlalchemy import select
from app.models.entities import DocumentChunk, SessionDocument

STOP={'the','and','for','this','that','with','what','why','how','from','have','does','can','you','your','are','a','an','is','of','to','in','i','me','it'}

def terms(text):
    return {t for t in re.findall(r'\w+',text.lower()) if t not in STOP and len(t)>1}

def split_chunks(pages, size=1100, overlap=150):
    result=[]
    for page_number,text in pages:
        text=re.sub(r'[ \t]+',' ',text).strip()
        for start in range(0,len(text),size-overlap):
            chunk=text[start:start+size].strip()
            if chunk: result.append((page_number,chunk))
    return result

def retrieve_chunks(db,session_id,query,limit=4):
    rows=db.scalars(select(DocumentChunk).join(SessionDocument,SessionDocument.document_id==DocumentChunk.document_id)
        .where(SessionDocument.session_id==session_id).limit(800)).all()
    words=terms(query)
    ranked=sorted(((len(words & terms(c.text)),c.chunk_no,c) for c in rows), key=lambda x:(-x[0],x[1],x[2].id))
    return [c for score,_,c in ranked[:limit] if score>0]
