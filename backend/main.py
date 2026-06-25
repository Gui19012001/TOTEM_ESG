"""
Totem ESG — Backend FastAPI com Google Gemini + Supabase
Deploy: Render.com (free tier)
Banco: Supabase PostgreSQL (dados persistentes)
"""

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import requests
from datetime import datetime

# ── Configuração ──────────────────────────────────────────────
app = FastAPI(title="Totem ESG API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_KEY    = os.environ.get("GEMINI_API_KEY", "")
ADMIN_TOKEN   = os.environ.get("ADMIN_TOKEN", "esg-admin-2024")
SUPABASE_URL  = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY  = os.environ.get("SUPABASE_KEY", "")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"gemini-2.5-flash:generateContent?key={GEMINI_KEY}"
)

# ── Headers Supabase ──────────────────────────────────────────
def supa_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def supa_get(table, params=None):
    """GET no Supabase REST API"""
    try:
        r = requests.get(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supa_headers(),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase erro: {str(e)}")

def supa_post(table, data):
    """INSERT no Supabase REST API"""
    try:
        r = requests.post(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supa_headers(),
            json=data,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase erro: {str(e)}")

def supa_patch(table, match, data):
    """UPDATE no Supabase REST API"""
    try:
        params = {k: f"eq.{v}" for k, v in match.items()}
        r = requests.patch(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supa_headers(),
            params=params,
            json=data,
            timeout=10,
        )
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase erro: {str(e)}")

def supa_delete(table, match):
    """DELETE no Supabase REST API"""
    try:
        params = {k: f"eq.{v}" for k, v in match.items()}
        r = requests.delete(
            f"{SUPABASE_URL}/rest/v1/{table}",
            headers=supa_headers(),
            params=params,
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Supabase erro: {str(e)}")

# ── Modelos Pydantic ──────────────────────────────────────────
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
    return Response(status_code=200)

@app.get("/ping")
def ping():
    return {"pong": True}

@app.head("/ping")
def ping_head():
    return Response(status_code=200)

@app.get("/api/quick-questions")
def get_quick_questions(topic: Optional[str] = None):
    params = {"select": "*", "order": "id.asc"}
    if topic:
        params["topic"] = f"eq.{topic}"
    return supa_get("quick_questions", params)

@app.post("/api/chat")
def chat(req: ChatRequest):
    if not GEMINI_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY nao configurada")
    if not SUPABASE_URL:
        raise HTTPException(status_code=500, detail="SUPABASE_URL nao configurada")

    # Base de conhecimento do Supabase
    rows = supa_get("knowledge", {"select": "category,title,content"})
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
        "Voce e o Agente ESG de uma fabrica industrial da Ibero Group.\n"
        "Responda SEMPRE em portugues brasileiro, de forma clara e simples.\n"
        "O publico sao operadores do chao de fabrica — use frases curtas e linguagem direta.\n"
        "Nao use markdown, asteriscos, hashtags ou formatacao especial nas respostas.\n"
        f"Foco atual: {topic_label}.\n\n"
    )
    if knowledge_text:
        system_text += f"BASE DE CONHECIMENTO DA EMPRESA:\n{knowledge_text}\n"
    else:
        system_text += "Base de conhecimento ainda nao configurada. Use boas praticas gerais de ESG.\n"
    system_text += "\nSe nao souber, diga honestamente e sugira contatar o responsavel ESG."

    # Histórico
    contents = []
    for msg in req.history[-8:]:
        role = "user" if msg.get("role") == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg.get("content", "")}]})
    contents.append({"role": "user", "parts": [{"text": req.question}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 2048, "temperature": 0.7},
    }

    try:
        resp = requests.post(GEMINI_URL, json=payload, timeout=45)
        resp.raise_for_status()
        data = resp.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise HTTPException(status_code=502, detail="Gemini nao retornou resposta")
        answer = candidates[0]["content"]["parts"][0]["text"]

        # Salva log no Supabase (sem travar se falhar)
        try:
            supa_post("logs", {
                "tablet_id": req.tablet_id,
                "topic":     req.topic,
                "question":  req.question,
                "answer":    answer,
            })
        except Exception:
            pass

        return {"answer": answer}

    except HTTPException:
        raise
    except requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="Gemini timeout — tente novamente")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro: {str(e)}")

# ── Endpoints admin ───────────────────────────────────────────
@app.get("/api/admin/knowledge", dependencies=[Depends(verify_admin)])
def list_knowledge():
    return supa_get("knowledge", {"select": "*", "order": "category.asc,title.asc"})

@app.post("/api/admin/knowledge", dependencies=[Depends(verify_admin)])
def upsert_knowledge(item: KnowledgeItem):
    # Verifica se já existe
    existing = supa_get("knowledge", {
        "select": "id",
        "category": f"eq.{item.category}",
        "title":    f"eq.{item.title}",
    })
    if existing:
        supa_patch("knowledge",
                   {"id": existing[0]["id"]},
                   {"content": item.content, "updated": datetime.utcnow().isoformat()})
    else:
        supa_post("knowledge", {
            "category": item.category,
            "title":    item.title,
            "content":  item.content,
        })
    return {"status": "ok"}

@app.delete("/api/admin/knowledge/{item_id}", dependencies=[Depends(verify_admin)])
def delete_knowledge(item_id: int):
    supa_delete("knowledge", {"id": item_id})
    return {"status": "ok"}

@app.get("/api/admin/logs", dependencies=[Depends(verify_admin)])
def get_logs(limit: int = 100, topic: Optional[str] = None):
    params = {"select": "*", "order": "created.desc", "limit": limit}
    if topic:
        params["topic"] = f"eq.{topic}"
    return supa_get("logs", params)

@app.get("/api/admin/stats", dependencies=[Depends(verify_admin)])
def get_stats():
    all_logs  = supa_get("logs", {"select": "topic,created"})
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    total     = len(all_logs)
    today     = sum(1 for r in all_logs if r.get("created","").startswith(today_str))

    by_topic = {}
    for r in all_logs:
        t = r.get("topic","outro")
        by_topic[t] = by_topic.get(t, 0) + 1

    return {
        "total_questions": total,
        "today_questions": today,
        "by_topic": [{"topic": k, "n": v} for k, v in by_topic.items()],
    }

@app.post("/api/admin/quick-questions", dependencies=[Depends(verify_admin)])
def add_quick(q: QuickQuestion):
    supa_post("quick_questions", {"topic": q.topic, "question": q.question})
    return {"status": "ok"}

@app.delete("/api/admin/quick-questions/{q_id}", dependencies=[Depends(verify_admin)])
def delete_quick(q_id: int):
    supa_delete("quick_questions", {"id": q_id})
    return {"status": "ok"}
