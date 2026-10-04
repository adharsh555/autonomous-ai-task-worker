from dataclasses import dataclass
import os
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str = "gemini-3.5-flash-lite"
    max_agent_steps: int = 7
    max_output_tokens: int = 256
    approval_threshold: float = 5000.0


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing {name}. Add it to .env")
    return value


settings = Settings(
    gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
    gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite"),
    max_agent_steps=int(os.getenv("MAX_AGENT_STEPS", "7")),
    max_output_tokens=int(os.getenv("MAX_OUTPUT_TOKENS", "256")),
    approval_threshold=float(os.getenv("APPROVAL_THRESHOLD", "5000")),
)
