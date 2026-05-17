#!/usr/bin/env sh
set -eu

ROOT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

ollama pull llama3.2:latest
ollama pull qwen3:8b

ollama create resume-jd-cleaner:latest -f "$ROOT_DIR/ollama/Modelfile.jd-cleaner"
ollama create resume-context-classifier:latest -f "$ROOT_DIR/ollama/Modelfile.resume-context"
ollama create resume-inference-matcher:latest -f "$ROOT_DIR/ollama/Modelfile.inference-match"
ollama create resume-comparison-narrator:latest -f "$ROOT_DIR/ollama/Modelfile.comparison-narrator"

ollama list
