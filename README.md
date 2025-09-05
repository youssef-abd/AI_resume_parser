# AI Resume Screener — From A to Z

This repository contains an end-to-end, free/open-source implementation of an AI-powered Resume Screener. It parses resumes (PDF/DOCX), extracts skills, embeds text, stores everything in PostgreSQL with pgvector, serves a FastAPI backend, and includes a Streamlit UI with highlighting of matched skill spans.


## Table of Contents
- [Project Goals](#project-goals)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Chronology of What We Built](#chronology-of-what-we-built)
- [Backend API](#backend-api)
- [Database Schema](#database-schema)
- [Skill Registry](#skill-registry)
- [Matching & Scoring](#matching--scoring)
- [Local Development](#local-development)
- [Environment Configuration (.env)](#environment-configuration-env)
- [Database (Docker + pgvector + Alembic)](#database-docker--pgvector--alembic)
- [Streamlit UI](#streamlit-ui)
- [Troubleshooting](#troubleshooting)
- [Next Steps](#next-steps)
- [License](#license)


## Project Goals
- Parse resumes (PDF/DOCX) and job descriptions; clean noisy formatting.
- Extract technical skills using NLP, driven by a dynamic skills registry.
- Generate sentence embeddings and compute semantic similarity.
- Store raw/cleaned text, skills, and embeddings in Postgres using pgvector.
- Serve a FastAPI API with endpoints for uploads and matching.
- Provide an optional Streamlit UI for demoing uploads/matches and highlighting matched skill spans.


## Architecture
- Parser layer: pdfplumber (PDF), python-docx (DOCX) + cleaning pipeline to strip markdown/bullets.
- NLP layer:
  - spaCy (PhraseMatcher) + skill registry (JSON) for skills extraction
  - regex fallback for extra coverage
- Embeddings: sentence-transformers (all-MiniLM-L6-v2, 384-dim) with normalized vectors.
- Storage: PostgreSQL + pgvector for vector similarity; SQLAlchemy models; Alembic migrations.
- Backend: FastAPI; endpoints for uploads (single and batch), matching, resume retrieval, health/readiness.
- UI: Streamlit to upload jobs/resumes, run matches, and visualize matched spans.


## Tech Stack
- Language: Python 3.10+
- Backend: FastAPI, Pydantic
- NLP: spaCy, PhraseMatcher; sentence-transformers
- Parsing: pdfplumber, python-docx (optional OCR deferred)
- Database: PostgreSQL + pgvector
- ORM/Migrations: SQLAlchemy 2.x, Alembic
- UI: Streamlit
- Infra: Docker Compose (Postgres + Adminer)
- Config: pydantic-settings (.env)

All tools are free/open-source.


## Chronology of What We Built
1) Initial scaffolding
- Created a minimal FastAPI app with health endpoints and stub upload/match endpoints.

2) Parsing & cleaning
- Implemented parsing for PDF (pdfplumber) and DOCX (python-docx).
- Added a cleaning pipeline to normalize Unicode/newlines and strip markdown/bullets/numbering.
- Saved development artifacts to `data/parsed/<resume_id>.json` (raw/cleaned text + meta).

3) Basic skills extraction & TF-IDF (interim)
- Added a simple regex-based skill extractor (proof of concept).
- Used TF-IDF cosine to score resume/job similarity (later replaced by embeddings).

4) Upgraded to sentence-transformers + spaCy
- Loaded `all-MiniLM-L6-v2` for robust embeddings.
- Added spaCy PhraseMatcher-based extraction for better precision/recall.
- Introduced a combined score: 0.7 * cosine + 0.3 * Jaccard(skill overlap).

5) Database integration (Postgres + pgvector)
- Docker Compose spin-up of Postgres (pgvector-enabled) + Adminer UI.
- SQLAlchemy models: `resumes`, `jobs`; embedded vectors stored with pgvector type.
- Vector search in SQL using `<=>` (cosine distance); converted to similarity 1 - distance.
- Replaced in-memory stores with DB persistence.

6) Readiness & limits
- Added `/readyz` endpoint to verify model load and DB connectivity.
- Enforced max upload size (configurable via `.env`).

7) Skill registry + matched spans
- Created `app/skills_registry.json` listing canonical skills + aliases; loaded dynamically.
- Extended match responses with `matched_spans` [{skill, text, start, end}] for explanations.

8) Batch uploads & resume retrieval
- Added `POST /upload_resumes` for multi-file upload.
- Added `GET /resumes/{resume_id}` to fetch cleaned_text and skills for UI highlighting.

9) Streamlit UI
- Initial UI to upload job/resume and run matches.
- Updated UI to support multi-file upload and to highlight matched skill spans using `<mark>`.

10) Migrations and settings
- Introduced Alembic; env configured to read DB URL from `.env` via pydantic-settings.
- Removed runtime table creation; schema managed via migrations.


## Backend API
Base URL (default): `http://127.0.0.1:8000`
- GET `/healthz` → simple health status
- GET `/readyz` → status + model_loaded + db_ok
- POST `/upload_job` (JSON)
  - `{ title, description, required_skills? }` → embed + persist → `{ job_id, ... }`
- POST `/upload_job_form` (multipart/form-data)
  - `title`, `description`, `required_skills` (comma/newline separated)
- POST `/upload_resume` (multipart/form-data)
  - `file` (.pdf/.docx), `candidate_name?` → parse/clean/extract/embed + persist
- POST `/upload_resumes` (multipart/form-data)
  - `files` (multiple .pdf/.docx), `candidate_names?` (multi-values aligned by index)
  - per-file responses with notes and lengths
- GET `/resumes/{resume_id}` → `{ resume_id, candidate_name, cleaned_text, skills }`
- GET `/match?job_id=...&k=20`
  - Vector search (pgvector) + skills overlap + composite score; includes `matched_spans` for explanations

All endpoints documented at `/docs` (Swagger UI) and `/openapi.json`.


## Database Schema
Table: `jobs`
- id (UUID, PK)
- title (TEXT)
- description_cleaned (TEXT)
- required_skills (JSONB, list[str])
- embedding (VECTOR(384))
- created_at, updated_at (timestamptz)

Table: `resumes`
- id (UUID, PK)
- candidate_name (TEXT)
- raw_text (TEXT)
- cleaned_text (TEXT)
- skills (JSONB, list[str])
- embedding (VECTOR(384))
- created_at, updated_at (timestamptz)

Indexes: Start with exact search. When dataset grows (≥1k):
```sql
CREATE INDEX IF NOT EXISTS resumes_embedding_ivfflat
ON resumes USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
ANALYZE resumes;
```


## Skill Registry
Path: `app/skills_registry.json`
- JSON with `skills: [{ name, aliases[] }]`.
- Loaded at app startup; builds spaCy PhraseMatcher + alias mapping.
- Add new skills or aliases by editing JSON; restart the API.

Example snippet:
```json
{
  "skills": [
    { "name": "python", "aliases": ["py"] },
    { "name": "kubernetes", "aliases": ["k8s", "eks", "gke"] }
  ]
}
```


## Matching & Scoring
- Embeddings: sentence-transformers (`all-MiniLM-L6-v2`, 384-d). Normalized vectors.
- Vector similarity: cosine via pgvector `<=>` (distance); similarity = 1 - distance.
- Skills overlap: Jaccard between job’s required skills and resume skills.
- Composite score: `0.7 * cosine + 0.3 * Jaccard`. Tunable.
- Explanations: `matched_spans` in `/match` contain `{ skill, text, start, end }` occurrences from resume text.


## Local Development
### Prerequisites
- Python 3.10+
- Docker Desktop (WSL2 backend on Windows)

### Setup
```powershell
# Create venv
py -3 -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip

# Install backend deps
.venv\Scripts\python -m pip install fastapi "uvicorn[standard]" python-multipart \
    pdfplumber python-docx spacy sentence-transformers numpy scikit-learn \
    sqlalchemy psycopg[binary] alembic pydantic-settings pgvector requests

# Download spaCy model
.venv\Scripts\python -m spacy download en_core_web_sm
```

### Start the database stack
```powershell
docker compose up -d
```
- Adminer: http://127.0.0.1:8080 (System: PostgreSQL, Server: db, User: postgres, Password: postgres, DB: resumes)

### Configure environment
- `.env` (already added):
```
DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5432/resumes
DEBUG=false
MODEL_NAME=all-MiniLM-L6-v2
MAX_UPLOAD_MB=10
```

### Run migrations
```powershell
.venv\Scripts\python -m alembic revision --autogenerate -m "init schema"
# Edit migration to ensure: op.execute("CREATE EXTENSION IF NOT EXISTS vector") in upgrade()
.venv\Scripts\python -m alembic upgrade head
```

### Start the API
```powershell
.venv\Scripts\python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- Swagger: http://127.0.0.1:8000/docs
- Readiness: http://127.0.0.1:8000/readyz


## Environment Configuration (.env)
- Managed via `pydantic-settings` (see `app/settings.py`).
- The API reads `.env` automatically; Alembic also reads `.env` via `migrations/env.py` if `DATABASE_URL` isn’t set in shell.


## Database (Docker + pgvector + Alembic)
- Docker Compose uses image `ankane/pgvector:latest` for Postgres with pgvector.
- Alembic controls schema. Runtime DDL (create_all) is disabled.
- For large datasets, add ivfflat index for `resumes.embedding`.


## Streamlit UI
Path: `ui/streamlit_app.py`
- Settings: `API_BASE_URL` (defaults to http://127.0.0.1:8000)
- Tabs:
  - Upload Job: paste markdown/plaintext; optional required skills
  - Upload Resumes: multi-file upload; optional candidate names list
  - Match Results: top-k table + per-candidate metrics and matched span highlighting

Run Streamlit:
```powershell
.venv\Scripts\python -m pip install streamlit requests
.venv\Scripts\python -m streamlit run ui/streamlit_app.py
```


## Troubleshooting
- Connection refused from UI:
  - Ensure API is running; sidebar API Base URL set correctly; try `/readyz`.
- 500 errors on match:
  - Ensure resumes/jobs exist in DB; check DB is reachable; ensure pgvector extension enabled.
- Alembic connection timeout:
  - DB not running or wrong URL; check `docker compose ps`, Adminer access, `.env`.
- File too large (413):
  - Increase `MAX_UPLOAD_MB` in `.env` and restart API.


## Next Steps
- Migrations: add initial revision if not yet applied; remove any legacy DDL.
- ANN Indexing: add ivfflat for scale.
- Skill registry expansion: grow coverage; add categories (must-have vs. nice-to-have).
- Scoring tunables: expose weights in `.env` or settings.
- CRUD endpoints: list/get/delete jobs/resumes; pagination.
- Background processing: Celery + Redis for OCR or batch.
- Deployment: Dockerfile + Render/Railway (API), HuggingFace Spaces (UI). Configure CORS.


## License
- This project uses only free/open-source tools and libraries. Please refer to individual libraries for their licenses.
