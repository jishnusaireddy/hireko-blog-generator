# 🚀 Hireko.ai Blog Generator — Railway Deployment

AI-powered blog generator with a beautiful web form UI. Fill in your topic, audience, goal, and word count — get a publication-ready blog with Hireko.ai theme in one click.

## ✨ Features

- **Web Form UI** — Topic, Audience, Goal, Word Count, Template selector
- **3-Iteration AI Pipeline** — Deep Research → Fact-Check Audit → HTML Rendering
- **Hireko.ai Editorial Theme** — Professional, branded blog output
- **FastAPI Backend** — REST API with Swagger docs at `/docs`
- **One-Click Deploy** — Dockerfile ready for Railway.app

## 📁 Project Structure

```
├── blog_agent/              # AI engine (research + generation + templates)
│   ├── __init__.py
│   ├── agent.py             # Pydantic AI agent + web search
│   ├── deps.py              # Dependencies dataclass
│   ├── llm_provider.py      # LLM factory (OpenRouter/Groq/NVIDIA)
│   ├── pipeline.py          # 3-iteration blog pipeline
│   └── templates.py         # Hireko HTML/CSS editorial templates
├── blog-dashboard/
│   └── index.html           # Web form UI (self-contained)
├── server.py                # FastAPI application
├── pydantic_ai_harness.py   # File/Shell/Code helper classes
├── requirements.txt         # Python dependencies
├── Dockerfile               # Docker build config
└── .env.example             # Required environment variables
```

## 🚂 Deploy to Railway.app

### Step 1: Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit - Hireko Blog Generator"
git remote add origin https://github.com/YOUR_USERNAME/hireko-blog-generator.git
git push -u origin main
```

### Step 2: Deploy on Railway

1. Go to [railway.app](https://railway.app) and sign in
2. Click **"New Project"** → **"Deploy from GitHub Repo"**
3. Select your `hireko-blog-generator` repository
4. Railway auto-detects the `Dockerfile` and starts building

### Step 3: Set Environment Variables

In your Railway project dashboard, go to the **Variables** tab and add:

| Variable | Value |
|---|---|
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `SERPER_API_KEY` | Your Serper API key |
| `LLM_PROVIDER` | `openrouter` |
| `LLM_MODEL` | `qwen/qwen3.7-flash` |

> ⚠️ Railway automatically sets the `PORT` variable — the server already reads it.

### Step 4: Get Your Public URL

Railway generates a public URL like:
```
https://hireko-blog-generator-production.up.railway.app
```

Visit it → you'll see the Blog Studio form → fill in details → generate!

## 🔗 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Redirects to dashboard form |
| `/dashboard/index.html` | GET | Blog generator form UI |
| `/api/generate` | POST | Generate a blog article |
| `/api/health` | GET | Health check & server status |
| `/api/templates` | GET | List available templates |
| `/api/blogs` | GET | List generated blogs |
| `/docs` | GET | Swagger API documentation |

## 🏠 Local Development

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/hireko-blog-generator.git
cd hireko-blog-generator

# Create .env from example
cp .env.example .env
# Edit .env and add your real API keys

# Install dependencies
pip install -r requirements.txt

# Run the server
python server.py
# → Open http://localhost:8000
```

## 🛠️ Tech Stack

- **Backend**: Python, FastAPI, Uvicorn
- **AI**: Pydantic AI, OpenRouter (Qwen 3.7 Flash)
- **Search**: Serper API (Google Search)
- **Frontend**: Vanilla HTML/CSS/JS (glassmorphism dark theme)
- **Deploy**: Docker, Railway.app
