"""
Totem ESG — Backend FastAPI com Google Gemini (gratuito)
Deploy: Render.com (free tier)
Fixes: SQLite threading, HEAD endpoints, error handling robusto
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import sqlite3
import os
import requests
from datetime import datetime
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────
app = FastAPI(title="Totem ESG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_KEY  = os.environ.get("GEMINI_API_KEY", "")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "esg-admin-2024")
DB_PATH     = Path(os.environ.get("DB_PATH", "totem.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
)

# ── Banco de dados ────────────────────────────────────────────
def get_conn():
    """Abre conexão SQLite com check_same_thread=False (obrigatório para FastAPI)"""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS knowledge (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title    TEXT NOT NULL,
            content  TEXT NOT NULL,
            updated  TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            tablet_id TEXT,
            topic     TEXT,
            question  TEXT NOT NULL,
            answer    TEXT NOT NULL,
            created   TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS quick_questions (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            topic    TEXT NOT NULL,
            question TEXT NOT NULL
        );
    """)
    count = conn.execute("SELECT COUNT(*) FROM quick_questions").fetchone()[0]
    if count == 0:
        conn.executescript("""
            INSERT INTO quick_questions (topic, question) VALUES
                ('ambiental', 'Qual e a meta de reducao de CO2?'),
                ('ambiental', 'Como esta o consumo de agua?'),
                ('ambiental', 'Quanto residuo reciclamos?'),
                ('seguranca', 'Quantos dias sem acidentes?'),
                ('seguranca', 'Quais EPIs devo usar?'),
                ('social',    'Quais programas sociais temos?'),
                ('politicas', 'Quais sao nossas certificacoes?');
        """)
    conn.commit()
    conn.close()

init_db()

def get_db():
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()

# ── Modelos Pydantic v1 ───────────────────────────────────────
class ChatRequest(BaseModel):
    question:  str
    topic:     str = "ambiental"
    tablet_id: str = "totem-01"
    history:   List[Dict[str, Any]] = []

    class Config:
        orm_mode = True

class KnowledgeItem(BaseModel):
    category: str
    title:    str
    content:  str

class QuickQuestion(BaseModel):
    topic:    str
    question: str

# ── Auth admin ────────────────────────────────────────────────
def verify_admin(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Token invalido")
    return True

# ── Endpoints públicos ────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.head("/health")
def health_head():
    """Aceita HEAD do UptimeRobot"""
    return Response(status_code=200)

@app.get("/ping")
def ping():
    return {"pong": True}

@app.head("/ping")
def ping_head():
    """Aceita HEAD do UptimeRobot"""
    return Response(status_code=200)

@app.get("/api/quick-questions")
def get_quick_questions(
    topic: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    if topic:
        rows = db.execute(
            "SELECT * FROM quick_questions WHERE topic=?", (topic,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM quick_questions").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/chat")
def chat(
    req: ChatRequest,
    db: sqlite3.Connection = Depends(get_db)
):
    if not GEMINI_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY nao configurada")

    # Base de conhecimento
    rows = db.execute(
        "SELECT category, title, content FROM knowledge"
    ).fetchall()

    knowledge_text = ""
    for row in rows:
        knowledge_text += f"[{row['category'].upper()}] {row['title']}:\n{row['content']}\n\n"

    topics = {
        "ambiental": "Indicadores Ambientais (emissoes, residuos, agua, energia)",
        "seguranca": "Seguranca e Saude do Trabalho (SST, EPIs, acidentes)",
        "social":    "Programas Sociais e metas de impacto social",
        "politicas": "Politicas internas e Certificacoes (ISO 14001, ISO 45001)",
    }
    topic_label = topics.get(req.topic, req.topic)

    system_text = (
        "Voce e o Agente ESG de uma fabrica industrial.\n"
        "Responda SEMPRE em portugues brasileiro, de forma clara e simples.\n"
        "O publico sao operadores do chao de fabrica.\n"
        f"Foco atual: {topic_label}.\n\n"
    )
    if knowledge_text:
        system_text += f"BASE DE CONHECIMENTO:\n{knowledge_text}\n"
    else:
        system_text += "Base de conhecimento ainda nao configurada. Use boas praticas gerais de ESG.\n"
    system_text += "\nSe nao souber, diga honestamente e sugira contatar o responsavel ESG."

    # Histórico Gemini
    contents = []
    for msg in req.history[-8:]:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
    contents.append({"role": "user", "parts": [{"text": req.question}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.7},
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise HTTPException(status_code=502, detail="Gemini nao retornou candidatos")
        answer = candidates[0]["content"]["parts"][0]["text"]

        try:
            db.execute(
                "INSERT INTO logs (tablet_id, topic, question, answer, created) VALUES (?,?,?,?,?)",
                (req.tablet_id, req.topic, req.question, answer,
                 datetime.utcnow().isoformat())
            )
            db.commit()
        except Exception:
            pass  # Log falhou mas resposta é retornada

        return {"answer": answer}

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Gemini timeout — tente novamente")
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Erro conexao Gemini: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro: {str(e)}")

# ── Endpoints admin ───────────────────────────────────────────
@app.get("/api/admin/knowledge", dependencies=[Depends(verify_admin)])
def list_knowledge(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute(
        "SELECT * FROM knowledge ORDER BY category, title"
    ).fetchall()
    return [dict(r) for r in rows]

@app.post("/api/admin/knowledge", dependencies=[Depends(verify_admin)])
def upsert_knowledge(
    item: KnowledgeItem,
    db: sqlite3.Connection = Depends(get_db)
):
    existing = db.execute(
        "SELECT id FROM knowledge WHERE category=? AND title=?",
        (item.category, item.title)
    ).fetchone()
    now = datetime.utcnow().isoformat()
    if existing:
        db.execute(
            "UPDATE knowledge SET content=?, updated=? WHERE id=?",
            (item.content, now, existing["id"])
        )
    else:
        db.execute(
            "INSERT INTO knowledge (category, title, content, updated) VALUES (?,?,?,?)",
            (item.category, item.title, item.content, now)
        )
    db.commit()
    return {"status": "ok"}

@app.delete("/api/admin/knowledge/{item_id}", dependencies=[Depends(verify_admin)])
def delete_knowledge(
    item_id: int,
    db: sqlite3.Connection = Depends(get_db)
):
    db.execute("DELETE FROM knowledge WHERE id=?", (item_id,))
    db.commit()
    return {"status": "ok"}

@app.get("/api/admin/logs", dependencies=[Depends(verify_admin)])
def get_logs(
    limit: int = 100,
    topic: Optional[str] = None,
    db: sqlite3.Connection = Depends(get_db)
):
    if topic:
        rows = db.execute(
            "SELECT * FROM logs WHERE topic=? ORDER BY created DESC LIMIT ?",
            (topic, limit)
        ).fetchall()
    else:
        rows = db.execute(
            "SELECT * FROM logs ORDER BY created DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]

@app.get("/api/admin/stats", dependencies=[Depends(verify_admin)])
def get_stats(db: sqlite3.Connection = Depends(get_db)):
    total = db.execute("SELECT COUNT(*) as n FROM logs").fetchone()["n"]
    today = db.execute(
        "SELECT COUNT(*) as n FROM logs WHERE created LIKE ?",
        (datetime.utcnow().strftime("%Y-%m-%d") + "%",)
    ).fetchone()["n"]
    by_topic = db.execute(
        "SELECT topic, COUNT(*) as n FROM logs GROUP BY topic"
    ).fetchall()
    return {
        "total_questions": total,
        "today_questions": today,
        "by_topic": [dict(r) for r in by_topic],
    }

@app.post("/api/admin/quick-questions", dependencies=[Depends(verify_admin)])
def add_quick(
    q: QuickQuestion,
    db: sqlite3.Connection = Depends(get_db)
):
    db.execute(
        "INSERT INTO quick_questions (topic, question) VALUES (?,?)",
        (q.topic, q.question)
    )
    db.commit()
    return {"status": "ok"}

@app.delete("/api/admin/quick-questions/{q_id}", dependencies=[Depends(verify_admin)])
def delete_quick(
    q_id: int,
    db: sqlite3.Connection = Depends(get_db)
):
    db.execute("DELETE FROM quick_questions WHERE id=?", (q_id,))
    db.commit()
    return {"status": "ok"}
