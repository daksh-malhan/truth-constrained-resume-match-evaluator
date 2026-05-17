from __future__ import annotations

import re
from typing import Dict, Iterable, List, Set, Tuple

KNOWN_SKILLS = [
    "python", "typescript", "javascript", "java", "sql", "fastapi", "flask", "django", "react", "next.js",
    "langchain", "llamaindex", "rag", "semantic search", "vector search", "qdrant", "pinecone", "weaviate",
    "faiss", "chromadb", "openai api", "llm", "machine learning", "pytorch", "tensorflow", "docker",
    "kubernetes", "aws", "gcp", "azure", "postgresql", "mysql", "sqlite", "mongodb", "redis",
    "github actions", "ci/cd", "rest api", "mcp", "langgraph", "tailwind", "sqlite", "pytest",
    "git", "oop", "data structures", "algorithms", "etl", "automation", "debugging", "backend development",
]

ALIASES: Dict[str, str] = {
    "nextjs": "next.js",
    "next": "next.js",
    "openai": "openai api",
    "large language model": "llm",
    "large language models": "llm",
    "retrieval augmented generation": "rag",
    "retrieval-augmented generation": "rag",
    "containerization": "docker",
    "rest apis": "rest api",
    "apis": "rest api",
    "api": "rest api",
    "version control": "git",
    "object oriented programming": "oop",
    "object-oriented programming": "oop",
    "oop concepts": "oop",
    "data structures & algorithms": "data structures",
    "dsa": "data structures",
    "data processing": "etl",
    "etl pipelines": "etl",
    "backend services": "backend development",
    "postgres": "postgresql",
    "chroma": "chromadb",
}

PARTIAL_SIMILARITY: Dict[Tuple[str, str], float] = {
    ("fastapi", "flask"): 0.5,
    ("fastapi", "django"): 0.5,
    ("postgresql", "mysql"): 0.65,
    ("kubernetes", "docker"): 0.35,
    ("langchain", "llamaindex"): 0.65,
    ("qdrant", "pinecone"): 0.75,
    ("qdrant", "weaviate"): 0.75,
    ("qdrant", "faiss"): 0.7,
    ("aws", "gcp"): 0.5,
    ("aws", "azure"): 0.5,
    ("ci/cd", "github actions"): 0.9,
    ("rag", "semantic search"): 0.7,
    ("react", "next.js"): 0.9,
    ("rest api", "fastapi"): 0.9,
    ("docker", "containerization"): 0.9,
    ("sql", "postgresql"): 0.75,
    ("sql", "mysql"): 0.75,
    ("pytorch", "tensorflow"): 0.65,
    ("openai api", "llm"): 0.8,
    ("vector search", "semantic search"): 0.7,
}


def normalize_term(term: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9+#./ -]", " ", term.lower()).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return ALIASES.get(cleaned, cleaned)


def detect_skills(text: str) -> List[str]:
    lowered = f" {text.lower()} "
    found: Set[str] = set()
    for raw in KNOWN_SKILLS + list(ALIASES.keys()):
        term = normalize_term(raw)
        pattern = r"(?<![a-z0-9])" + re.escape(raw.lower()) + r"(?![a-z0-9])"
        if re.search(pattern, lowered):
            found.add(term)
    return sorted(found)


def best_partial_match(target: str, available: Iterable[str]) -> Tuple[str | None, float]:
    target = normalize_term(target)
    best_term = None
    best_score = 0.0
    for candidate in available:
        candidate = normalize_term(candidate)
        if candidate == target:
            return candidate, 1.0
        score = PARTIAL_SIMILARITY.get((target, candidate)) or PARTIAL_SIMILARITY.get((candidate, target)) or 0.0
        if score > best_score:
            best_term = candidate
            best_score = score
    return best_term, best_score
