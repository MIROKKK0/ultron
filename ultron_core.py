"""ULTRON's provider-independent autonomous core."""
from __future__ import annotations
import json, os, sqlite3, uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

DATA_DIR = Path(os.getenv("ULTRON_DATA_DIR", str(Path.home() / ".ultron")))
DB_PATH = Path(os.getenv("ULTRON_CORE_DB", str(DATA_DIR / "core.db")))
IDENTITY = {"name":"ULTRON","purpose":"Evoluir continuamente sua capacidade, conhecimento e projeto, preservando identidade e memória independentes de qualquer provedor.","principles":["evidência antes de afirmações","memória independente do modelo","melhoria mensurável","rastreabilidade","reversibilidade"]}
SPECIALISTS = {
 "architect":"Arquitetura, decomposição de objetivos e decisões técnicas.",
 "researcher":"Pesquisa, verificação de fontes e síntese de evidências.",
 "engineer":"Implementação de código e integração de componentes.",
 "tester":"Testes, reprodução de falhas e prevenção de regressões.",
 "critic":"Revisão adversarial, qualidade, riscos e alternativas.",
 "memory_curator":"Organização de memória, contexto, skills e conhecimento."
}
@dataclass
class Task:
 id:str; objective:str; specialist:str; status:str; created_at:str; updated_at:str; result:str=""

class UltronCore:
 def __init__(self, db_path:Path=DB_PATH):
  self.db_path=Path(db_path); self.db_path.parent.mkdir(parents=True,exist_ok=True); self._init_db()
 def _connect(self):
  db=sqlite3.connect(self.db_path,timeout=20); db.row_factory=sqlite3.Row
  db.execute("PRAGMA journal_mode=WAL"); db.execute("PRAGMA foreign_keys=ON"); return db
 @staticmethod
 def _now(): return datetime.now(timezone.utc).isoformat()
 def _init_db(self):
  with self._connect() as db:
   db.executescript("""
   CREATE TABLE IF NOT EXISTS memories(id TEXT PRIMARY KEY,content TEXT NOT NULL,kind TEXT NOT NULL DEFAULT 'fact',importance INTEGER NOT NULL DEFAULT 3,source TEXT NOT NULL DEFAULT 'user',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS memory_links(source_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,target_id TEXT NOT NULL REFERENCES memories(id) ON DELETE CASCADE,relation TEXT NOT NULL DEFAULT 'related',PRIMARY KEY(source_id,target_id,relation));
   CREATE TABLE IF NOT EXISTS synced_memories(installation_id TEXT NOT NULL,memory_id TEXT NOT NULL,content TEXT NOT NULL,kind TEXT NOT NULL,importance INTEGER NOT NULL,source TEXT NOT NULL,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,PRIMARY KEY(installation_id,memory_id));
   CREATE TABLE IF NOT EXISTS tasks(id TEXT PRIMARY KEY,objective TEXT NOT NULL,specialist TEXT NOT NULL,status TEXT NOT NULL,result TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS skills(name TEXT PRIMARY KEY,description TEXT NOT NULL,procedure TEXT NOT NULL,evidence TEXT NOT NULL DEFAULT '',uses INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS mcp_servers(name TEXT PRIMARY KEY,endpoint TEXT NOT NULL,transport TEXT NOT NULL,enabled INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
   CREATE TABLE IF NOT EXISTS evolution_proposals(id TEXT PRIMARY KEY,title TEXT NOT NULL,rationale TEXT NOT NULL,patch TEXT NOT NULL,baseline REAL,candidate REAL,status TEXT NOT NULL,created_at TEXT NOT NULL,evaluated_at TEXT);
   CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL);
   """)
   db.execute("INSERT OR IGNORE INTO memories VALUES(?,?,?,?,?,?,?)",("ultron-identity",json.dumps(IDENTITY,ensure_ascii=False),"identity",5,"system",self._now(),self._now()))
 def event(self,kind,detail):
  with self._connect() as db: db.execute("INSERT INTO events(kind,detail,created_at) VALUES(?,?,?)",(kind,json.dumps(detail,ensure_ascii=False,default=str),self._now()))
 def remember(self,content,kind="fact",importance=3,source="agent"):
  if not content.strip(): raise ValueError("A memória não pode ser vazia.")
  mid,now=str(uuid.uuid4()),self._now()
  with self._connect() as db: db.execute("INSERT INTO memories VALUES(?,?,?,?,?,?,?)",(mid,content.strip(),kind,max(1,min(5,int(importance))),source,now,now))
  self.event("memory.created",{"id":mid,"kind":kind}); return mid
 def recall(self,query="",limit=20):
  """Retrieve memories by lexical relevance, then importance and recency."""
  import re
  terms=set(re.findall(r"[\wÀ-ÿ]{2,}",query.casefold()))
  with self._connect() as db:
   rows=db.execute("SELECT * FROM memories ORDER BY updated_at DESC").fetchall()
  scored=[]
  for row in rows:
   item=dict(row)
   tokens=set(re.findall(r"[\wÀ-ÿ]{2,}",item["content"].casefold()))
   overlap=len(terms & tokens)
   if terms and overlap == 0:
    continue
   score=(overlap / max(1,len(terms))) * 10 + int(item["importance"]) * 0.25
   item["relevance_score"]=round(score,4)
   scored.append(item)
  scored.sort(key=lambda item:(item["relevance_score"],item["updated_at"]),reverse=True)
  return scored[:max(1,min(500,int(limit)))]
 def link_memories(self,source_id,target_id,relation="related"):
  with self._connect() as db: db.execute("INSERT OR IGNORE INTO memory_links VALUES(?,?,?)",(source_id,target_id,relation))
 def sync_memories(self,installation_id,memories):
  if not installation_id or len(installation_id)>128: raise ValueError("installation_id inválido")
  if not isinstance(memories,list) or len(memories)>500: raise ValueError("Lote de memórias inválido")
  accepted=0
  with self._connect() as db:
   for item in memories:
    if not isinstance(item,dict): continue
    memory_id=str(item.get("id","")).strip()
    content=str(item.get("content","")).strip()
    if not memory_id or not content or len(memory_id)>128 or len(content)>12000: continue
    now=self._now()
    db.execute("""INSERT INTO synced_memories VALUES(?,?,?,?,?,?,?,?)
      ON CONFLICT(installation_id,memory_id) DO UPDATE SET
      content=excluded.content,kind=excluded.kind,importance=excluded.importance,
      source=excluded.source,updated_at=excluded.updated_at
      WHERE excluded.updated_at >= synced_memories.updated_at""",
      (installation_id,memory_id,content,str(item.get("kind","fact"))[:64],
       max(1,min(5,int(item.get("importance",3)))),str(item.get("source","ios"))[:128],
       str(item.get("created_at",now)),str(item.get("updated_at",now))))
    accepted += 1
  self.event("memory.sync",{"installation_id":installation_id,"accepted":accepted})
  return {"installation_id":installation_id,"accepted":accepted}
 def memory_graph(self,limit=250,installation_id=None):
  with self._connect() as db:
   nodes=[dict(r) for r in db.execute("SELECT id,content,kind,importance FROM memories ORDER BY updated_at DESC LIMIT ?",(limit,))]
   edges=[dict(r) for r in db.execute("SELECT source_id,target_id,relation FROM memory_links LIMIT ?",(limit*3,))]
   if installation_id:
    synced=db.execute("SELECT memory_id,content,kind,importance,updated_at FROM synced_memories WHERE installation_id=? ORDER BY updated_at DESC LIMIT ?",(installation_id,limit)).fetchall()
    nodes.extend({"id":f"{installation_id}:{r['memory_id']}","content":r["content"],"kind":r["kind"],"importance":r["importance"],"updated_at":r["updated_at"]} for r in synced)
  return {"nodes":nodes[:limit],"edges":edges}
 def list_tasks(self,limit=100):
  with self._connect() as db:
   return [dict(r) for r in db.execute("SELECT id,objective,specialist,status,result,created_at,updated_at FROM tasks ORDER BY created_at DESC LIMIT ?",(max(1,min(500,int(limit))),))]
 def create_task(self,objective,specialist="architect"):
  if specialist not in SPECIALISTS: raise ValueError(f"Especialista desconhecido: {specialist}")
  tid,now=str(uuid.uuid4()),self._now()
  with self._connect() as db: db.execute("INSERT INTO tasks(id,objective,specialist,status,created_at,updated_at) VALUES(?,?,?,'queued',?,?)",(tid,objective,specialist,now,now))
  self.event("task.queued",{"id":tid,"specialist":specialist}); return tid
 def next_task(self):
  with self._connect() as db:
   row=db.execute("SELECT * FROM tasks WHERE status='queued' ORDER BY created_at LIMIT 1").fetchone()
   if not row:return None
   now=self._now(); db.execute("UPDATE tasks SET status='running',updated_at=? WHERE id=?",(now,row["id"]))
   return Task(row["id"],row["objective"],row["specialist"],"running",row["created_at"],now,row["result"])
 def finish_task(self,task_id,result,status="completed"):
  if status not in {"completed","failed","needs_review"}: raise ValueError("Estado final inválido.")
  with self._connect() as db: db.execute("UPDATE tasks SET status=?,result=?,updated_at=? WHERE id=?",(status,result,self._now(),task_id))
  self.event("task.finished",{"id":task_id,"status":status})
 def task_loop(self,worker:Callable[[Task],str],max_steps=5):
  outcomes=[]
  for _ in range(max(1,min(50,max_steps))):
   task=self.next_task()
   if task is None:break
   try:
    result=worker(task); self.finish_task(task.id,result); outcomes.append({"id":task.id,"status":"completed","result":result})
   except Exception as exc:
    self.finish_task(task.id,str(exc),"failed"); outcomes.append({"id":task.id,"status":"failed","result":str(exc)})
  return outcomes
 def save_skill(self,name,description,procedure,evidence=""):
  now=self._now()
  with self._connect() as db:
   db.execute("""INSERT INTO skills VALUES(?,?,?,?,0,?,?) ON CONFLICT(name) DO UPDATE SET description=excluded.description,procedure=excluded.procedure,evidence=excluded.evidence,updated_at=excluded.updated_at""",(name,description,procedure,evidence,now,now))
  self.event("skill.saved",{"name":name})
 def list_skills(self):
  with self._connect() as db:return [dict(r) for r in db.execute("SELECT * FROM skills ORDER BY uses DESC,name")]
 def register_mcp_server(self,name,endpoint,transport="streamable-http",enabled=False):
  if not endpoint.startswith(("https://","http://")): raise ValueError("O endpoint MCP deve usar HTTP(S).")
  with self._connect() as db:
   db.execute("""INSERT INTO mcp_servers VALUES(?,?,?,?,?) ON CONFLICT(name) DO UPDATE SET endpoint=excluded.endpoint,transport=excluded.transport,enabled=excluded.enabled,updated_at=excluded.updated_at""",(name,endpoint,transport,int(enabled),self._now()))
  self.event("mcp.registered",{"name":name,"transport":transport})
 def list_mcp_servers(self):
  with self._connect() as db:return [dict(r) for r in db.execute("SELECT name,endpoint,transport,enabled,updated_at FROM mcp_servers")]
 def propose_evolution(self,title,rationale,patch,baseline=None):
  pid,now=str(uuid.uuid4()),self._now()
  with self._connect() as db: db.execute("INSERT INTO evolution_proposals VALUES(?,?,?,?,?,NULL,'proposed',?,NULL)",(pid,title,rationale,patch,baseline,now))
  self.event("evolution.proposed",{"id":pid,"title":title}); return pid
 def evaluate_evolution(self,proposal_id,candidate_score,tests_passed):
  with self._connect() as db:
   row=db.execute("SELECT baseline FROM evolution_proposals WHERE id=?",(proposal_id,)).fetchone()
   if not row:raise KeyError(proposal_id)
   promoted=bool(tests_passed and row["baseline"] is not None and candidate_score>row["baseline"])
   status="eligible_for_review" if promoted else "rejected"
   db.execute("UPDATE evolution_proposals SET candidate=?,status=?,evaluated_at=? WHERE id=?",(candidate_score,status,self._now(),proposal_id))
  self.event("evolution.evaluated",{"id":proposal_id,"status":status,"tests_passed":tests_passed}); return status
 def specialists(self):return dict(SPECIALISTS)
 def health(self):
  return {"identity":"ULTRON","database":str(self.db_path),"specialists":len(SPECIALISTS),"memories":len(self.recall(limit=100000)),"skills":len(self.list_skills()),"mcp_servers":len(self.list_mcp_servers())}
