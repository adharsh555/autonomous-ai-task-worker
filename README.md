# Autonomous AI Task Worker

A narrow, working prototype for the CentrAlign AI Engineering Intern problem: an AI worker accepts a natural-language outcome, selects tools, executes against a simulated company billing application, observes results, recovers from a retryable failure, requests approval for a high-value action, verifies the outcome, and returns evidence.

## Why this architecture

The challenge explicitly allows a small simulated company application and says a narrow prototype that genuinely demonstrates autonomy is preferable to a broad mocked system. This project therefore keeps the environment deterministic and focuses engineering effort on the agent loop and reliability boundaries.

Core loop:

`Goal → Understand → Plan → Execute → Observe → Adapt → Verify → Complete`

### Components

- **FastAPI** — small HTTP/API layer and demo UI.
- **Gemini 3.5 Flash-Lite** — low-latency agent reasoning and tool selection.
- **Tool layer** — deterministic invoice search, invoice retrieval, billing write, and verification.
- **SQLite** — local simulated company data and actual billing writes.
- **Agent state** — per-run conversation history, trace, step budget, and approval state.
- **Safety boundary** — writes ≥ `$5,000` pause for human approval before mutation.

## Free-tier design

The default model is `gemini-3.5-flash-lite`. Keep the task prompts concise, cap model output at 256 tokens, and stop after 7 agent turns. Tool responses are intentionally compact. The worker performs no unnecessary LLM calls: one call selects the next action, then the deterministic tool result is returned to Gemini.

The model is configurable through `.env`, so the project does not hard-code a provider dependency into the rest of the application.

## Setup

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
cp .env.example .env
```

Put your Gemini API key in `.env`:

```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.5-flash-lite
MAX_AGENT_STEPS=7
MAX_OUTPUT_TOKENS=256
APPROVAL_THRESHOLD=5000
```

Run:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Open `http://127.0.0.1:8000`.

## Demo scenarios

### 1. Normal autonomous completion

```text
Find the latest invoice from Acme Corp, extract the amount and due date, enter it into our internal billing system, verify that it was saved, and tell me what happened.
```

Expected behavior: search → identify latest invoice → read source → write → verify → evidence.

### 2. Failure recovery

```text
Find the latest invoice from Globex, enter it into the billing system, verify it, and report the result.
```

The simulated billing system intentionally returns a timeout on the first Globex write. The worker detects the retryable result, retries once, then verifies the saved record.

### 3. Human approval

```text
Find the latest invoice from Umbrella Labs, enter it into the billing system, verify it, and report the result.
```

The invoice is `$7,200`, above the `$5,000` approval threshold. The write is not executed until the user approves it in the UI.

## Important implementation decisions

### Deterministic tools, model-driven decisions

Gemini decides which tool should run and what information is needed next. The application owns the actual side effects. This keeps business rules, approval, source-data validation, retries, and verification deterministic.

### Verification is a separate operation

A successful write response is not treated as proof of completion. The worker calls `verify_billing_record` and compares the stored values with the source invoice before reporting success.

### Bounded autonomy

The agent has a hard step limit. This prevents runaway loops and keeps free-tier usage predictable.

### No automatic function execution

The application manually handles function calls. This is intentional: approval and retry decisions must remain under application control rather than being delegated to automatic function execution.

## Limitations

- The company environment is simulated and local.
- Browser/computer-use is not included; the challenge explicitly permits a simulated application for a narrow prototype.
- Memory is per-run rather than persistent company memory.
- Retry policy is intentionally simple: one retry for a retryable tool result.
- There is no authentication or multi-user persistence.
- The demo data is fixed.

## Next steps with more time

1. Replace the SQLite simulator with connector interfaces for real APIs/browser tools.
2. Add durable run state and background execution.
3. Add policy-based permissions per tool and user.
4. Add structured evaluation datasets and success/recovery metrics.
5. Add persistent company memory with retrieval and provenance.
6. Add browser/computer-use execution behind the same tool interface.

## Submission checklist

- GitHub repository
- README and architecture
- Working demo video
- Normal completion demo
- Retry/recovery demo
- Approval demo
- Limitations and next steps
- Model/API/framework disclosure

Do not use real company credentials or unauthorized third-party access.
