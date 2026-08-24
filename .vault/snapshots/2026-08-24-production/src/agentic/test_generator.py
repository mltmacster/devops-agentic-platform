"""Test Generator Agent — Writes unit and integration tests.

Analyzes source code or specs to generate pytest-style test fixtures,
mocks, and assertions that cover happy paths and edge cases. Uses an
LLM when DAP_LLM_API_KEY is configured; otherwise falls back to
template-based case generation.
"""

import logging
import re

from .llm import LLMClient, LLMError, get_llm_client
from .plugin_interface import BaseAgent
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TestGeneratorAgent(BaseAgent):
    """Test Generator: Produces unit and integration tests from specs/code."""

    SYSTEM_PROMPT = (
        "You are the DAP Test Generator agent. From the user's specification, "
        "generate test cases. Return ONLY a JSON object with exactly these "
        'keys: {"test_type": string, "unit_tests": array, "integration_tests": array} '
        'Rules: test_type is one of "Unit", "Integration", or "Unit + Integration". '
        "unit_tests and integration_tests are arrays (each 1-10) of objects "
        '{"name": string, "description": string, "assertion": string, "setup": string}. '
        'Test names must be unique and start with "test_"."'
    )

    @property
    def name(self) -> str:
        return "Test Generator"

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

        valid_types = {"Unit", "Integration", "Unit + Integration"}
        test_type = data.get("test_type")
        if test_type not in valid_types:
            raise LLMError(f"LLM result has invalid 'test_type': {test_type!r}")

        def _clean_cases(raw) -> list[Dict[str, str]]:
            cases = []
            for case in raw if isinstance(raw, list) else []:
                if isinstance(case, dict) and isinstance(case.get("name"), str) and case["name"].strip():
                    cases.append({
                        "name": case["name"],
                        "description": str(case.get("description", "")),
                        "assertion": str(case.get("assertion", "")),
                        "setup": str(case.get("setup", "")),
                    })
            return cases[:10]

        unit_tests = _clean_cases(data.get("unit_tests"))
        integration_tests = _clean_cases(data.get("integration_tests"))
        if not unit_tests and not integration_tests:
            raise LLMError("LLM result has no test cases")

        test_cases = unit_tests + integration_tests
        return {
            "test_type": test_type,
            "tests_generated": len(test_cases),
            "test_cases": test_cases,
            "unit_tests": unit_tests,
            "integration_tests": integration_tests,
            "engine": "llm",
        }

    # ─── Execute method (heuristic path) ───

    def execute(self, request_id: str, query: str) -> Dict[str, Any]:
        """Generate tests based on the user's specification."""

        # ── Determine test type ───────────
        test_type = self._determine_test_type(query)

        # ── Generate test cases ───────────
        functions = self._extract_functions(query) or ["main_function"]

        unit_tests = []
        integration_tests = []

        for func_name in functions:
            unit_tests.extend(self._unit_test_cases(func_name))
            integration_tests.extend(self._integration_test_cases(func_name))

        test_cases = unit_tests + integration_tests

        return {
            "test_type": test_type,
            "tests_generated": len(test_cases),
            "test_cases": test_cases,
            "unit_tests": unit_tests,
            "integration_tests": integration_tests,
        }

    # ─── Classification helpers ──────────

    def _determine_test_type(self, query: str) -> str:
        """Classify whether to generate unit tests, integration tests, or both."""

        if any(kw in query.lower() for kw in ["integration", "e2e", "end-to-end"]):
            return "Integration"
        elif any(kw in query.lower() for kw in ["unit", "component"]):
            return "Unit"
        else:
            return "Unit + Integration"

    def _extract_functions(self, query: str) -> list[str] | None:
        """Extract function names from the query text."""

        # Pattern for common method/function naming
        pattern = r'\b([a-z_][a-z0-9_]*)\b'
        matches = re.findall(pattern, query)

        # Filter out common words
        common_words = {
            "the", "and", "for", "of", "to", "with", "in", "on", "it",
            "this", "that", "will", "be", "are", "as", "not", "from",
            "a", "an", "or", "but", "is", "was", "were",
            "test", "tests", "write", "generate",
        }

        candidates = [m for m in matches if len(m) > 3 and m.lower() not in common_words]
        return list(dict.fromkeys(candidates)) if candidates else None

    # ─── Unit test generation ──────────

    def _unit_test_cases(self, func_name: str) -> list[Dict[str, Any]]:
        """Generate unit test case descriptions."""

        tests = []

        # Happy path
        tests.append({
            "name": f"test_{func_name}_happy_path",
            "description": f"Verify {func_name} returns expected result with valid inputs",
            "assertion": "# expect(result).toEqual(expected)",
            "setup": "Create valid input data",
        })

        # Empty/null input
        tests.append({
            "name": f"test_{func_name}_edge_case_empty_input",
            "description": f"Verify {func_name} handles empty/null input gracefully",
            "assertion": "# expect(result).toBeNull() or expect(error).toThrow()",
            "setup": "Create empty/null input data",
        })

        # Invalid type
        tests.append({
            "name": f"test_{func_name}_edge_case_invalid_type",
            "description": f"Verify {func_name} raises appropriate error for invalid input types",
            "assertion": "# expect(await fn()).toThrow()",
            "setup": "Create input with wrong type",
        })

        # Max length
        tests.append({
            "name": f"test_{func_name}_edge_case_max_length",
            "description": f"Verify {func_name} handles maximum input length correctly",
            "assertion": "# expect(result).toHaveLength(max_len)",
            "setup": "Create input at maximum allowed length",
        })

        # Min length
        tests.append({
            "name": f"test_{func_name}_edge_case_min_length",
            "description": f"Verify {func_name} handles minimum input length correctly",
            "assertion": "# expect(result).toHaveLength(min_len)",
            "setup": "Create input at minimum allowed length",
        })

        # Null value
        tests.append({
            "name": f"test_{func_name}_edge_case_null",
            "description": f"Verify {func_name} handles None/null values gracefully",
            "assertion": "# expect(result).toBeNone() or assertRaises(ValueError)",
            "setup": "Create input with None/null values",
        })

        # Empty string
        tests.append({
            "name": f"test_{func_name}_edge_case_empty_string",
            "description": f"Verify {func_name} handles empty string input correctly",
            "assertion": "# expect(result).toBe('') or expect(result).toHaveLength(0)",
            "setup": "Create input with empty strings",
        })

        # Special characters
        tests.append({
            "name": f"test_{func_name}_edge_case_special_characters",
            "description": f"Verify {func_name} handles special characters safely",
            "assertion": "# expect(result).notToContain('<script>')",
            "setup": "Create input with special characters (XSS, injection)",
        })

        return tests

    # ─── Integration test generation ──────

    def _integration_test_cases(self, func_name: str) -> list[Dict[str, Any]]:
        """Generate integration test case descriptions."""

        tests = []

        # Database call
        tests.append({
            "name": f"test_{func_name}_integration_db",
            "description": f"Verify {func_name} correctly interacts with the database",
            "assertion": "# expect(db_result).toEqual(expected)",
            "setup": "# Use test database fixture\n# with test_db():",
        })

        # API call
        tests.append({
            "name": f"test_{func_name}_integration_api",
            "description": f"Verify {func_name} correctly calls external API",
            "assertion": "# assert response.status_code == 200",
            "setup": "# with mock_client:",
        })

        # File I/O
        tests.append({
            "name": f"test_{func_name}_integration_file",
            "description": f"Verify {func_name} correctly reads/writes files",
            "assertion": "# assert file.exists()\n# assert content == expected",
            "setup": "# with tempfile.NamedTemporaryFile():",
        })

        return tests
