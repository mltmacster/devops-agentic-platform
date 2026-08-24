"""Development Stack Definitions — Available stacks can be provisioned in sandboxes.

Each stack is a combination of runtime + tools + database that can be provisioned
in a sandbox instance. Stacks are implemented as plugins (see plugin_interface.py).

## Available Stacks
1. Python Stack: Python 3.12 + pip + FastAPI + SQLite
2. Rust Stack: Rust 1.70+ + cargo + Actix + SQLite  
3. Node.js Stack: Node 20 + npm/yarn + React + Express
4. ML/Data Stack: Python + pgVector 0.8.0 + Ollama + LangGraph
5. Full Web Stack: Node.js + React + PostgreSQL + pgML + pgGraph

## Plugin Interface
All stacks implement the `StackModule` interface (see src/agentic/common/plugin_interface.py).

## Plugin Discovery
Plugins can be:
- Built-in (shipped with the platform)
- Community plugins (from ~/.dap/plugins/)
- Enterprise plugins (custom, signed by your org)

"""
