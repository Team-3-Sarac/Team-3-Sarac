# MatchIQ — Soccer YouTube Intelligence Platform

A full-stack web application that analyzes trending topics, narratives, and fan sentiment across soccer YouTube content using NLP, LLMs, and the YouTube Data API v3.

**Live Demo:** https://team-3-sarac.vercel.app/

---

## What It Does

YouTube is the primary source of soccer highlights and analysis, but the volume of content makes it hard to stay informed. MatchIQ automates ingestion and analysis of soccer YouTube content across the top European leagues, surfacing trending narratives, match summaries, and fan sentiment in a centralized dashboard.

---

## Tech Stack

| Layer           | Technology                   |
|-----------------|------------------------------|
| Frontend        | React / Next.js / TypeScript |
| Styling         | Tailwind CSS                 |
| Backend         | FastAPI                      |
| Database        | MongoDB                      |
| Vector DB       | Qdrant                       |
| LLM             | OpenAI GPT-4.1-mini           |
| Data Collection | YouTube Data API v3          |
| Infrastructure  | Hetzner (Docker Compose)     |
| CI/CD           | GitHub Actions               |

---

## Project Structure

```
Team-3-Sarac/
├── .github/workflows/    → CI/CD pipeline
├── database/             → Docker/MongoDB setup
├── docs/                 → Documentation and evaluation files
├── fastapi/              → Backend (Python/FastAPI)
│   ├── data/             → Local JSON output files
│   ├── pipeline/         → LLM processing, trend scoring, narrative building
│   └── routes/           → API routes and ingestion scripts
├── frontend/             → Next.js/React UI
│   ├── api/              → API call handlers
│   ├── app/              → Pages and components
│   └── public/           → Static assets
├── scripts/
│   ├── deploy.sh         → Deployment script
│   └── run-pipeline.sh   → Manual pipeline trigger
├── .gitignore
├── Caddyfile             → Reverse proxy config
├── docker-compose.yml    → Container orchestration
└── keywords.csv          → Keyword filter list
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- Node.js 18+ / Bun (package manager)
- Docker & Docker Compose

### 1. Clone the repo
```bash
git clone https://github.com/your-org/Team-3-Sarac.git
cd Team-3-Sarac
```

### 2. Set up environment variables
Fill in your `.env`:
```
MONGO_ROOT_USERNAME=
MONGO_ROOT_PASSWORD=
MONGO_DATABASE=
MONGO_HOST=        # Hetzner IP for shared DB, localhost for local dev
MONGO_PORT=27017
OPENAI_API_KEY=
YOUTUBE_API_KEY=
QDRANT_API_KEY=
```

### 3. Install backend dependencies
```bash
cd fastapi
pip install -r requirements.txt
```

### 4. Install frontend dependencies
```bash
cd frontend
npm install
```

### 5. Run locally
```bash
# Terminal 1 — backend
cd fastapi
uvicorn main:app --reload

# Terminal 2 — frontend
cd frontend
npm run dev
```

Frontend: `http://localhost:3000` | API: `http://localhost:8000`

---

## Running the Pipeline

MatchIQ uses a **two-stage pipeline**:
- **Stage 1 (Phases 1-4):** Local data ingestion from YouTube (runs on your machine)
- **Stage 2 (Phases 5-7):** Server-side LLM analysis (runs on Hetzner with Qdrant access)

### Automated Script
```bash
./scripts/run-pipeline.sh --days 1 # number of days (default 1 day back)
```

---

## Deployment

The backend is deployed on Hetzner via Docker. To update the live server after merging to main:

```bash
ssh root@<hetzner-ip>
cd /path/to/repo
git pull origin main
docker compose --env-file fastapi/.env up fastapi -d --build
```

Or use the deploy script:
```bash
./scripts/deploy.sh
```

---

## Team

| Name              | Role                                |
|-------------------|-------------------------------------|
| Inaaya Rana       | Team Lead, Frontend                 |
| Carolyn Jiang     | Frontend                            |
| Andy Situ         | Backend                             |
| Isabella Castillo | Scrum Master, Backend, Data Science |
| Rodolfo Gonzalez  | Backend, Data Science               |
| Pamela Espinoza   | Data Science                        |
