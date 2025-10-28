🧠 AI Copilot Framework

AI Copilot is a local, experimental framework for building intelligent assistants and autonomous agents.
It’s a personal learning project designed to explore how large language models can reason, plan, and interact with tools — eventually growing into a flexible framework for multi-agent systems.

🚀 Overview

Current capabilities:

- Full chat interface with FastAPI backend and React + Vite frontend

- Integration with OpenAI’s GPT models (currently using gpt-4o-mini)

- A working ReAct-style Agent Layer capable of reasoning and invoking tools autonomously

- Tool system with registry and runtime management

- Tools include: web search / HTTP request, summarization, translation, keyword extraction, calculator, and context retrieval

- Context-aware memory and document retrieval

- Simple frontend UI with chat, sidebar, and memory/document panel

In short, it’s a functioning local AI assistant — built from scratch to understand how every layer of the stack works.

⚙️ Tech Stack

Backend: Python · FastAPI

Frontend: React · Vite

AI: OpenAI Chat Completions (via LangChain + langchain_openai)

Database: SQLite (through SQLAlchemy ORM)

🧩 Architecture

The project is structured around layers:

- Tool Layer - Defines and registers modular tools (@register_tool) with .run() or .arun() methods.
- Agent Layer - ReAct-style reasoning loop allowing the LLM to plan, select, and execute tools autonomously.
- Pipeline - Manages context retrieval, summarization, tool calling, and agent orchestration.
- Frontend - Lightweight React interface for interaction and experimentation.

The system is designed for incremental growth — each new layer builds on existing capabilities without refactoring the entire core.

🧪 Setup (Local)

Clone and run locally:

`git clone https://github.com/st000ne/Copilot`

`edit .env file to include OpenAI and DeepL (only for translation tool) api keys`

`run the run.py`

🧭 Roadmap

This project is under active development — next milestones include:

Planner & Supervisor Agent: top-level orchestration of sub-agents and task delegation

Detailed logging and trace system for reasoning transparency

LangGraph integration for structured multi-agent workflows

Complete frontend redesign for usability and debugging

Extended model support (Anthropic, Gemini, Ollama, etc.) with configurable model settings

Containerization & Cloud deployment

💡 Purpose

This repository isn’t meant as a polished product — it’s a learning playground for mastering AI system design, reasoning loops, and practical LLM integration.
Every module is intentionally transparent, so behavior can be observed, changed, and improved without magic wrappers.

🖥️ UI

A minimal but functional web interface allows chatting, memory inspection, and live testing of new tools and agent behaviors.

🧑‍💻 Author

Developed by st000ne
 — backend developer transitioning into AI engineering, exploring how reasoning systems and tool-based agents can evolve from first principles.