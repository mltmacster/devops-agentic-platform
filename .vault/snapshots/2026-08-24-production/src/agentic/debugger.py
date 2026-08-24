"""Debugger Agent — Traces errors and suggests fixes.

Analyzes stack traces, error messages, or code snippets to identify
the root cause and propose actionable fixes. Uses an LLM when
DAP_LLM_API_KEY is configured; otherwise falls back to pattern matching.
"""

import logging

from .llm import LLMClient, LLMError, get_llm_client
from .plugin_interface import BaseAgent
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DebuggerAgent(BaseAgent):
    """Debugger: Diagnoses errors and proposes fixes."""

    SYSTEM_PROMPT = (
        "You are the DAP Debugger agent. Analyze the user's error report "
        "(stack trace, message, or description) and return ONLY a JSON object "
        'with exactly these keys: {"error_type": string, "diagnosis": string, '
        '"root_cause": string, "fix_suggestion": string, "example": string} '
        "Rules: error_type is the canonical exception name if identifiable "
        '(e.g. "TypeError", "KeyError", "ModuleNotFoundError"), otherwise a human '
        'phrasing ("Key Error", "Runtime Error") or "Unknown Error". diagnosis is '
        "one sentence on what is wrong; root_cause is one sentence on the "
        "underlying cause; fix_suggestion is a concrete fix; example is a short "
        'quoted "wrong vs fixed" code snippet.'
    )

    @property
    def name(self) -> str:
        return "Debugger"

    # ─── LLM path ─────────────────────────

    async def execute_async(self, request_id: str, query: str) -> Dict[str, Any]:
        """Execute with the LLM when configured; fall back to heuristics."""
        llm = get_llm_client()
        if llm.is_configured:
            try:
                return await self._execute_with_llm(llm, request_id, query)
            except LLMError as exc:
                logger.warning("LLM path failed (%s); using heuristics", exc)

        result = self.execute(request_id, query)
        result["engine"] = "heuristic"
        return result

    async def _execute_with_llm(self, llm: LLMClient, request_id: str, query: str) -> Dict[str, Any]:
        data = await llm.complete_json(self.SYSTEM_PROMPT, query)
        for key in ("error_type", "diagnosis", "root_cause", "fix_suggestion"):
            value = data.get(key)
            if not isinstance(value, str) or not value.strip():
                raise LLMError(f"LLM result missing '{key}'")
        return {
            "error_type": data["error_type"],
            "diagnosis": data["diagnosis"],
            "root_cause": data["root_cause"],
            "fix_suggestion": data["fix_suggestion"],
            "example": str(data.get("example", "")),
            "engine": "llm",
        }

    # ─── Error classification rules ──────────────

    # (error_type, phrases) — case-insensitive substring match, first hit wins.
    # Canonical exception names first (traceback form), then human phrasing.
    # "Connection Error" precedes "Timeout Error" so "connection timed out"
    # classifies as a connection problem, not a timeout.
    ERROR_PATTERNS = [
        ("KeyError", ["keyerror", "missing key"]),
        ("ModuleNotFoundError", ["modulenotfounderror", "no module named"]),
        ("ImportError", ["importerror", "cannot import", "failed to import"]),
        ("ConnectionError", ["connectionerror", "connection refused", "connection reset"]),
        ("TimeoutError", ["timeouterror", "timeout exceeded"]),
        ("TypeError", ["typeerror", "wrong type"]),
        ("ValueError", ["valueerror", "invalid value"]),
        ("IndexError", ["indexerror", "index out of range"]),
        ("AttributeError", ["attributeerror", "no attribute"]),
        ("PermissionError", ["permissionerror", "permission denied", "access denied"]),
        ("FileNotFoundError", ["filenotfounderror", "no such file"]),
        ("RuntimeError", ["runtimeerror"]),
        ("Key Error", ["key error"]),
        ("Connection Error", ["connection error", "connection timed out", "network unreachable", "unreachable"]),
        ("Timeout Error", ["operation timed out", "timed out"]),
        ("File Not Found Error", ["file not found", "file missing"]),
        ("Runtime Error", ["runtime error"]),
    ]

    ERROR_FIXES = {
        "TypeError": {
            "root_cause": "A variable's actual type doesn't match what the function expects.",
            "fix": "Add explicit type conversion: str(var), int(var), or use type hints with validation.",
            "example": "# Wrong: func(5)\n# Fixed: func(int(5))",
        },
        "ValueError": {
            "root_cause": "A value is present but has an invalid format or range.",
            "fix": "Validate input before use. Add try/except with specific handler.",
            "example": "# Wrong: int('abc')\n# Fixed:\ntry:\n    val = int(x)\nexcept ValueError:",
        },
        "KeyError": {
            "root_cause": "The code is accessing a dict/list index that hasn't been initialized.",
            "fix": "Use .get(key, default) for dicts or check len/list membership first.",
            "example": "# Wrong: data['missing_key']\n# Fixed: data.get('key', default_value)",
        },
        "IndexError": {
            "root_cause": "List index is out of bounds (negative or >= len).",
            "fix": "Validate the index before access: if 0 <= i < len(lst):",
            "example": "# Wrong: lst[10] when len=5\n# Fixed: lst[min(9, idx)]",
        },
        "AttributeError": {
            "root_cause": "The object instance doesn't have the attribute being accessed.",
            "fix": "Check the class definition or verify you instantiated the object correctly.",
            "example": "# Wrong: obj.method()\n# Fixed: hasattr(obj, 'method') check first",
        },
        "ImportError": {
            "root_cause": "The package isn't installed or the import path is incorrect.",
            "fix": "Run `pip install <package>` and verify the import path matches your project structure.",
            "example": "# Wrong: from mylib import x\n# Fixed: pip install mylib",
        },
        "ModuleNotFoundError": {
            "root_cause": "The module isn't in the Python path or not installed.",
            "fix": "Add the project root to sys.path or install with pip.",
            "example": "# Wrong: import mymodule\n# Fixed: sys.path.insert(0, '/path/to/project')",
        },
        "ConnectionError": {
            "root_cause": "The target service is down, unreachable, or the connection was dropped.",
            "fix": "Verify network connectivity, check service health, and add retry logic with exponential backoff.",
            "example": "# Wrong: requests.get(url)\n# Fixed: tenacity.retry(requests.get)(url)",
        },
        "TimeoutError": {
            "root_cause": "The operation exceeded its timeout threshold.",
            "fix": "Increase the timeout value or implement circuit breaker pattern.",
            "example": "# Wrong: requests.get(url, timeout=1)\n# Fixed: requests.get(url, timeout=5)",
        },
        "PermissionError": {
            "root_cause": "The process lacks the required OS or file-level permissions.",
            "fix": "Run with appropriate privileges (sudo, elevated) or fix file/directory permissions.",
            "example": "# Wrong: open('/root/file.txt')\n# Fixed: os.chmod(path, 0o644)",
        },
        "FileNotFoundError": {
            "root_cause": "The file path doesn't exist or the directory was deleted.",
            "fix": "Verify the path exists before accessing: os.path.exists(path).",
            "example": "# Wrong: open('data.csv')\n# Fixed: if os.path.exists(path): open(path)",
        },
        "RuntimeError": {
            "root_cause": "A general error occurred during runtime (catch-all category).",
            "fix": "Add specific try/except handlers for the expected error types.",
            "example": "# Wrong: bare try/except\n# Fixed:\ntry:\n    risky_operation()\nexcept Exception as e:",
        },
    }

    # ─── Execute method (heuristic path) ───

    def execute(self, request_id: str, query: str) -> Dict[str, Any]:
        """Diagnose the error and suggest a fix using pattern matching."""

        error_type = self._classify_error(query)
        diagnosis = self._diagnose(error_type, query)

        return {
            "error_type": error_type,
            "diagnosis": diagnosis["summary"],
            "root_cause": diagnosis["root_cause"],
            "fix_suggestion": diagnosis["fix"],
            "example": diagnosis.get("example", ""),
        }

    # ─── Internal helpers ──────────────

    def _classify_error(self, query: str) -> str:
        """Classify the error from the user's description.

        Returns the spelling of the pattern that matched, so traceback-form
        input yields canonical names (e.g. "KeyError") while natural-language
        input yields human phrasing (e.g. "Key Error").
        """

        q = query.lower()
        for error_type, phrases in self.ERROR_PATTERNS:
            if any(phrase in q for phrase in phrases):
                return error_type

        if any(kw in q for kw in ["traceback", "stack", "exception"]):
            return "Traceback"

        return "Unknown Error"

    def _diagnose(self, error_type: str, query: str | None = None) -> Dict[str, str]:
        """Generate diagnosis and fix for a classified error."""

        for name, _ in self.ERROR_PATTERNS:
            if error_type == name:
                info = self.ERROR_FIXES.get(name) or self.ERROR_FIXES.get(name.replace(" ", ""))
                return {
                    "summary": f"Detected a {error_type}",
                    "root_cause": info["root_cause"],
                    "fix": info["fix"],
                    "example": info.get("example", ""),
                }

        return {
            "summary": f"Detected a {error_type} — needs further investigation",
            "root_cause": "The error occurred in an unhandled exception chain. Trace the stack to find where control was lost.",
            "fix": "Add try/except blocks around the failing code path. Use traceback.print_exc() to log full context.",
            "example": "# Wrong: bare try/except\n# Fixed:\ntry:\n    risky_operation()\nexcept Exception as e:",
        }