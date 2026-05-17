from __future__ import annotations

import json
import os
import re
from typing import List, Tuple

import httpx
from pydantic import BaseModel, Field

from ..config import ollama_base_url
from .job_parser import parse_job_paragraphs


class CleanedJobDescription(BaseModel):
    concrete_requirements: List[str] = Field(default_factory=list)
    ignored_snippets: List[str] = Field(default_factory=list)
    used_llm: bool = False
    warning: str | None = None

    @property
    def cleaned_text(self) -> str:
        return "\n".join(f"- {item}" for item in self.concrete_requirements)


KEEP_PATTERNS = [
    "develop", "maintain", "backend", "python", "rest api", "apis", "etl", "data processing",
    "automation", "optimization", "debug", "performance", "collaborate", "oop", "object oriented",
    "data structures", "algorithms", "git", "version control", "scripts", "services", "pipelines",
]

IGNORE_PATTERNS = [
    "our culture", "who we are", "spark greatness", "shatter boundaries", "share success",
    "cornerstone powers", "cornerstone galaxy", "organizations", "customers", "communities",
    "linkedin", "comparably", "glassdoor", "facebook", "check us out", "equal opportunity",
    "benefits", "future of work", "100 million", "7,000", "180+ countries",
]

HEADING_PATTERNS = {
    "in this role you will",
    "you have what it takes if you have",
    "our culture",
    "who we are",
}


def _clean_line(text: str) -> str:
    text = text.strip(" \t\r\n-•")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def deterministic_clean_job_description(job_description_text: str) -> CleanedJobDescription:
    kept: List[str] = []
    ignored: List[str] = []
    for paragraph in parse_job_paragraphs(job_description_text):
        for raw_line in paragraph.splitlines() or [paragraph]:
            line = _clean_line(raw_line)
            if not line:
                continue
            lowered = line.lower().rstrip(":")
            if lowered.startswith("we're looking for") or lowered.startswith("we are looking for"):
                if " to support " in lowered:
                    line = re.sub(r"^we are looking for .*? to support ", "Support ", line, flags=re.IGNORECASE)
                    line = re.split(r"\bThis role is ideal\b", line, flags=re.IGNORECASE)[0].strip(" .")
                    lowered = line.lower()
                else:
                    ignored.append(line)
                    continue
            if lowered in HEADING_PATTERNS or len(line.split()) <= 2:
                ignored.append(line)
                continue
            if any(pattern in lowered for pattern in IGNORE_PATTERNS):
                ignored.append(line)
                continue
            if any(pattern in lowered for pattern in KEEP_PATTERNS):
                if line not in kept:
                    kept.append(line)
            else:
                ignored.append(line)
    return CleanedJobDescription(concrete_requirements=kept, ignored_snippets=ignored, used_llm=False)


def llm_clean_job_description(job_description_text: str) -> CleanedJobDescription:
    model = os.getenv("OLLAMA_JD_CLEANER_MODEL", "resume-jd-cleaner:latest")
    timeout = float(os.getenv("OLLAMA_JD_CLEANER_TIMEOUT_SECONDS", "12"))
    max_tokens = int(os.getenv("OLLAMA_JD_CLEANER_NUM_PREDICT", "450"))
    response = httpx.post(
        f"{ollama_base_url()}/api/chat",
        json={
            "model": model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0, "num_predict": max_tokens},
            "messages": [
                {"role": "user", "content": job_description_text},
            ],
        },
        timeout=timeout,
    )
    response.raise_for_status()
    content = response.json().get("message", {}).get("content", "{}")
    cleaned = CleanedJobDescription.model_validate_json(content)
    cleaned.used_llm = True
    return cleaned


def clean_job_description(job_description_text: str) -> CleanedJobDescription:
    if os.getenv("ENABLE_JD_CLEANER_LLM", "true").lower() in {"1", "true", "yes", "on"} and os.getenv("LLM_PROVIDER", "mock").lower() == "ollama":
        try:
            cleaned = llm_clean_job_description(job_description_text)
            if cleaned.concrete_requirements:
                return cleaned
        except Exception as exc:
            fallback = deterministic_clean_job_description(job_description_text)
            fallback.warning = f"JD cleaner LLM failed; deterministic cleaner used: {exc}"
            return fallback
    fallback = deterministic_clean_job_description(job_description_text)
    if not fallback.concrete_requirements:
        fallback.warning = "No concrete candidate requirements were extracted; downstream extraction will use the original job description."
    return fallback
