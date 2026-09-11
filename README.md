# DeepSeek Local Coding Agent

A locally running, Claude Code-style coding agent built in Python and powered by a local LLM through Ollama.

## Project Goal

Build a local coding agent capable of understanding unfamiliar Git repositories, reading and searching source code, planning tasks, modifying files, running tests and commands, reviewing changes, and eventually committing and pushing approved changes to GitHub.

The agent is being developed phase-by-phase so that each capability becomes part of the final architecture rather than a temporary prototype.

## Core Workflow

```text
User Task
    ↓
Agent Runtime
    ↓
Plan / Reason
    ↓
Save Reasoning Trace
    ↓
Use Registered Tools
    ↓
Observe Tool Results
    ↓
Continue Reasoning / Review
    ↓
Produce Final Answer
    ↓
Save Result
    ↓
Test / Review Changes
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
User / CLI
    ↓
Agent Runtime
    ├── Model Layer
    │      ↓
    │    Ollama
    │      ↓
    │    Local LLM
    │
    ├── Tool System / Registry
    │      ├── File System Tools
    │      ├── Repository Search
    │      └── Terminal Tools
    │
    ├── Repository Engine
    │      ├── Repository Discovery
    │      ├── File Inspection
    │      └── Search
    │
    ├── Safety Layer
    │      └── Approval Controls
    │
    ├── Git Engine
    │
    └── Output / Reasoning Recording
           ├── .reason/
           └── .results/
```

## Current Model

The currently validated model for the agent is:

```text
qwen3:8b
```

Qwen3 8B is currently being used as the primary model because it successfully handled structured tool calls in the real repository integration test.

DeepSeek models were evaluated during the model-selection phase, but the current repository-agent workflow is being continued with `qwen3:8b`.

## Technology

* Python 3.13.14
* Ollama 0.32.7
* Ollama Python SDK 0.6.2
* Git 2.54.0.windows.1
* Qwen3 8B
* Windows
* Intel Core i5-11400H
* NVIDIA GeForce RTX 2050 4 GB VRAM
* Approximately 24 GB RAM

## Foundation Progress

```text
Phase 0  ✅ Final Architecture

Phase 1  ✅ Environment & Hardware Validation

Phase 2  ✅ Ollama / Model Layer

Phase 3  ✅ Agent Runtime

Phase 4  ✅ Repository Discovery

Phase 5  ✅ Tool System

Phase 6  ✅ File Reading

Phase 7  ✅ Repository Search
```

## Current Capabilities

The current foundation can:

* Connect Python to Ollama
* Run the selected local LLM
* Capture model thinking traces
* Save reasoning traces as `.reason` files
* Save final answers as `.result` files
* Handle structured tool calls
* Maintain agent sessions
* Execute registered tools through the Tool Registry
* Discover repository structure
* Detect project and test files
* Inspect Git repository state
* Safely read repository files
* Search repository contents

## Real Repository Validation

The foundation has been tested against a real GitHub repository cloned locally rather than only against synthetic test data.

The agent was given the task to:

```text
Find where Telegram is used in this repository,
read the relevant file,
and explain what it does.

The agent was required to use search_repo first
and then read_file before answering.
```

The validated execution flow was:

```text
User Task
    ↓
search_repo("Telegram")
    ↓
Search Results
    ↓
read_file("README.md")
    ↓
File Contents
    ↓
Model Reasoning
    ↓
Final Answer
```

This confirmed that the model, agent runtime, tool registry, repository search, file-reading tools, reasoning recorder, and final-result handling can operate together in a real repository workflow.

## Reasoning and Results

The agent keeps reasoning traces and final answers separate.

```text
.reason/
    └── Reasoning traces from model turns

.results/
    └── Final answers produced by completed agent tasks
```

`.reason/` is intended for debugging and auditing model reasoning.

`.results/` stores the final user-facing answer returned by the agent.

Both directories are runtime-generated artifacts and are excluded from Git.

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
Context management

Large repository support

Failure recovery

Project-specific instructions

Session management

Method description generation

Workflow diagram generation

Evaluation framework

Performance optimization

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
├── results/
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

Runtime output directories:

```text
.reason/
.results/
```

These are generated locally and are not committed to Git.

## Development Principle

The MVP is not intended to be a throwaway prototype.

Each phase is designed as a direct extension of the final architecture so that later capabilities can be added without replacing the core agent.

The development process prioritizes:

```text
Validate
    ↓
Integrate
    ↓
Test on a real repository
    ↓
Keep the capability
    ↓
Build the next phase
```

## Status

**Foundation complete.**

Next milestone:

**MVP — File Editing**
