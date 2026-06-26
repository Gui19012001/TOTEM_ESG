"""
Totem ESG — Painel Admin (Streamlit)
Gerencie a base de conhecimento, visualize logs e estatísticas.
Rode localmente: streamlit run admin/admin_app.py
"""

import streamlit as st
import requests
import pandas as pd
from datetime import datetime
import os

# ── Configuração ──────────────────────────────────────────────
st.set_page_config(
    page_title="Totem ESG — Admin",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_URL     = os.environ.get("API_URL", "http://localhost:8000")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "esg-admin-2024")
HEADERS     = {"x-admin-token": ADMIN_TOKEN}

CATEGORIES = {
    "ambiental": "🌿 Ambiental",
    "seguranca": "🦺 Segurança e Saúde",
    "social":    "👥 Social",
    "politicas": "📋 Políticas e Certificações",
}

# ── Helpers ───────────────────────────────────────────────────
def api(method, path, **kwargs):
    try:
        r = getattr(requests, method)(f"{API_URL}{path}", headers=HEADERS, timeout=10, **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Não foi possível conectar ao backend. Verifique se o servidor está rodando.")
        return None
    except Exception as e:
        st.error(f"Erro: {e}")
        return None

# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.shields.io/badge/ESG-Totem-1D9E75?style=for-the-badge", use_container_width=True)
    st.markdown("---")
    page = st.radio(
        "Navegação",
        ["📊 Dashboard", "📝 Base de Conhecimento", "💬 Perguntas Rápidas", "📋 Logs de Uso"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption(f"Backend: `{API_URL}`")
    if st.button("🔄 Verificar conexão"):
        r = api("get", "/health")
        if r:
            st.success(f"Online ✅  {r.get('timestamp','')[:19]}")

# ── PÁGINA: Dashboard ─────────────────────────────────────────
if page == "📊 Dashboard":
    st.title("📊 Dashboard ESG")
    stats = api("get", "/api/admin/stats")
    if stats:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Perguntas hoje",   stats["today_questions"])
        c2.metric("Total histórico",  stats["total_questions"])
        c3.metric("Tokens entrada",   stats.get('total_tokens_in', 'N/A'))
        c4.metric("Tokens saída",     stats.get('total_tokens_out', 'N/A'))

        st.markdown("---")
        st.subheader("Perguntas por tema")
        if stats["by_topic"]:
            df = pd.DataFrame(stats["by_topic"])
            df["topic"] = df["topic"].map(CATEGORIES).fillna(df["topic"])
            df.columns = ["Tema", "Perguntas"]
            st.bar_chart(df.set_index("Tema"))
        else:
            st.info("Nenhuma interação registrada ainda.")

        custo_est = 0  # Gemini gratuito — sem custo de tokens

# ── PÁGINA: Base de Conhecimento ──────────────────────────────
elif page == "📝 Base de Conhecimento":
    st.title("📝 Base de Conhecimento ESG")

    knowledge = api("get", "/api/admin/knowledge")

    col_form, col_list = st.columns([1, 1])

    with col_form:
        st.subheader("Adicionar / Atualizar")
        with st.form("knowledge_form", clear_on_submit=True):
            category = st.selectbox("Categoria", list(CATEGORIES.keys()),
                                    format_func=lambda x: CATEGORIES[x])
            title   = st.text_input("Título", placeholder="Ex: Meta de CO₂ 2025")
            content = st.text_area("Conteúdo", height=200,
                                   placeholder="Ex: Meta de redução de 30% nas emissões de CO₂ até dezembro de 2025. Baseline: 1.200 toneladas/ano em 2022.")
            submitted = st.form_submit_button("💾 Salvar", use_container_width=True, type="primary")
            if submitted and title and content:
                r = api("post", "/api/admin/knowledge",
                        json={"category": category, "title": title, "content": content})
                if r:
                    st.success("✅ Salvo com sucesso!")
                    st.rerun()

    with col_list:
        st.subheader("Itens cadastrados")
        if knowledge:
            for item in knowledge:
                cat_label = CATEGORIES.get(item["category"], item["category"])
                with st.expander(f"{cat_label} — {item['title']}"):
                    st.write(item["content"])
                    st.caption(f"Atualizado: {item['updated'][:19]}")
                    if st.button("🗑️ Remover", key=f"del_{item['id']}"):
                        api("delete", f"/api/admin/knowledge/{item['id']}")
                        st.rerun()
        else:
            st.info("Nenhum item cadastrado. Adicione informações ESG da empresa ao lado.")

        # Upload de texto em lote
        st.markdown("---")
        st.subheader("📥 Importar texto em lote")
        st.caption("Cole aqui um bloco grande de texto. O agente usará como contexto completo.")
        bulk_cat  = st.selectbox("Categoria do bloco", list(CATEGORIES.keys()),
                                 format_func=lambda x: CATEGORIES[x], key="bulk_cat")
        bulk_title = st.text_input("Título do bloco", "Base ESG Completa", key="bulk_title")
        bulk_text  = st.text_area("Texto completo", height=150, key="bulk_text",
                                  placeholder="Cole aqui relatório ESG, política ambiental, indicadores...")
        if st.button("📤 Importar bloco", use_container_width=True):
            if bulk_text:
                r = api("post", "/api/admin/knowledge",
                        json={"category": bulk_cat, "title": bulk_title, "content": bulk_text})
                if r:
                    st.success("✅ Bloco importado!")
                    st.rerun()

# ── PÁGINA: Perguntas Rápidas ──────────────────────────────────
elif page == "💬 Perguntas Rápidas":
    st.title("💬 Perguntas Rápidas dos Totens")
    st.caption("Estas perguntas aparecem como atalhos na tela do operador.")

    questions = api("get", "/api/quick-questions")
    if questions:
        df = pd.DataFrame(questions)
        df["topic"] = df["topic"].map(CATEGORIES).fillna(df["topic"])
        for _, row in pd.DataFrame(questions).iterrows():
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{CATEGORIES.get(row['topic'], row['topic'])}** — {row['question']}")
            if c2.button("Remover", key=f"dq_{row['id']}"):
                api("delete", f"/api/admin/quick-questions/{row['id']}")
                st.rerun()

    st.markdown("---")
    st.subheader("Adicionar pergunta")
    with st.form("quick_form", clear_on_submit=True):
        q_topic = st.selectbox("Tema", list(CATEGORIES.keys()), format_func=lambda x: CATEGORIES[x])
        q_text  = st.text_input("Pergunta", placeholder="Ex: Qual o prazo da certificação ISO 14001?")
        if st.form_submit_button("➕ Adicionar", type="primary"):
            if q_text:
                api("post", "/api/admin/quick-questions", json={"topic": q_topic, "question": q_text})
                st.rerun()

# ── PÁGINA: Logs ──────────────────────────────────────────────
elif page == "📋 Logs de Uso":
    st.title("📋 Logs de Interações")

    col_f1, col_f2 = st.columns([1, 3])
    topic_filter = col_f1.selectbox("Filtrar por tema",
                                    ["todos"] + list(CATEGORIES.keys()),
                                    format_func=lambda x: "Todos" if x == "todos" else CATEGORIES[x])
    limit = col_f2.slider("Últimas N interações", 10, 500, 100)

    params = {"limit": limit}
    if topic_filter != "todos":
        params["topic"] = topic_filter

    logs = api("get", "/api/admin/logs", params=params)
    if logs:
        df = pd.DataFrame(logs)
        df["created"] = pd.to_datetime(df["created"]).dt.strftime("%d/%m %H:%M")
        df["topic"]   = df["topic"].map(CATEGORIES).fillna(df["topic"])
        df = df.rename(columns={
            "created": "Data/Hora", "tablet_id": "Tablet",
            "topic": "Tema", "question": "Pergunta",
            "tokens_in": "Tok. entrada", "tokens_out": "Tok. saída"
        })

        st.dataframe(
            df[["Data/Hora", "Tablet", "Tema", "Pergunta", "Tok. entrada", "Tok. saída"]],
            use_container_width=True, hide_index=True,
        )

        st.download_button(
            "📥 Exportar CSV",
            df.to_csv(index=False).encode("utf-8"),
            f"logs_esg_{datetime.now().strftime('%Y%m%d')}.csv",
            "text/csv",
        )

        st.markdown("---")
        st.subheader("Perguntas mais frequentes")
        top = df["Pergunta"].value_counts().head(10).reset_index()
        top.columns = ["Pergunta", "Frequência"]
        st.dataframe(top, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum log encontrado.")
