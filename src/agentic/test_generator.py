"""Test Generator Agent — Writes unit and integration tests.

Analyzes source code or specs to generate pytest-style test fixtures,
mocks, and assertions that cover happy paths and edge cases.
"""

import re
from .plugin_interface import BaseAgent
from typing import Dict, Any


class TestGeneratorAgent(BaseAgent):
    """Test Generator: Produces unit and integration tests from specs/code."""

    @property
    def name(self) -> str:
        return "Test Generator"

    # ─── Execute method ────────────────

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
