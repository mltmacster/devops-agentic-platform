"""LLM Client — OpenAI-compatible chat completions for the agentic engine.

Enabling a real LLM is opt-in via environment variables:

  DAP_LLM_API_KEY     API key (required — without it, agents use heuristics)
  DAP_LLM_BASE_URL    Base URL, default https://api.openai.com/v1
  DAP_LLM_MODEL       Model name, default gpt-4o-mini
  DAP_LLM_TIMEOUT     Request timeout in seconds, default 60
  DAP_LLM_MAX_TOKENS  Max completion tokens, default 4096

Any workhorse OpenAI-compatible endpoint works (OpenAI, Azure, Ollama,
vLLM, LiteLLM) by pointing DAP_LLM_BASE_URL at it. When unconfigured or
on any request/parse failure, agents transparently fall back to their
built-in heuristic logic, so the platform runs with zero external deps.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Raised when an LLM request fails or returns unusable output."""


@dataclass
class LLMConfig:
    """LLM client configuration (sourced from environment)."""

    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    timeout_seconds: float = 60.0
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            api_key=os.environ.get("DAP_LLM_API_KEY", "").strip(),
            base_url=os.environ.get("DAP_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
            model=os.environ.get("DAP_LLM_MODEL", "gpt-4o-mini"),
            timeout_seconds=float(os.environ.get("DAP_LLM_TIMEOUT", "60") or 60),
            max_tokens=int(os.environ.get("DAP_LLM_MAX_TOKENS", "4096") or 4096),
        )


class LLMClient:
    """Minimal OpenAI-compatible chat client with JSON-first helpers."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig.from_env()

    @property
    def is_configured(self) -> bool:
        """True when an API key is present (LLM mode enabled)."""
        return bool(self.config.api_key)

    async def complete(self, system: str, user: str, json_mode: bool = False) -> str:
        """Single chat completion. Returns the assistant message text."""
        if not self.is_configured:
            raise LLMError("LLM not configured (set DAP_LLM_API_KEY)")

        payload: dict = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": 0.2,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                resp = await client.post(
                    f"{self.config.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {exc}") from exc

        if resp.status_code != 200:
            raise LLMError(f"LLM returned HTTP {resp.status_code}: {resp.text[:300]}")

        try:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
        except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"Unexpected LLM response shape: {exc}") from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMError("LLM returned empty content")
        return content

    async def complete_json(self, system: str, user: str) -> dict:
        """Chat completion whose output must parse as a JSON object."""
        content = (await self.complete(system, user, json_mode=True)).strip()

        # Tolerate markdown code fences some models add despite json mode
        if content.startswith("```"):
            lines = content.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines).strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {content[:300]}") from exc

        if not isinstance(parsed, dict):
            raise LLMError("LLM JSON was not an object")
        return parsed


def get_llm_client() -> LLMClient:
    """Fresh client per call so env changes (tests, restarts) take effect."""
    return LLMClient()


def run_blocking(fn):
    """Run a blocking callable safely from sync or async contexts.

    Inline when no event loop is running; in a worker thread when called
    from inside a running loop (so the event loop is never blocked).
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return fn()
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(fn).result()
