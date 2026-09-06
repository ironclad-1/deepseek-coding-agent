# DeepSeek Local Coding Agent

A locally running, Claude Code-style coding agent powered by DeepSeek through Ollama.

## Project Goal

Build a local coding agent capable of understanding unfamiliar Git repositories, reading and searching source code, planning tasks, modifying files, running tests and commands, reviewing changes, and eventually committing and pushing approved changes to GitHub.

## Core Workflow

```text
User Task
    ↓
DeepSeek Agent
    ↓
Plan / Reason
    ↓
Use Tools
    ↓
Observe Results
    ↓
Review / Fix
    ↓
Test
    ↓
Git Diff
    ↓
User Approval
    ↓
Commit
    ↓
Push
    ↓
GitHub
```

## Current Architecture

```text
User
 ↓
Agent Runtime
 ├── Model Layer
 ├── Tool System
 ├── Repository Engine
 ├── Safety Layer
 ├── Git Engine
 └── Reasoning Recorder
        ↓
     .reason/
```

## Technology

* Python 3.13.14
* Ollama 0.32.7
* Ollama Python SDK 0.6.2
* Git 2.54.0.windows.1
* DeepSeek-R1 14B tool-calling model
* Windows
* Intel Core i5-11400H
* NVIDIA GeForce RTX 2050 4 GB VRAM
* Approximately 24 GB RAM

## Foundation Progress

```text
Phase 0  ✅ Final Architecture
Phase 1  ✅ Environment & Hardware Validation
Phase 2  ✅ Ollama / DeepSeek Model Layer
Phase 3  ✅ Agent Runtime
Phase 4  ✅ Repository Discovery
Phase 5  ✅ Tool System
Phase 6  ✅ File Reading
Phase 7  ✅ Repository Search
```

## Current Capabilities

The current foundation can:

* Connect Python to Ollama
* Run the selected DeepSeek model
* Capture model thinking traces
* Save reasoning traces as `.reason` files
* Handle structured tool calls
* Maintain agent sessions
* Execute registered tools
* Discover repository structure
* Detect project and test files
* Inspect Git repository state
* Safely read repository files
* Search repository contents

## Planned MVP

The MVP will add:

```text
Phase 8  → File Editing
Phase 9  → Command Execution
Phase 10 → Safety & Approval
Phase 11 → Git Integration
Phase 12 → Self-Review & Testing
Phase 13 → Git Commit
Phase 14 → Git Push
```

## Future Capabilities

The longer-term project will support:

```text
Method description generation
Workflow diagram generation
Large repository context management
Failure recovery
Project-specific instructions
Session management
Model benchmarking
GitHub API integration
Issue and Pull Request automation
```

## Project Structure

```text
deepseek-coding-agent/
│
├── agent/
├── context/
├── git/
├── Phases/
├── prompts/
├── reasoning/
├── repository/
├── safety/
├── sessions/
├── tests/
├── tools/
├── workspace/
│
├── .gitignore
├── README.md
├── config.py
├── main.py
├── requirements.txt
└── Roadmap.rdmp
```

## Development Principle

The MVP is not intended to be a throwaway prototype.

Each phase is designed as a direct extension of the final architecture so that later features can be added without replacing the core agent.

## Status

Foundation complete.

Next milestone: **MVP — File Editing**.
