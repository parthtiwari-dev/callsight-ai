# callsight-ai
AI-powered sales call intelligence platform for automated transcription, diarization, quality scoring, issue detection, and coaching insights.

## Phase 1 Status

This repository currently implements the setup and pipeline spine:

- FastAPI app skeleton with `GET /health`
- SQLAlchemy schema for orgs, teams, advisors, calls, transcript segments, analyses, issue tags, contests, and processing events
- Source-agnostic ingestion interfaces with folder, generic webhook, and Exotel stub adapters
- Pipeline spine with mock transcript mode, `faster-whisper` transcription hook, pyannote diarization hook, overlap detection, and PII redaction
- CLI runner that works without OpenAI, Hugging Face, or audio model downloads when `--mock` is used
- Focused tests for quote grounding and ingestion idempotency

## Setup

```powershell
cd "C:\great learning self paced\interview assignments\callsight-ai"

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional local speech dependencies:

```powershell
pip install -r requirements-speech.txt
```

Copy `.env.example` to `.env` and fill credentials as needed. Phase 1 mock mode does not require `OPENAI_API_KEY` or `HUGGINGFACE_ACCESS_TOKEN`.

## Run Postgres

```powershell
docker compose up -d db
```

## Run API

```powershell
uvicorn app.main:app --reload
```

Then open:

- Health: `http://127.0.0.1:8000/health`
- Swagger: `http://127.0.0.1:8000/docs`

Expected health response:

```json
{"status":"ok","service":"callsight-ai"}
```

## Run Pipeline Spine

Mock mode, no speech dependencies:

```powershell
python scripts/run_pipeline_once.py --mock
```

Real audio mode, after installing `requirements-speech.txt` and setting `HUGGINGFACE_ACCESS_TOKEN`:

```powershell
python scripts/run_pipeline_once.py --audio-path sample_calls/demo.wav --metadata-path sample_calls/demo.metadata.json
```

## Test

```powershell
pytest
```

## Real vs. Mocked in Phase 1

Real:

- Project setup, pinned dependencies, Docker Postgres config
- SQLAlchemy data model and idempotency constraint
- FastAPI app shell and health route
- Source adapter abstraction
- Deterministic quote-grounding utility
- PII redaction and overlap detection helpers

Mocked or deferred:

- OpenAI call analysis, scoring, and coaching notes are Phase 2
- Streamlit dashboards are placeholders until stored analysis data exists
- Live telephony vendor integration is represented by interface-conformant adapters and an Exotel stub
- Speech model execution is wired but optional; use `--mock` until local model downloads and Hugging Face pyannote access are ready
