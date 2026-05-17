from app.services.job_cleaner import deterministic_clean_job_description


def test_job_cleaner_keeps_candidate_requirements_and_ignores_marketing():
    text = """
    We're looking for a Junior Engineer - Python- Intern This role is Office Based
    We are looking for a Python Intern to support backend development, data processing, and automation tasks. This role is ideal for someone eager.
    In this role you will
    Develop and maintain backend services using Python
    Build and consume REST APIs
    Our Culture
    Spark Greatness. Shatter Boundaries. Share Success.
    Who We Are
    Cornerstone powers the potential of organizations and their people.
    Check us out on LinkedIn and Facebook!
    You Have What It Takes If You Have
    Strong basics in Python
    Experience with Git/version control
    """
    cleaned = deterministic_clean_job_description(text)
    kept = "\n".join(cleaned.concrete_requirements)
    ignored = "\n".join(cleaned.ignored_snippets)
    assert "Develop and maintain backend services using Python" in kept
    assert "Support backend development, data processing, and automation tasks" in kept
    assert "Build and consume REST APIs" in kept
    assert "Strong basics in Python" in kept
    assert "Experience with Git/version control" in kept
    assert "Spark Greatness" in ignored
    assert "Cornerstone powers" in ignored
    assert "LinkedIn" in ignored
    assert "Junior Engineer" in ignored
