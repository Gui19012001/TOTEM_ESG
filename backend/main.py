"""
Totem ESG — Backend FastAPI
Serve: agente Claude, base de conhecimento ESG, logs de interações
Deploy: Railway (conectado ao GitHub, deploy automático no push)
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import anthropic
import sqlite3
import os
import json
from datetime import datetime
from pathlib import Path

# ── Configuração ──────────────────────────────────────────────
app = FastAPI(title="Totem ESG API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restringir ao domínio do totem
    allow_methods=["*"],
    allow_headers=["*"],
)

ANTHROPIC_KEY = os.environ["ANTHROPIC_API_KEY"]   # GitHub Secret → Railway env var
ADMIN_TOKEN   = os.environ.get("ADMIN_TOKEN", "esg-admin-2024")
DB_PATH       = Path(os.environ.get("DB_PATH", "data/totem.db"))

DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Banco de dados ────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS knowledge (
                id       INTEGER PRIMARY KEY,
                category TEXT NOT NULL,
                title    TEXT NOT NULL,
                content  TEXT NOT NULL,
                updated  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                tablet_id  TEXT,
                topic      TEXT,
                question   TEXT NOT NULL,
                answer     TEXT NOT NULL,
                tokens_in  INTEGER,
                tokens_out INTEGER,
                created    TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS quick_questions (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                topic    TEXT NOT NULL,
                question TEXT NOT NULL
            );

            INSERT OR IGNORE INTO quick_questions (topic, question) VALUES
                ('ambiental', 'Qual é a meta de redução de CO₂?'),
                ('ambiental', 'Como está o consumo de água?'),
                ('ambiental', 'Quanto resíduo reciclamos?'),
                ('seguranca', 'Quantos dias sem acidentes?'),
                ('seguranca', 'Quais EPIs devo usar hoje?'),
                ('social',    'Quais programas sociais temos?'),
                ('politicas', 'Quais são nossas certificações?');
        """)

init_db()

# ── Modelos Pydantic ──────────────────────────────────────────
class ChatRequest(BaseModel):
    question:  str
    topic:     str = "ambiental"
    tablet_id: str = "totem-01"
    history:   list[dict] = []

class KnowledgeItem(BaseModel):
    category: str
    title:    str
    content:  str

class QuickQuestion(BaseModel):
    topic:    str
    question: str

# ── Auth simples para rotas admin ─────────────────────────────
def verify_admin(x_admin_token: str = Header(...)):
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Token inválido")
    return True

# ── Endpoints públicos (totem) ────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/api/quick-questions")
def get_quick_questions(topic: Optional[str] = None, db: sqlite3.Connection = Depends(get_db)):
    if topic:
        rows = db.execute(
            "SELECT * FROM quick_questions WHERE topic = ?", (topic,)
        ).fetchall()
    else:
        rows = db.execute("SELECT * FROM quick_questions").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/chat")
async def chat(req: ChatRequest, db: sqlite3.Connection = Depends(get_db)):
    # Monta base de conhecimento do banco
    rows = db.execute("SELECT category, title, content FROM knowledge").fetchall()
    knowledge_text = ""
    for row in rows:
        knowledge_text += f"[{row['category'].upper()}] {row['title']}:\n{row['content']}\n\n"

    topics = {
        "ambiental": "Indicadores Ambientais (emissões, resíduos, água, energia)",
        "seguranca": "Segurança e Saúde do Trabalho (SST, EPIs, acidentes)",
        "social":    "Programas Sociais e metas de impacto social",
        "politicas": "Políticas internas e Certificações (ISO 14001, ISO 45001, etc.)",
    }
    topic_label = topics.get(req.topic, req.topic)

    system = f"""Você é o Agente ESG de uma fábrica industrial.
Responda SEMPRE em português brasileiro, de forma clara e simples.
O público são operadores do chão de fábrica — use frases curtas, linguagem direta.
Foco atual: {topic_label}.

{'BASE DE CONHECIMENTO DA EMPRESA:\n' + knowledge_text if knowledge_text else 'ATENÇÃO: Base de conhecimento ainda não configurada. Responda com boas práticas gerais de ESG e oriente o operador a consultar o responsável da área.'}

Se não souber com as informações disponíveis, diga honestamente e sugira contatar o responsável ESG."""

    messages = req.history[-8:] + [{"role": "user", "content": req.question}]

    try:
        client   = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
        response = client.messages.create(
            model      = "claude-sonnet-4-6",
            max_tokens = 1024,
            system     = system,
            messages   = messages,
        )
        answer     = response.content[0].text
        tokens_in  = response.usage.input_tokens
        tokens_out = response.usage.output_tokens

        db.execute(
            "INSERT INTO logs (tablet_id, topic, question, answer, tokens_in, tokens_out, created) VALUES (?,?,?,?,?,?,?)",
            (req.tablet_id, req.topic, req.question, answer, tokens_in, tokens_out, datetime.utcnow().isoformat())
        )
        db.commit()

        return {"answer": answer, "tokens_in": tokens_in, "tokens_out": tokens_out}

    except anthropic.APIError as e:
        raise HTTPException(status_code=502, detail=f"Erro na API Claude: {str(e)}")

# ── Endpoints admin (protegidos) ──────────────────────────────
@app.get("/api/admin/knowledge", dependencies=[Depends(verify_admin)])
def list_knowledge(db: sqlite3.Connection = Depends(get_db)):
    rows = db.execute("SELECT * FROM knowledge ORDER BY category, title").fetchall()
    return [dict(r) for r in rows]

@app.post("/api/admin/knowledge", dependencies=[Depends(verify_admin)])
def upsert_knowledge(item: KnowledgeItem, db: sqlite3.Connection = Depends(get_db)):
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
def delete_knowledge(item_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM knowledge WHERE id=?", (item_id,))
    db.commit()
    return {"status": "ok"}

@app.get("/api/admin/logs", dependencies=[Depends(verify_admin)])
def get_logs(limit: int = 100, topic: Optional[str] = None, db: sqlite3.Connection = Depends(get_db)):
    if topic:
        rows = db.execute(
            "SELECT * FROM logs WHERE topic=? ORDER BY created DESC LIMIT ?", (topic, limit)
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
    tokens = db.execute(
        "SELECT SUM(tokens_in) as ti, SUM(tokens_out) as to_ FROM logs"
    ).fetchone()
    by_topic = db.execute(
        "SELECT topic, COUNT(*) as n FROM logs GROUP BY topic"
    ).fetchall()
    return {
        "total_questions": total,
        "today_questions": today,
        "total_tokens_in":  tokens["ti"] or 0,
        "total_tokens_out": tokens["to_"] or 0,
        "by_topic": [dict(r) for r in by_topic],
    }

@app.post("/api/admin/quick-questions", dependencies=[Depends(verify_admin)])
def add_quick_question(q: QuickQuestion, db: sqlite3.Connection = Depends(get_db)):
    db.execute(
        "INSERT INTO quick_questions (topic, question) VALUES (?,?)",
        (q.topic, q.question)
    )
    db.commit()
    return {"status": "ok"}

@app.delete("/api/admin/quick-questions/{q_id}", dependencies=[Depends(verify_admin)])
def delete_quick_question(q_id: int, db: sqlite3.Connection = Depends(get_db)):
    db.execute("DELETE FROM quick_questions WHERE id=?", (q_id,))
    db.commit()
    return {"status": "ok"}
