# DeepSeek Local Coding Agent

A locally running, Claude Code-style coding agent built in Python and powered by a local LLM through Ollama.

## Project Goal

Build a local coding agent capable of understanding unfamiliar Git repositories, reading and searching source code, planning coding tasks, modifying files safely, running commands and tests, reviewing its own changes, presenting proposed changes to the user, obtaining informed approval, committing approved changes, and eventually pushing approved commits to GitHub.

The agent is being developed phase-by-phase so that each capability becomes part of the final architecture rather than a temporary prototype.

The final system is intended to support a workflow such as:

```text
                    User Task
                        │
                        ▼
              Understand Repository
                        │
                        ▼
                  Plan / Reason
                        │
                        ▼
   ┌───────────► Propose Changes
   │                    │
   │                    ▼
   │           Explain WHAT + WHY
   │                    │
   │                    ▼
   │               User Approval
   │              ╱            ╲
   │       Rejected            Approved
   │           │                   │
   │           ▼                   ▼
   │   Ask Rejection Reason       Test
   │           │                   │
   │           ▼                   ▼
   │   Feed Reason to Model      Review
   │           │                   │
   │      ┌────┴────┐              ▼
   │      │         │            Commit
   │      ▼         ▼              │
   │ User suggests  No changes     ▼
   │ modification   required      Push
   │      │         │              │
   └──────┘         └──────────► Stop
```

## Quick Start

### 1. Create and activate the virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

Make sure Ollama is installed and running, then verify the configured model is available:

```powershell
ollama list
```

The current model is:

```text
qwen3:8b
```

### 3. Start the agent

From the project root:

```powershell
python main.py
```

Enter the coding task when prompted.

### 4. Run tests

Phase 12 runtime tests:

```powershell
python -m pytest tests/test_phase12_runtime.py -v
```

Phase 12 runner test:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python tests/test_phase12_runner.py
```

Older phase tests are currently standalone Python test scripts and can be executed directly:

```powershell
python tests/test_phase11_git_operations.py
```

### 5. Runtime artifacts

During execution, reasoning traces and final results are stored locally in:

```text
.reason/
.results/
```

These directories are excluded from Git.


## Core Workflow

```text
User Task
    ↓
Agent Runtime
    ↓
Repository Understanding
    ↓
Plan / Reason
    ↓
Save Reasoning Trace
    ↓
Use Registered Tools
    ↓
Observe Tool Results
    ↓
Review / Test Changes
    ↓
Build Change Proposal
    ↓
Explain WHAT and WHY
    ↓
User Approval
    ├── YES
    │    ↓
    │  Execute Approved Changes
    │    ↓
    │  Test / Review
    │
    └── NO
         ↓
      Ask Rejection Reason
         ↓
      Feed Reason to Model
         ↓
      Revise / Clarify / Stop
    ↓
Git Diff
    ↓
Commit Approval
    ↓
Commit
    ↓
Push Approval
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
    ├── Planner / Change Management
    │      ├── Task interpretation
    │      ├── Change proposal
    │      ├── WHAT
    │      ├── WHY
    │      └── Change state
    │
    ├── Tool System / Registry
    │      ├── File System Tools
    │      ├── Repository Search
    │      ├── Terminal Tools
    │      └── Git Tools
    │
    ├── Repository Engine
    │      ├── Repository Discovery
    │      ├── File Inspection
    │      └── Search
    │
    ├── Safety Layer
    │      ├── Approval Policy
    │      └── Change Approval Gate
    │
    ├── Test / Review Runner
    │      ├── Test Execution
    │      └── Git Diff Review
    │
    ├── Git Engine
    │      ├── Status
    │      ├── Diff
    │      ├── Log
    │      ├── Branch
    │      ├── Remote
    │      ├── Add
    │      └── Commit
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

Qwen3 8B is currently being used as the primary model because it successfully handled structured tool calls in real repository integration tests.

DeepSeek models were evaluated during the model-selection phase. The official DeepSeek R1 14B model did not reliably perform the required tool-calling workflow in the initial calculator/tool tests, while the community DeepSeek tool-calling build was usable in isolated tests but was slower and less reliable in real repository workflows.

The project therefore currently continues with:

```text
qwen3:8b
```

The model layer remains configurable so that another model can be evaluated later without redesigning the agent architecture.

## Technology

```text
Python              3.13.14
Ollama              0.32.7
Ollama Python SDK   0.6.2
Git                 2.54.0.windows.1
Primary Model       Qwen3 8B
Operating System    Windows
CPU                 Intel Core i5-11400H
GPU                 NVIDIA GeForce RTX 2050 4 GB VRAM
RAM                 Approximately 24 GB
```

## Development Phases

```text
Phase 0   ✅ Final Architecture

Phase 1   ✅ Environment & Hardware Validation

Phase 2   ✅ Ollama / Model Layer

Phase 3   ✅ Agent Runtime

Phase 4   ✅ Repository Discovery

Phase 5   ✅ Tool System

Phase 6   ✅ File Reading

Phase 7   ✅ Repository Search

Phase 8   ✅ File Editing

Phase 9   ✅ Command Execution

Phase 10  ✅ Safety & Approval Foundation

Phase 11  ✅ Git Integration — Read-Only Operations

Phase 12  ✅ Self-Review & Testing Loop

Phase 13  🔄 Change Approval + Git Commit

Phase 14  ⏳ Git Push
```

## Phase 8 — File Editing

The agent can now safely create and modify repository files.

Implemented operations:

```text
read_file()
write_file()
edit_file()
```

File editing includes:

```text
Repository path validation
Path traversal protection
UTF-8 validation
Binary-file detection
File size limits
Overwrite protection
Exact single-occurrence replacement
Safe file creation
```

`edit_file()` rejects ambiguous modifications when the requested `old_text` occurs more than once.

## Phase 9 — Command Execution

Controlled command execution was implemented using `shell=False`.

Supported command families currently include approved executables such as:

```text
python
python.exe
py
py.exe
pytest
pytest.exe
git
git.exe
pip
pip.exe
```

The command execution layer includes:

```text
Executable allowlisting
Blocked command detection
Shell chaining protection
Shell redirection protection
PowerShell / CMD rejection
Working-directory control
Timeout handling
stdout capture
stderr capture
Exit-code capture
```

Commands are never executed through an unrestricted shell.

## Phase 10 — Safety & Approval Foundation

A safety layer was added to classify tool requests into:

```text
SAFE
REQUIRE_APPROVAL
DENIED
```

### Safe operations

```text
read_file
search_repo

git_status
git_diff
git_log
git_branch
git_remote
```

### Approval-required operations

```text
write_file
edit_file
run_command
```

### Explicitly denied operations

Dangerous commands such as the following are blocked:

```text
del
erase
rd
rmdir
format
shutdown
restart-computer
stop-computer
remove-item
set-content
add-content
invoke-expression
iex
powershell
powershell.exe
cmd
cmd.exe
```

Unknown tools and unapproved executables are denied by default.

The safety layer is deliberately separate from user interaction:

```text
ApprovalManager
    ↓
decides SAFE / APPROVAL / DENIED

Agent Runtime
    ↓
handles user interaction
```

## Phase 11 — Git Integration

Read-only Git operations were implemented:

```text
git_status()
git_diff()
git_log()
git_branch()
git_remote()
```

These operations validate that the target directory is a Git repository before execution.

The Git engine uses:

```text
subprocess.run()
shell=False
captured stdout / stderr
timeouts
structured ToolResult
```

The following mutating Git operations were subsequently added for Phase 13:

```text
git_add()
git_commit()
```

They are intentionally separate.

```text
git_add()
    ↓
Stage explicitly selected files

git_commit()
    ↓
Commit currently staged changes
```

`git_commit()` does not automatically stage every repository file.

## Phase 12 — Self-Review & Testing Loop

Phase 12 introduced `agent/runner.py`.

The runner provides:

```text
TestRunResult
ReviewResult
ValidationResult
AgentRunner
```

The validation workflow is:

```text
Modify Files
    ↓
Run Tests
    ↓
Capture Result
    ↓
Review Git Diff
    ↓
Return Feedback to Model
    ↓
Fix if Necessary
    ↓
Retest
```

The runtime integration ensures that runner-triggered commands do not bypass Phase 10 safety.

The self-review test command is supplied explicitly, for example:

```python
runtime.run(
    "Fix the bug in app.py.",
    test_command="pytest",
)
```

A repository does not have to use pytest; another appropriate test command can be supplied later.

## Phase 13 — Change Approval and Git Commit

Phase 13 is currently being redesigned around a more user-centered approval workflow.

The earlier approval model was tool-centric:

```text
Model
    ↓
write_file
    ↓
Approve this tool? [y/n]
```

The new architecture is change-centric:

```text
Model
    ↓
Plan
    ↓
Change Proposal
    ↓
WHAT will change?
WHY will it change?
WHICH files are involved?
WHICH operations are planned?
    ↓
User Approval
```

The user should see an understandable summary before repository modifications occur.

Example:

```text
PROPOSED CHANGES

WHAT:
- Add the addition operation to calculator.py.
- Add tests for the new operation.

WHY:
- The requested feature requires addition support.
- The existing implementation does not provide it.

FILES:
- calculator.py
- tests/test_calculator.py

Do you approve these changes? [y/n]:
```

### Rejection workflow

Rejecting a proposal should no longer produce only a generic tool error.

Instead:

```text
User: n
    ↓
Agent asks:
"Why are you not approving these changes?"
    ↓
User provides reason
    ↓
Reason is added to the model conversation
    ↓
Model interprets the reason
```

The model can then:

```text
Revise the proposed modification
        OR
Ask a clarification question
        OR
Stop the modification
```

For example:

```text
User:
Don't add the addition operation.

Model:
Understood. I will not add the addition operation.
```

If the user clearly does not want repository changes, the agent should stop the modification workflow rather than repeatedly requesting approval.

### Git Commit

After implementation, testing, and diff review, the intended commit flow is:

```text
git_status
    ↓
git_diff
    ↓
Tests
    ↓
Change Review
    ↓
User Approval
    ↓
git_add
    ↓
User Approval
    ↓
git_commit
```

Current Phase 13 Git safety classification:

```text
git_add      → REQUIRE_APPROVAL

git_commit   → REQUIRE_APPROVAL
```

Git push is intentionally not included in Phase 13.

## Current Capabilities

The project can now:

```text
Connect Python to Ollama

Run a local LLM

Capture model-provided thinking traces

Save reasoning traces as .reason files

Save final answers as .result files

Maintain agent sessions

Handle structured model tool calls

Execute tools through a Tool Registry

Discover repository structure

Inspect repository files

Search repository contents

Safely create files

Safely edit files

Run approved commands

Run tests

Capture stdout / stderr / exit codes

Handle command timeouts

Review Git diffs

Inspect Git status

Inspect Git history

Inspect current branch

Inspect Git remotes

Stage explicitly selected Git paths

Create Git commits from staged changes

Require approval for mutating operations

Feed self-review results back into the model
```

The new change-approval architecture additionally targets:

```text
Human-readable change summaries

WHAT explanation

WHY explanation

Approval before mutation

Rejection reason collection

Model feedback after rejection

Revision / clarification / stop behavior
```

## Reasoning and Results

The agent keeps model reasoning and final answers separate.

```text
.reason/
    └── Reasoning traces from model turns

.results/
    └── Final answers produced by completed agent tasks
```

`.reason/` is intended for debugging and auditing.

`.results/` stores final user-facing answers.

There is also a Python package:

```text
results/
└── recorder.py
```

which contains the code responsible for writing `.result` files.

The runtime-generated `.reason/` and `.results/` directories are excluded from Git.

## Testing Strategy

The project currently contains two testing styles.

### Legacy phase tests

Phases 1–11 contain several standalone Python test programs that use explicit assertions and can be executed directly:

```powershell
python tests/test_phase11_git_operations.py
```

### Pytest-based tests

Phase 12 introduced pytest-based test functions:

```powershell
python -m pytest tests/test_phase12_runtime.py -v
```

Phase 12 runtime integration currently has:

```text
5 tests
5 passed
```

Phase 12 runner validation currently has:

```text
14 checks
14 passed
```

The existing runner test is still structured as a standalone test program and is therefore executed directly.

The testing structure will be standardized later rather than rewriting all earlier phase tests unnecessarily.

## Validation History

Important validation milestones include:

```text
Phase 8
File editing tests passed.

Phase 9
Command execution tests passed.
Real Qwen3 command-execution integration passed.

Phase 10
Safety policy tests passed.
Runtime safety tests passed.
Real-model rejection testing passed.
Real-model safety integration passed.

Phase 11
Git operations tests passed.
Read-only repository state was verified.
Real Qwen3 Git integration passed.

Phase 12
AgentRunner:
14/14 checks passed.

Phase 12 Runtime:
5/5 pytest tests passed.
```

## Real Repository Validation

The foundation and multiple later phases have been tested against real local Git repositories rather than only synthetic objects.

The real integration workflow has validated combinations of:

```text
Qwen3 model
    ↓
Agent Runtime
    ↓
Tool Registry
    ↓
Repository Search
    ↓
File Reading
    ↓
File Editing
    ↓
Command Execution
    ↓
Safety / Approval
    ↓
Git inspection
```

This has established that the core agent components can operate together in a real repository environment.

## Project Structure

```text
deepseek-coding-agent/
│
├── agent/
│   ├── __init__.py
│   ├── loop.py
│   ├── model.py
│   ├── planner.py
│   ├── runner.py
│   ├── runtime.py
│   ├── session.py
│   └── change_manager.py          # Phase 13 architecture
│
├── context/
│   ├── __init__.py
│   ├── history.py
│   ├── manager.py
│   └── selector.py
│
├── git/
│   ├── __init__.py
│   └── operations.py
│
├── Phases/
│   ├── Phase-1
│   ├── Phase-2
│   ├── Phase-3
│   ├── Phase-4
│   ├── Phase-5
│   ├── Phase-6
│   └── Phase-7
│
├── prompts/
│   ├── system.txt
│   └── approval.txt               # Phase 13 architecture
│
├── reasoning/
│   ├── __init__.py
│   ├── formatter.py
│   └── recorder.py
│
├── repository/
│   ├── __init__.py
│   ├── context.py
│   ├── scanner.py
│   └── search.py
│
├── results/
│   ├── __init__.py
│   └── recorder.py
│
├── safety/
│   ├── __init__.py
│   ├── approval.py
│   └── change_gate.py
│
├── sessions/
│
├── tests/
│   ├── test_agent.py
│   ├── test_foundation_integration.py
│   ├── test_phase10_model_report_consistency.py
│   ├── test_phase10_runtime.py
│   ├── test_phase10_safety.py
│   ├── test_phase11_git_operations.py
│   ├── test_phase12_runner.py
│   ├── test_phase12_runtime.py
│   ├── test_phase13_git_commit.py
│   ├── test_phase2_model.py
│   ├── test_phase2_streaming.py
│   ├── test_phase2_tools.py
│   ├── test_phase3_runtime.py
│   ├── test_phase4_repository.py
│   ├── test_phase5_tools.py
│   ├── test_phase6_file_reading.py
│   ├── test_phase7_repository_search.py
│   ├── test_phase8_file_editing.py
│   └── test_phase9_command_execution.py
│
├── tools/
│   ├── __init__.py
│   ├── filesystem.py
│   ├── registry.py
│   ├── search.py
│   └── terminal.py
│
├── workspace/
│   └── .gitkeep
│
├── .gitignore
├── README.md
├── config.py
├── main.py
├── requirements.txt
└── Roadmap.rdmp
```

Runtime-generated directories:

```text
.reason/
.results/
```

These are generated locally and are not committed to Git.

## Important Architectural Principles

### Controlled Tool Execution

The model never receives unrestricted machine access.

```text
Model
    ↓
Tool Request
    ↓
Tool Registry
    ↓
Safety Policy
    ↓
Approval when required
    ↓
Tool Execution
```

### Safety Is Separate From Interaction

The safety system decides:

```text
SAFE
REQUIRE_APPROVAL
DENIED
```

The runtime and change gate handle the interaction with the user.

### Change Approval Is Human-Centered

Repository modifications should be presented in understandable terms:

```text
WHAT
WHY
FILES
OPERATIONS
```

The user should be able to reject a proposal and explain the reason.

That rejection reason becomes part of the agent's context.

### Reasoning Traces Are Audit Artifacts

`.reason` files record model-provided thinking traces.

They are not treated as repository working memory.

### Explicit Git Staging

Git staging is explicit.

```text
git_add(paths)
```

stages selected paths only.

`git_commit(message)` commits currently staged changes.

The agent should not silently stage unrelated repository files.

### Incremental Architecture

The MVP is not intended to be a throwaway prototype.

Every phase is designed as a direct extension of the final architecture so that later capabilities can be added without replacing the core agent.

The development process prioritizes:

```text
Validate
    ↓
Integrate
    ↓
Test
    ↓
Validate on a real repository
    ↓
Keep the capability
    ↓
Build the next phase
```

## Planned Future Capabilities

After the MVP:

```text
Phase 15 → Context Management

Phase 16 → Large Repository Support

Phase 17 → Failure Recovery

Phase 18 → Project Instructions

Phase 19 → Session Management

Phase 20 → Evaluation Framework

Phase 21 → Performance Optimization

Phase 22 → Model Benchmarking
```

Later V2 capabilities:

```text
Phase 23 → GitHub API Integration

Phase 24 → Issue & Pull Request Automation
```

Additional planned capabilities include:

```text
Method description generation

Workflow diagram generation

Repository-specific instructions

Improved session persistence

Failure recovery

Large-repository indexing

Better context selection

Evaluation and benchmarking

GitHub issue automation

Pull request automation
```

## Final Success Criterion

The long-term goal is to give the agent:

```text
"Fix this problem in this unfamiliar repository."
```

and have it perform the complete workflow:

```text
1. Understand the repository

2. Find the relevant code

3. Plan the solution

4. Explain WHAT and WHY

5. Obtain user approval

6. Make the required changes

7. Run appropriate tests

8. Diagnose failures

9. Fix failures

10. Retest

11. Review the Git diff

12. Present the resulting changes

13. Obtain commit approval

14. Stage the intended files

15. Create the commit

16. Obtain push approval

17. Push to GitHub
```

The agent should also correctly handle user feedback such as:

```text
"Don't make any changes."

"Don't modify the frontend."

"Do not add that feature."

"Change the implementation to use another approach."

"Why did you make this change?"
```

The model should use such feedback to revise, clarify, or stop rather than blindly continuing execution.

## Current Status

```text
Foundation                         ✅ Complete
MVP Phases 8–12                   ✅ Complete
Phase 13 Git foundation            ✅ Partially implemented
Phase 13 Change Approval           🔄 In progress
Phase 13 Commit Workflow           ⏳ Pending final approval integration
Phase 14 Git Push                  ⏳ Pending
```

Current development focus:

```text
Change Proposal
      ↓
WHAT + WHY
      ↓
User Approval
      ↓
Rejection Reason
      ↓
Model Feedback
      ↓
Revision / Clarification / Stop
      ↓
Approved Repository Modification
      ↓
Testing
      ↓
Diff Review
      ↓
Git Commit
```
