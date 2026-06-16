from __future__ import annotations

from typing import List

from .harness import EvalCase


# A small benchmark of (resume, job description) pairs with the tools a competent
# coach should call. Kept compact and source-grounded so runs stay fast and the
# truth constraint is exercised (each resume omits some required skill).
BENCHMARK_CASES: List[EvalCase] = [
    EvalCase(
        name="backend_python_intern",
        resume=(
            "PROJECTS\n"
            "Built a FastAPI service in Python with pytest coverage and a SQLite backend.\n"
            "Created a Dockerized REST API that processes JSON records and logs progress.\n"
            "SKILLS\nPython, FastAPI, Docker, SQL, Git"
        ),
        job_description=(
            "Backend Engineer Intern\n"
            "Required: strong Python and REST API development. Must have Docker and SQL.\n"
            "Preferred: Kubernetes orchestration and AWS deployment."
        ),
        target_role="Backend Engineer Intern",
        expected_tools={"score_resume", "find_gaps", "rewrite_bullet"},
    ),
    EvalCase(
        name="data_analyst",
        resume=(
            "EXPERIENCE\n"
            "Analyzed sales data in SQL and Excel and built weekly reporting dashboards.\n"
            "Wrote Python scripts to clean CSV data and compute summary statistics.\n"
            "SKILLS\nSQL, Excel, Python, pandas"
        ),
        job_description=(
            "Data Analyst\n"
            "Required: SQL and data visualization. Experience with statistics.\n"
            "Preferred: Tableau and A/B testing."
        ),
        target_role="Data Analyst",
        expected_tools={"score_resume", "find_gaps"},
    ),
    EvalCase(
        name="frontend_react",
        resume=(
            "PROJECTS\n"
            "Built a responsive React app in TypeScript with reusable components.\n"
            "Styled interfaces with CSS and added unit tests with Jest.\n"
            "SKILLS\nReact, TypeScript, CSS, Jest, Git"
        ),
        job_description=(
            "Frontend Engineer\n"
            "Required: React and TypeScript. Must write component tests.\n"
            "Preferred: Next.js and accessibility experience."
        ),
        target_role="Frontend Engineer",
        expected_tools={"score_resume", "find_gaps", "rewrite_bullet"},
    ),
    EvalCase(
        name="ml_intern",
        resume=(
            "PROJECTS\n"
            "Trained a scikit-learn classifier in Python on a tabular dataset with pandas.\n"
            "Evaluated models with cross-validation and reported accuracy.\n"
            "SKILLS\nPython, pandas, scikit-learn, NumPy"
        ),
        job_description=(
            "Machine Learning Intern\n"
            "Required: Python and machine learning fundamentals.\n"
            "Preferred: PyTorch, NLP, and cloud deployment."
        ),
        target_role="Machine Learning Intern",
        expected_tools={"score_resume", "find_gaps"},
    ),
    EvalCase(
        name="strong_match_backend",
        resume=(
            "EXPERIENCE\n"
            "Developed Python REST APIs with FastAPI, containerized with Docker, backed by SQL.\n"
            "Wrote pytest suites and used Git for version control on a team project.\n"
            "SKILLS\nPython, FastAPI, REST, Docker, SQL, Git, pytest"
        ),
        job_description=(
            "Backend Engineer\n"
            "Required: Python, REST API development, Docker, and SQL.\n"
            "Nice to have: pytest and Git workflow."
        ),
        target_role="Backend Engineer",
        expected_tools={"score_resume", "find_gaps"},
    ),
]
