"""Code Architect Agent — Plans and scaffolds application code.

Analyzes requirements, generates architecture decisions, and produces
boilerplate project scaffolding. Uses an LLM when DAP_LLM_API_KEY is
configured; otherwise falls back to built-in scaffolding templates.
"""

import logging

from .llm import LLMClient, LLMError, get_llm_client
from .plugin_interface import BaseAgent
from typing import Dict, Any

logger = logging.getLogger(__name__)


class CodeArchitectAgent(BaseAgent):
    """Code Architect: Generates scaffolding plans and boilerplate from natural-language specs."""

    SYSTEM_PROMPT = (
        "You are the DAP Code Architect agent. From the user's project request, "
        "produce scaffolding guidance. Return ONLY a JSON object with exactly "
        'these keys: {"project_type": string, "tech_stack": array of strings, '
        '"files": array of objects} Rules: project_type is one of "REST API", '
        '"Web Application", "Mobile Application", "CLI Tool", "Microservice", '
        '"Dashboard / Admin Panel", or "Application (unspecified)". tech_stack is '
        '2-5 technology names. files is 3-10 objects of {"path": string, '
        '"description": string} with absolute paths under /workspace/."'
    )

    @property
    def name(self) -> str:
        return "Code Architect"

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

        project_type = data.get("project_type")
        if not isinstance(project_type, str) or not project_type.strip():
            raise LLMError("LLM result missing 'project_type'")

        tech_stack = [s for s in data.get("tech_stack", []) if isinstance(s, str) and s.strip()][:10]
        if not tech_stack:
            raise LLMError("LLM result has empty 'tech_stack'")

        files = [
            {"path": f["path"], "description": str(f.get("description", ""))}
            for f in data.get("files", [])
            if isinstance(f, dict) and isinstance(f.get("path"), str) and f["path"].strip()
        ][:25]
        if not files:
            raise LLMError("LLM result has no 'files'")

        return {
            "plan": [
                f"Analyzing requirements for a {project_type}",
                f"Selecting technology stack: {', '.join(tech_stack)}",
                f"Generating project scaffolding ({len(files)} files)",
            ],
            "project_type": project_type,
            "tech_stack": tech_stack,
            "files_created": [f["path"] for f in files],
            "files": files,
            "engine": "llm",
        }

    # ─── Execute method (heuristic path) ───

    def execute(self, request_id: str, query: str) -> Dict[str, Any]:
        """Generate scaffolding plan and boilerplate for the requested project."""

        # ── Parse intent from query ───────────────
        project_type = self._classify_project(query)

        # ── Generate scaffolding plan ─────────────
        stack = self._select_tech_stack(project_type, query)
        files = self._generate_scaffold(project_type, stack)

        return {
            "plan": [
                f"Analyzing requirements for a {project_type}",
                f"Selecting technology stack: {', '.join(stack)}",
                f"Generating project scaffolding ({len(files)} files)",
            ],
            "project_type": project_type,
            "tech_stack": stack,
            "files_created": [f["path"] for f in files],
            "files": files,
        }

    def _classify_project(self, query: str) -> str:
        """Classify the project type from user's request."""

        if any(kw in query.lower() for kw in ["api", "rest"]):
            return "REST API"
        elif any(kw in query.lower() for kw in ["web", "frontend", "spa"]):
            return "Web Application"
        elif any(kw in query.lower() for kw in ["mobile", "app"]):
            return "Mobile Application"
        elif any(kw in query.lower() for kw in ["cli", "command line"]):
            return "CLI Tool"
        elif any(kw in query.lower() for kw in ["microservice", "service"]):
            return "Microservice"
        elif any(kw in query.lower() for kw in ["dashboard", "admin"]):
            return "Dashboard / Admin Panel"
        else:
            return "Application (unspecified)"

    def _select_tech_stack(self, project_type: str, query: str) -> list[str]:
        """Select the technology stack based on project type and query hints."""

        stacks = {
            "REST API": ["Python", "FastAPI", "PostgreSQL"],
            "Web Application": ["React", "Next.js", "TypeScript"],
            "Mobile Application": ["React Native", "Expo", "Node.js"],
            "CLI Tool": ["Python", "Click"],
            "Microservice": ["Go", "gRPC", "PostgreSQL"],
            "Dashboard / Admin Panel": ["React", "TypeScript", "Tailwind CSS"],
        }

        # Override based on query hints
        if any(kw in query.lower() for kw in ["fastapi", "django"]):
            stacks[project_type] = ["Python", "FastAPI", "PostgreSQL"]
        elif any(kw in query.lower() for kw in ["spring", "java"]):
            stacks[project_type] = ["Java", "Spring Boot", "PostgreSQL"]

        return stacks.get(project_type, ["Python", "FastAPI", "SQLite"])

    def _generate_scaffold(self, project_type: str, stack: list[str]) -> list[Dict[str, Any]]:
        """Generate the expected scaffold files based on type and stack."""

        scaffolds = {
            "REST API": [
                {"path": "/workspace/app/main.py", "description": "FastAPI entry point"},
                {"path": "/workspace/app/models.py", "description": "Database models (SQLAlchemy)"},
                {"path": "/workspace/app/schemas.py", "description": "Pydantic schemas for validation"},
                {"path": "/workspace/app/routes.py", "description": "API routes and endpoints"},
                {"path": "/workspace/config.py", "description": "Application settings"},
            ],
            "Web Application": [
                {"path": "/workspace/app/src/index.tsx", "description": "App entry point"},
                {"path": "/workspace/app/src/App.tsx", "description": "Main application component"},
                {"path": "/workspace/app/src/components/Header.tsx", "description": "Navigation header"},
                {"path": "/workspace/app/src/components/Footer.tsx", "description": "Page footer"},
                {"path": "/workspace/app/public/index.html", "description": "Static HTML shell"},
            ],
            "Mobile Application": [
                {"path": "/workspace/app/App.tsx", "description": "Root component"},
                {"path": "/workspace/app/navigation/RootNavigator.tsx", "description": "Navigation structure"},
                {"path": "/workspace/app/screens/HomeScreen.tsx", "description": "Home screen"},
                {"path": "/workspace/app/services/api.ts", "description": "API client"},
            ],
            "CLI Tool": [
                {"path": "/workspace/main.py", "description": "CLI entry point"},
                {"path": "/workspace/cli/__init__.py", "description": "CLI package init"},
                {"path": "/workspace/cli/commands.py", "description": "Command implementations"},
            ],
            "Microservice": [
                {"path": "/workspace/app/main.py", "description": "Service entry point"},
                {"path": "/workspace/app/services/__init__.py", "description": "Services package"},
                {"path": "/workspace/app/services/health.py", "description": "Health check endpoint"},
                {"path": "/workspace/app/config.py", "description": "Service configuration"},
            ],
            "Dashboard / Admin Panel": [
                {"path": "/workspace/dashboard/src/App.tsx", "description": "Dashboard entry point"},
                {"path": "/workspace/dashboard/src/layout/DashboardLayout.tsx", "description": "Main layout"},
                {"path": "/workspace/dashboard/src/charts/AnalyticsChart.tsx", "description": "Analytics visualization"},
            ],
        }

        return scaffolds.get(project_type, [
            {"path": "/workspace/app/main.py", "description": "Application entry point"}
        ])
