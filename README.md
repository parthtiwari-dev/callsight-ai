# FitNova Callsight AI

AI-powered sales-call intelligence for FitNova: ingest calls, transcribe/diarize, score call quality, flag risky moments with quote evidence, support advisor contests, and surface insights through FastAPI and Streamlit dashboards.

## How It Works

```
Call Source (folder / webhook / Exotel stub)
        -> Ingestion (idempotency check on external_call_id)
        -> Non-sales pre-filter (short/irrelevant calls excluded, not analyzed)
        -> PII redaction (card / phone / OTP-like patterns masked)
        -> Transcription + diarization (advisor vs customer, timestamped)
        -> Analysis (single structured OpenAI call: scores + issue tags + coaching)
        -> Guardrails (quote-grounding verification, deterministic score caps)
        -> Postgres (org -> team -> advisor -> call -> transcript -> tags)
        -> FastAPI -> Streamlit dashboards (Sales Director / Team Leader / Advisor)
        -> Advisor contests a flag -> Team Leader resolves it -> stored back
```

Ingestion is adapter-based so a new telephony/CRM vendor is a new adapter, not a rewrite. The one paid API call in the whole pipeline is the analysis step; transcription/diarization run locally.

## What Works

- Source-agnostic ingestion skeleton with folder, webhook, and Exotel-stub adapters.
- Mock pipeline that runs without paid APIs or audio models.
- Optional real audio transcription/diarization hooks using `faster-whisper` and pyannote.
- Structured analysis schema with five rubric scores, overall score, issue tags, summary, and coaching notes.
- OpenAI real-analysis path, defaulting to `gpt-4o-mini`.
- Quote-grounding guardrails and deterministic compliance score cap.
- Postgres persistence for calls, transcripts, analyses, issue tags, contests, and processing events.
- FastAPI endpoints for calls, ingestion, org/team/advisor management, dashboards, and contest resolution.
- Streamlit call-processing page plus dashboards for Sales Director, Team Leader, Advisor, and Call Detail.
- Realistic seeded demo data.

## Supported Audio Formats

The folder ingestion adapter recognizes:

- `.wav`
- `.mp3`
- `.m4a`
- `.flac`
- `.ogg`

For the smoothest demo, use `.wav` or `.mp3`. Real audio mode also needs the speech dependencies and Hugging Face pyannote access.

## Scoring Rubric & Issue Taxonomy

**Rubric** — five dimensions, each scored 0-10, rolled up into a weighted overall score:

| Dimension | Weight |
|---|---|
| Needs discovery | 25% |
| Compliance | 25% |
| Objection handling | 20% |
| Product knowledge | 15% |
| Next-step booking | 15% |

Needs discovery and compliance carry the most weight because a mis-sold or misleading call is a worse outcome than a slightly weak pitch. The same weighted score rolls up to advisor, team, and org averages.

**Issue tags** — each carries a severity (low/medium/high/critical), a timestamp, the exact quoted line, a reason, and a confidence score:

- `no_needs_discovery`
- `over_promising` (e.g. guaranteed results)
- `pressure_or_urgency`
- `price_before_value`
- `undisclosed_costs`
- `weak_or_missing_trial_booking`
- `talking_over_customer`

A verified `over_promising` tag at `critical` severity automatically caps the compliance score at 3/10, regardless of what the model scored it — a deterministic rule, not something the LLM can talk itself out of.

## Edge Case Handling

| Case | Handling |
|---|---|
| Mono recording / poor diarization | Segments are matched to the best-overlapping speaker turn; if diarization confidence is low it's recorded on the call (`diarization_quality`) instead of silently trusted. |
| Hindi-English code-switching | Local `faster-whisper` transcription handles code-switched audio natively; no translation step that could lose meaning. |
| Non-sales calls (wrong number, internal) | A pre-filter checks call duration and sales-relevant keywords before spending an LLM call; excluded calls are stored with status `excluded_non_sales`, not analyzed. |
| PII in the call | Card-like numbers, phone numbers, and OTP/PIN codes are regex-redacted before the transcript is stored or sent to OpenAI. |
| Hallucinated / false-positive tags | Every tag's quoted line is fuzzy-matched against the real transcript; unverified tags are dropped and logged to `ProcessingEvent`, never shown to a reviewer. |
| Vendor/API failures | External calls (OpenAI, transcription) are wrapped in retry/backoff; a `(source_id, external_call_id)` unique constraint plus per-call status tracking means a failed or retried call is never double-processed. |

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

## Recommended Demo Flow

For the most reliable take-home walkthrough:

```powershell
docker compose up -d db
python scripts/seed_demo_data.py
streamlit run dashboard/Home.py
```

Then in Streamlit:

```text
Process Call -> Mock demo call -> Call Detail -> Advisor contest -> Team Leader resolve
```

The `Process Call` page runs the full loop against Postgres: ingestion, transcript generation, analysis, guardrails, persistence, and dashboard visibility. Mock mode is the recommended demo path because it is deterministic and does not require OpenAI, Hugging Face, or local audio model downloads.

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
- Process Call
- Sales Director
- Team Leader
- Advisor
- Call Detail

The UI has a light sky-blue theme and a pitch-black dark theme, selectable from the sidebar. See **Recommended Demo Flow** above for the step-by-step walkthrough.

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

Real audio is also available through the Streamlit `Process Call` page by uploading a supported audio file. If no sample audio is committed, place any short supported file at `sample_calls/demo.wav` or upload it through Streamlit.

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
- Full SSO/RBAC is intentionally out of scope; contest/admin actions are demo-level.
- Notifications are out of scope.
- Real speech execution depends on local model downloads and Hugging Face access.

## Test

```powershell
pytest -q
```

## Design Decisions

- **PostgreSQL over a document store.** The data is inherently relational — org → team → advisor, call → transcript segments → scores → tags — and dashboards need real aggregate queries (team averages, org rollups) that relational joins handle cleanly and a document store makes awkward.
- **Adapter pattern for ingestion.** FitNova may switch telephony or CRM vendors, or run several at once. Every source (folder, webhook, Exotel stub) normalizes into one shape before anything downstream runs, so adding a new vendor is a new adapter, not a rewrite.
- **Quote-grounding guardrails.** An LLM can claim a flag is backed by a line the advisor never said. Every issue tag is fuzzy-matched against the actual transcript before it's trusted; unverified tags are logged and discarded rather than silently kept. A false flag is worse than a missed one — it unfairly penalizes an advisor and erodes trust in the whole system.
- **`gpt-4o-mini` as the default model.** Cost-effective for structured scoring at call volume; the model is swappable via `OPENAI_MODEL` for higher-stakes or final scoring runs.
- **Contest resolution stays human.** An advisor can contest a flag, but a Team Leader resolves it — deliberately not a second LLM call. Adjudicating a dispute about the model's own judgment is a human decision, not one to automate.
- **Idempotent processing.** A unique constraint on `(source_id, external_call_id)` plus a `ProcessingEvent` log means a call is never double-processed, and every retry or rejection is auditable instead of silent.
- **Synchronous processing, by design, for now.** At FitNova's current scale this keeps the system simple to run and reason about; the natural next step at higher call volume is moving ingestion-to-analysis onto a background worker queue.
