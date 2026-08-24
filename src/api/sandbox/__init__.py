"""Agentic AI Engine — Multi-Agent Orchestration Layer

This module implements the agentic AI coding engine that powers the platform's
AI-assisted development features.

## Architecture Overview
```
User Request → Intent Analyzer → Agent Router → [Code Architect / Debugger / Test Generator]
                                      ↓
                              Tool Provider Registry
                                      ↓
                            [Git | Crawle4AI | IBM Docling | LangGraph | Ollama | pgVector]
```

## Agent Types
1. **Code Architect** — Plans and scaffolds code structures, generates boilerplate
2. **Debug Agent** — Traces errors through stack traces, suggests fixes
3. **Test Generator** — Writes unit/integration tests based on source code
4. **Researcher** — Scrapes web docs, retrieves API references (Crawle4AI)
5. **Documentation Agent** — Generates API docs from code (Docling)

## Tool Provider Registry
All tools implement the `BaseTool` interface and are registered via plugin discovery.

See src/agentic/tool_registry.py for the tool registry implementation.
"""
