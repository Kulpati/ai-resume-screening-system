# AI Resume Screening & Candidate Ranking System

Upload resumes, paste a job description, get every candidate **scored, ranked, and explained** — plus a structured candidate profile, an ML category prediction, an ATS readability score, and interview questions per candidate. Built with FastAPI + PostgreSQL. **No paid API key. Everything runs offline.**

**Live demo:** _deployment link added after deploy_
**Frontend:** open `/app` on the running server — a one-page UI served by FastAPI itself (register/login, create job, upload, ranking, candidate detail). API docs at `/docs`.

## The AI / ML (honest, explainable version)

| Piece | What it is | What it does |
|---|---|---|
| **ML Model 1 — Scoring** | TF-IDF + cosine similarity, pure Python in `app/scoring.py` (no sklearn) | JD and each resume become weighted word vectors → 0–100 match score, plus matched / missing JD keywords |
| **ML Model 2 — Category classifier** | Multinomial Naive Bayes, pure Python in `app/ml_classifier.py` (no sklearn) | Predicts BACKEND / DATA / FRONTEND / DEVOPS + confidence %. Bayes theorem, Laplace smoothing, log-probabilities, softmax |
| **Structured parsing** | Regex + skill dictionary in `app/parsing.py` | Name, email, phone, skills, education, experience years from raw resume text |
| **ATS readability** | Fixed rules, 100 points, in `app/ats.py` | Is the resume itself complete and machine-readable (contact, sections, length, metrics) + improvement tips |
| **Insight layer** | Rule + template generation in `app/insight.py` | Strengths with evidence, skill gaps, 5–7 interview questions, verdict from fixed score bands |

This is **not** deep learning and not an LLM — and that is the point: every number can be explained word by word in an interview.

### How TF-IDF scoring works, in plain words
1. Lowercase everything, remove common words ("the", "and", "experience"...).
2. **TF** = how often a word appears in a document. **IDF** = how rare that word is across all documents — rare, specific words like `postgresql` count more.
3. JD and resume each become a list of TF-IDF numbers (a vector).
4. **Cosine similarity** between the two vectors × 100 = the score.
5. JD words present in the resume = **matched keywords**; absent = **missing keywords**.

### Verdict bands (fixed, explainable)
`>= 70` Strong match — shortlist · `45–69` Can interview — probe the gaps · `< 45` Weak match — likely reject

## Features
- JWT auth (PBKDF2-hashed passwords) + per-user data isolation
- **Email OTP verification** (`/auth/send-otp`, `/auth/verify-otp`) — 6-digit code, only its hash stored, 5-min expiry, max 3 attempts, SMTP sending, `OTP_ENABLED` off-switch so the demo never blocks
- Resume upload (.txt/.pdf) with status flow UPLOADED → PROCESSING → COMPLETED/FAILED, **2 MB size cap + file validation**
- Screening + ranking per job, candidate profile endpoint (parsing + ML category + ATS in one call)
- **Duplicate resume detection** (SHA-256 of cleaned text)
- **Dashboard stats** — totals, average score, verdict counts, ML category distribution
- One-page frontend at `/app`

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
# Frontend: http://127.0.0.1:8000/app   Docs: http://127.0.0.1:8000/docs
```

No Docker needed for the demo: without `DATABASE_URL` it uses a local SQLite file (`app.db`). For PostgreSQL: `docker compose up --build` (API on :8000, Postgres on :5432).

## Demo (using `samples/`)

```bash
python -m pytest -q        # 16 tests, full flow tested end-to-end
python demo.py --offline   # boots a throwaway DB and runs the sample demo
```
Expected demo ranking: **Strong 96.58 · Medium 65.34 · Weak 27.38**

## Endpoints

| Method | Path | Auth | What |
|---|---|---|---|
| GET | `/health` | – | Health check |
| GET | `/app` | – | One-page frontend |
| POST | `/auth/register` | – | Create user (password PBKDF2-hashed) |
| POST | `/auth/login` | – | Get JWT access token |
| GET | `/auth/me` | ✓ | Current user |
| POST | `/auth/send-otp` | – | Email a 6-digit OTP (when `OTP_ENABLED=true`) |
| POST | `/auth/verify-otp` | – | Verify an OTP (hash check, expiry, attempt limit) |
| POST | `/jobs` | ✓ | Create job (title + JD text) |
| GET | `/jobs` / `/jobs/{id}` | ✓ | List / get your jobs |
| POST | `/resumes/upload` | ✓ | Upload `.txt`/`.pdf` (max 2 MB); text extracted (pypdf for PDF) and stored |
| GET | `/resumes` / `/resumes/{id}` | ✓ | List / get your resumes |
| GET | `/resumes/duplicates` | ✓ | Duplicate resume groups |
| GET | `/resumes/{id}/profile` | ✓ | Structured profile + ML category + ATS score |
| POST | `/jobs/{id}/screen` | ✓ | Score all your COMPLETED resumes for this job |
| GET | `/jobs/{id}/ranking` | ✓ | Candidates ranked by score, descending |
| GET | `/jobs/{id}/candidates/{resume_id}/ai-insight` | ✓ | Strengths, gaps, interview questions, verdict |
| GET | `/stats/dashboard` | ✓ | Totals, average score, verdict + category counts |

## Project structure
```
ai-resume-screening-system/
├── app/
│   ├── main.py            # app entry, routes registration, /app frontend route
│   ├── config.py          # env settings (DB, JWT, OTP, SMTP)
│   ├── database.py        # SQLAlchemy engine + session
│   ├── models.py          # User, Job, Resume, ScreeningResult, EmailOTP
│   ├── schemas.py         # Pydantic request/response models
│   ├── auth.py            # PBKDF2 password hashing + JWT
│   ├── scoring.py         # ML Model 1: TF-IDF + cosine similarity
│   ├── ml_classifier.py   # ML Model 2: Multinomial Naive Bayes classifier
│   ├── parsing.py         # structured profile extraction (regex + dictionary)
│   ├── ats.py             # ATS readability score (fixed rules, 100 pts)
│   ├── insight.py         # strengths, gaps, interview questions, verdict
│   ├── extract.py         # .txt / .pdf text extraction
│   ├── otp.py             # OTP generate / hash / SMTP send
│   ├── routers/           # users (auth+OTP), jobs, resumes, stats
│   └── static/index.html  # one-page frontend served by FastAPI
├── tests/                 # 16 pytest tests (API, ML, OTP, validation, frontend)
├── samples/               # sample JD + strong/medium/weak resumes
├── demo.py                # one-command demo (python demo.py --offline)
├── requirements.txt
├── Dockerfile
└── docker-compose.yml     # API + PostgreSQL
```

## Tech
FastAPI · SQLAlchemy · PostgreSQL (SQLite fallback for demo/tests) · PyJWT · pypdf · Docker · pytest. ML: pure Python — `math`, `re`, `collections`, `hashlib`, `secrets` only.

## Tests
`python -m pytest -q` — **16 tests**: full ranking flow, 401 on protected routes, AI insight structure + verdict band, ML classifier (categories, empty → UNKNOWN), structured parsing fields, ATS score + tips, profile endpoint, duplicate detection, dashboard, OTP (disabled-by-default + full flow), upload validation (wrong type 400, oversized → FAILED), frontend page served.

## Author
**Kulpati Kumawat** — Backend developer (Python, FastAPI, PostgreSQL). Built and tested end-to-end; every score in this project can be explained from the code.
