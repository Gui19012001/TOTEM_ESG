# Totem ESG — Fábrica

Agente ESG interativo para operadores industriais.
Stack: **FastAPI** (backend) · **Streamlit** (admin) · **Kivy** (APK Android) · **Railway** (cloud) · **GitHub Actions** (CI/CD)

---

## Estrutura do projeto

```
totem-esg/
├── backend/
│   ├── main.py              # FastAPI — agente, logs, base ESG
│   └── requirements.txt
├── admin/
│   └── admin_app.py         # Streamlit — painel de gestão
├── totem/
│   └── totem_app.py         # Kivy — APK Android
├── buildozer.spec           # Config do build Android
├── Procfile                 # Railway: como rodar o backend
├── .env.example             # Template de variáveis
├── .gitignore
└── .github/
    └── workflows/
        ├── deploy.yml       # Deploy automático no Railway
        └── build_apk.yml    # Build + signing do APK
```

---

## 1. Setup local

```bash
git clone https://github.com/SEU_USER/totem-esg.git
cd totem-esg

# Criar .env a partir do template
cp .env.example .env
# Editar .env com suas chaves

# Instalar dependências do backend
pip install -r backend/requirements.txt

# Rodar backend local
uvicorn backend.main:app --reload --port 8000

# Rodar admin (outro terminal)
pip install streamlit pandas requests
API_URL=http://localhost:8000 streamlit run admin/admin_app.py

# Rodar totem Kivy (outro terminal)
pip install kivy requests
API_URL=http://localhost:8000 python totem/totem_app.py
```

---

## 2. Deploy Railway

1. Acesse [railway.app](https://railway.app) e crie um projeto
2. Conecte ao seu repositório GitHub
3. Em **Variables**, adicione:
   - `ANTHROPIC_API_KEY` → sua chave Anthropic
   - `ADMIN_TOKEN` → senha do painel admin
   - `DB_PATH` → `/data/totem.db`
4. Em **Settings → Volume**, monte `/data` para persistência do SQLite
5. Adicione `RAILWAY_TOKEN` nos **GitHub Secrets** do repositório

A partir daí, todo `git push main` faz deploy automático.

---

## 3. Build do APK

Adicione estes **GitHub Secrets** no repositório:

| Secret | Como gerar |
|---|---|
| `KEYSTORE_BASE64` | `base64 -w 0 keystore.jks` |
| `KEY_ALIAS` | alias da sua chave |
| `KEY_PASSWORD` | senha da chave |
| `STORE_PASSWORD` | senha do keystore |
| `API_URL` | URL do Railway (ex: `https://totem-esg.up.railway.app`) |

O APK é gerado automaticamente no push e fica disponível em **Actions → Artifacts**.

Para gerar o keystore (se não tiver):
```bash
keytool -genkey -v -keystore keystore.jks \
  -alias totem-esg -keyalg RSA -keysize 2048 \
  -validity 10000
```

---

## 4. Instalar APK no tablet

```bash
# Via ADB (USB)
adb install bin/totem-esg-signed.apk

# Ou baixe o artifact do GitHub Actions e instale manualmente
```

---

## 5. Variáveis de ambiente por tablet

Para identificar cada tablet nos logs, defina antes de rodar:
```bash
TABLET_ID=totem-linha-a python totem/totem_app.py
```

No APK, edite `totem_app.py` antes do build ou use um arquivo de config local.

---

## Custos estimados

| Item | Custo |
|---|---|
| Railway (Hobby) | ~$5/mês |
| Claude Sonnet 4.6 | ~$0,008 por pergunta |
| 1.000 perguntas/mês | ~R$40 |
| GitHub Actions | Gratuito (2.000 min/mês) |
