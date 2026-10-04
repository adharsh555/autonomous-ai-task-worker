# 90-second demo script

## 0:00–0:15 — Goal
Show the dashboard and say:

> “This is a narrow autonomous AI task worker for a simulated company billing system. I give it an outcome, not a sequence of clicks.”

## 0:15–0:40 — Normal execution
Run the Acme task.

Point at the trace:
- search invoice
- read source
- write billing record
- verify
- complete

Say:

> “Gemini selects the next tool from the state of the task. The application executes the side effect, returns the observation, and the loop continues. Completion is only reported after a separate verification call.”

## 0:40–1:05 — Failure recovery
Run the Globex task.

The first billing write intentionally returns a timeout.

Say:

> “This environment injects one deterministic timeout. The worker recognizes it as retryable, retries once, and then verifies the result instead of blindly claiming success.”

## 1:05–1:25 — Human approval
Run the Umbrella Labs task.

The UI pauses at approval.

Say:

> “High-value writes are policy-controlled. The model cannot bypass the application boundary. The worker pauses, asks for approval, and only then performs the mutation and verification.”

## 1:25–1:30 — Close
Say:

> “The important part is not the invoice domain. The reusable abstraction is the worker loop: understand the outcome, select a tool, execute, observe, recover, verify, and return evidence.”
