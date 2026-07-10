# FitNova Callsight AI

AI-powered sales-call intelligence for FitNova: ingest calls, transcribe/diarize, score call quality, flag risky moments with quote evidence, support advisor contests, and surface insights through FastAPI and Streamlit dashboards.

## What Works

- Source-agnostic ingestion skeleton with folder, webhook, and Exotel-stub adapters.
- Mock pipeline that runs without paid APIs or audio models.
- Optional real audio transcription/diarization hooks using `faster-whisper` and pyannote.
- Structured analysis schema with five rubric scores, overall score, issue tags, summary, and coaching notes.
- OpenAI real-analysis path, defaulting to `gpt-4o-mini`.
- Quote-grounding guardrails and deterministic compliance score cap.
- Postgres persistence for calls, transcripts, analyses, issue tags, contests, and processing events.
- FastAPI endpoints for calls, ingestion, org/team/advisor management, dashboards, and contest resolution.
- Streamlit dashboards for Sales Director, Team Leader, Advisor, and Call Detail.
- Realistic seeded demo data.

## Supported Audio Formats

The folder ingestion adapter recognizes:

- `.wav`
- `.mp3`
- `.m4a`
- `.flac`
- `.ogg`

For the smoothest demo, use `.wav` or `.mp3`. Real audio mode also needs the speech dependencies and Hugging Face pyannote access.

## Setup

```powershell
cd "C:\great learning self paced\interview assignments\callsight-ai"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Optional real speech stack:

```powershell
pip install -r requirements-speech.txt
```

Create `.env` from `.env.example`:

```env
DATABASE_URL=postgresql+psycopg://callsight:callsight@localhost:5432/callsight
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
HUGGINGFACE_ACCESS_TOKEN=
WHISPER_MODEL_SIZE=base
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8
DIARIZATION_MODEL=pyannote/speaker-diarization-community-1
USE_MOCK_TRANSCRIPT=true
```

## Run Database

```powershell
docker compose up -d db
```

## Seed Demo Data

```powershell
python scripts/seed_demo_data.py
```

This creates FitNova, three teams, eight advisors, sixteen scored calls, varied issue tags, and contests in pending/upheld/dismissed states.

## Run FastAPI

```powershell
uvicorn app.main:app --reload
```

Open:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

Swagger demo flow:

1. `POST /webhooks/ingest/generic_webhook`
2. `GET /calls`
3. `GET /calls/{call_id}`
4. `GET /calls/{call_id}/analysis`
5. `POST /calls/{call_id}/tags/{tag_id}/contest`
6. `POST /admin/tags/{tag_id}/resolve`
7. `GET /dashboards/org-summary`

## Run Streamlit

```powershell
streamlit run dashboard/Home.py
```

Pages:

- Home
- Sales Director
- Team Leader
- Advisor
- Call Detail

The UI has a light sky-blue theme and a pitch-black dark theme, selectable from the sidebar.

## Mock Pipeline Demo

```powershell
python scripts/run_pipeline_once.py --mock --analyze --mock-analysis --persist
```

This runs the full reliable demo loop:

```text
mock transcript -> mock structured analysis -> guardrails -> Postgres persistence
```

Rerun the command and `"created": false` confirms idempotency.

## Real Audio Pipeline

Install speech dependencies:

```powershell
pip install -r requirements-speech.txt
```

Set:

```env
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o-mini
HUGGINGFACE_ACCESS_TOKEN=your_hf_token
```

Run:

```powershell
python scripts/run_pipeline_once.py --audio-path sample_calls/demo.wav --metadata-path sample_calls/demo.metadata.json --analyze --persist
```

Real audio is supported by the code path, but the reliable graded demo path is mock/seeded data unless local model setup is already working.

## Real vs Mocked

Real:

- SQLAlchemy/Postgres schema
- FastAPI data APIs
- Streamlit dashboards
- Structured scoring schema
- Guardrails and quote verification
- Contest workflow
- Idempotent persistence
- Mock and real audio pipeline entrypoints

Mocked or scoped:

- Live telephony/CRM vendor integration is represented through source adapters.
- Full SSO/RBAC is simplified to demo-level request/header fields.
- Notifications are out of scope.
- Real speech execution depends on local model downloads and Hugging Face access.

## Test

```powershell
pytest -q
```

## Interview Talking Points

- Postgres fits because the data is relational: orgs, teams, advisors, calls, transcripts, tags, contests.
- The adapter pattern prevents telephony vendor lock-in.
- Quote grounding is necessary because false flags can unfairly penalize advisors.
- `gpt-4o-mini` is the default model because it is cost-effective for structured scoring.
- Contest resolution is human-driven by design; no second LLM is used to judge disputes.
- At larger scale, synchronous processing would move to a background worker queue.
