from pathlib import Path

OLLAMA_HOST = "http://localhost:11434"
MODEL_NAME = "qwen3:8b"

PROJECT_ROOT = Path(__file__).resolve().parent

REASONING_DIR = PROJECT_ROOT / ".reason"
RESULTS_DIR = PROJECT_ROOT / ".results"

THINK = True
STREAM = True
KEEP_ALIVE = "5m"
REQUEST_TIMEOUT = 300.0