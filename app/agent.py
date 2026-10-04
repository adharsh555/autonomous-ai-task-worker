from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from google import genai
from google.genai import types

from .config import settings
from .tools import execute

SYSTEM_PROMPT = """You are a reliable autonomous task worker for a simulated company billing system.
Complete the user's outcome, not just the conversation.
Use tools to discover facts and perform actions. After every action, inspect the result and choose the next action.
Never invent invoice data. Retry a retryable failure once. Verify a billing write before claiming success.
For high-value writes, the application will pause for human approval; do not try to bypass it.
Keep final responses concise and evidence-based.
"""

TOOL_DEFS = [
    types.FunctionDeclaration(
        name="search_invoices",
        description="Find invoices for a vendor. Use this when the user asks for an invoice but does not provide its ID.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"vendor": types.Schema(type="STRING")},
            required=["vendor"],
        ),
    ),
    types.FunctionDeclaration(
        name="get_invoice",
        description="Read the complete source invoice by invoice ID.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"invoice_id": types.Schema(type="STRING")},
            required=["invoice_id"],
        ),
    ),
    types.FunctionDeclaration(
        name="write_billing_record",
        description="Enter verified invoice amount and due date into the simulated billing system.",
        parameters=types.Schema(
            type="OBJECT",
            properties={
                "invoice_id": types.Schema(type="STRING"),
                "amount": types.Schema(type="NUMBER"),
                "due_date": types.Schema(type="STRING"),
            },
            required=["invoice_id", "amount", "due_date"],
        ),
    ),
    types.FunctionDeclaration(
        name="verify_billing_record",
        description="Check whether the billing record exists and exactly matches the source invoice.",
        parameters=types.Schema(
            type="OBJECT",
            properties={"invoice_id": types.Schema(type="STRING")},
            required=["invoice_id"],
        ),
    ),
]

CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=[types.Tool(function_declarations=TOOL_DEFS)],
    max_output_tokens=settings.max_output_tokens,
)


@dataclass
class Run:
    id: str
    task: str
    history: list[types.Content] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    status: str = "running"
    final: str = ""
    pending_approval: dict[str, Any] | None = None
    steps: int = 0


class Agent:
    def __init__(self) -> None:
        if not settings.gemini_api_key:
            raise RuntimeError("GEMINI_API_KEY is missing. Add it to .env")
        self.client = genai.Client(api_key=settings.gemini_api_key)

    def start(self, task: str) -> Run:
        run = Run(id=uuid4().hex, task=task.strip())
        run.history.append(types.Content(role="user", parts=[types.Part.from_text(text=run.task)]))
        return self._loop(run)

    def approve(self, run: Run, approved: bool) -> Run:
        pending = run.pending_approval
        if not pending:
            run.status = "failed"
            run.final = "There is no pending approval."
            return run
        run.pending_approval = None
        if not approved:
            run.status = "completed"
            run.final = "I stopped before the billing write because approval was denied."
            run.trace.append({"event": "approval", "decision": "denied"})
            return run

        run.trace.append({"event": "approval", "decision": "approved", "tool": pending["tool"], "arguments": pending["args"]})
        result = execute(pending["tool"], pending["args"], approved=True)
        run.trace.append({"event": "tool_result", "tool": pending["tool"], "result": result})
        run.history.append(
            types.Content(
                role="user",
                parts=[types.Part.from_function_response(name=pending["tool"], response=result)],
            )
        )
        run.status = "running"
        return self._loop(run)

    def _loop(self, run: Run) -> Run:
        while run.steps < settings.max_agent_steps:
            run.steps += 1
            try:
                response = self.client.models.generate_content(
                    model=settings.gemini_model,
                    contents=run.history,
                    config=CONFIG,
                )
            except Exception as exc:
                run.status = "failed"
                run.final = "The AI service failed while processing the task."
                run.trace.append({"event": "error", "type": type(exc).__name__, "message": str(exc)})
                return run

            if not response.candidates:
                run.status = "failed"
                run.final = "Gemini returned no response candidate."
                return run

            model_content = response.candidates[0].content
            run.history.append(model_content)

            calls = [p.function_call for p in (model_content.parts or []) if p.function_call]
            if not calls:
                run.status = "completed"
                run.final = (response.text or "Task completed.").strip()
                run.trace.append({"event": "complete", "message": run.final})
                return run

            # Keep execution serial: one tool result goes back to the model at a time.
            call = calls[0]
            name = call.name
            args = dict(call.args or {})
            run.trace.append({"event": "tool_call", "tool": name, "arguments": args})

            if name == "write_billing_record" and float(args.get("amount", 0)) >= settings.approval_threshold:
                run.pending_approval = {"tool": name, "args": args, "call_id": call.id}
                run.status = "waiting_for_approval"
                run.trace.append({"event": "approval_required", "amount": float(args.get("amount", 0)), "threshold": settings.approval_threshold})
                return run

            result = execute(name, args)
            run.trace.append({"event": "tool_result", "tool": name, "result": result})

            # The demo intentionally injects one recoverable timeout for Globex.
            if result.get("retryable"):
                run.trace.append({"event": "retry", "tool": name, "reason": result.get("error")})
                result = execute(name, args)
                run.trace.append({"event": "tool_result", "tool": name, "retry": True, "result": result})

            # generateContent expects function results in a user content turn.
            run.history.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_function_response(name=name, response=result)],
                )
            )

        run.status = "failed"
        run.final = "The worker stopped after reaching its safety step limit."
        run.trace.append({"event": "step_limit", "max_steps": settings.max_agent_steps})
        return run
