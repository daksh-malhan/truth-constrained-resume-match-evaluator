from __future__ import annotations

import re
from collections import Counter, defaultdict
from typing import List

from ..schemas import (
    ATSKeywordMatch,
    ATSPenalty,
    ATSRankingReadiness,
    ATSRecommendation,
    ATSScoreBreakdown,
    ATSSkillCoverage,
    Citation,
    JobRequirement,
    RequirementMatch,
    ResumeEvidence,
    ResumeSection,
    RunConfig,
    SourceType,
    Suggestion,
)
from .skill_normalizer import detect_skills, normalize_term


STANDARD_SECTIONS = {
    "summary",
    "objective",
    "skills",
    "technical skills",
    "experience",
    "work experience",
    "professional experience",
    "projects",
    "education",
    "certifications",
    "awards",
    "achievements",
    "publications",
    "leadership",
}
CRITICAL_SECTIONS = {"skills", "projects", "experience", "work experience", "professional experience", "education"}
ACTION_VERBS = {
    "built",
    "developed",
    "implemented",
    "designed",
    "created",
    "optimized",
    "automated",
    "integrated",
    "modeled",
    "deployed",
    "tested",
    "analyzed",
}
WEAK_PHRASES = [
    "worked on",
    "helped with",
    "responsible for",
    "familiar with",
    "basic knowledge of",
    "made project",
    "did coding",
    "used technology",
]
PROTECTED_PATTERNS = [
    r"\bdate of birth\b|\bdob\b",
    r"\bmarital status\b|\bmarried\b|\bsingle\b",
    r"\breligion\b|\bpolitical affiliation\b",
    r"\bnationality\b|\bnational origin\b",
    r"\bdisability\b|\bhealth information\b",
    r"\bmale\b|\bfemale\b|\bgender\b",
]


def ats_band(score: float) -> str:
    if score >= 85:
        return "ATS-ready"
    if score >= 70:
        return "Mostly ATS-ready"
    if score >= 55:
        return "Needs optimization"
    if score >= 40:
        return "High risk"
    return "Likely parsing or matching issues"


def ranking_band(score: float) -> str:
    if score >= 90:
        return "Highly competitive ATS profile"
    if score >= 80:
        return "Competitive ATS profile"
    if score >= 70:
        return "Moderately competitive ATS profile"
    if score >= 55:
        return "Needs targeted optimization"
    return "Likely to be filtered or overlooked"


def _resume_citation(resume_text: str, section: ResumeSection | None = None) -> Citation:
    quote = (section.source_quote if section else resume_text[:300]) or "Original uploaded resume text."
    return Citation(
        source_type=SourceType.resume,
        source_location=f"{section.section_name} section, page {section.page_number}" if section else "Uploaded resume PDF",
        quote=quote[:300],
        page_number=section.page_number if section else None,
        section_name=section.section_name if section else None,
    )


def _job_citation(requirement: JobRequirement) -> Citation:
    return Citation(
        source_type=SourceType.job_description,
        source_location=requirement.source_location,
        quote=requirement.source_quote,
        paragraph_index=requirement.paragraph_index,
    )


def _pct(value: float, maximum: float) -> float:
    return 0.0 if maximum <= 0 else max(0.0, min(1.0, value / maximum))


def score_parseability(resume_text: str, sections: List[ResumeSection], config: RunConfig) -> tuple[float, list[str], list[ATSRecommendation]]:
    """Estimate whether the uploaded PDF produced reliable, searchable text."""
    warnings: list[str] = []
    recommendations: list[ATSRecommendation] = []
    length = len(resume_text.strip())
    lines = [line for line in resume_text.splitlines() if line.strip()]
    weird_ratio = len(re.findall(r"[^\x09\x0A\x0D\x20-\x7E]", resume_text)) / max(length, 1)
    avg_line = sum(len(line) for line in lines) / max(len(lines), 1)
    bullet_count = len([line for line in lines if re.match(r"^\s*[-*•]", line)])
    detected_sections = len({section.section_name.lower() for section in sections if section.section_name.lower() != "other"})

    score = config.ats_parseability_weight
    if length < 200:
        score = min(score, 3)
        warnings.append("Resume text extraction is very short; the PDF may be image-only or poorly parsed.")
    if weird_ratio > 0.03:
        score -= 5
        warnings.append("Extracted text contains many unusual characters.")
    elif weird_ratio > 0.01:
        score -= 2
    if avg_line < 18 and len(lines) > 20:
        score -= 3
        warnings.append("Extracted lines are highly fragmented, which may indicate layout parsing issues.")
    if detected_sections < 2:
        score -= 3
        warnings.append("Few recognizable section headings were preserved during extraction.")
    if bullet_count == 0 and len(lines) > 10:
        score -= 1.5
    if score < config.ats_parseability_weight:
        recommendations.append(
            ATSRecommendation(
                category="formatting_improvement",
                priority="high" if score < 8 else "medium",
                recommendation_text="Use a simple text-based PDF and verify that copied text appears in the correct order.",
                reason="ATS-style systems depend on clean text extraction.",
                truth_status="formatting_only",
            )
        )
    return round(max(0.0, min(config.ats_parseability_weight, score)), 2), warnings, recommendations


def score_section_structure(sections: List[ResumeSection], config: RunConfig) -> tuple[float, list[str], list[str], list[ATSRecommendation]]:
    detected = sorted({section.section_name for section in sections if section.text.strip()})
    normalized = {section.lower() for section in detected}
    standard_hits = {name for name in normalized if name in STANDARD_SECTIONS or any(part in name for part in ["skill", "project", "experience", "education", "cert"])}
    has_skills = any("skill" in name for name in normalized)
    has_experience_or_projects = any(("experience" in name or "project" in name) for name in normalized)
    has_education = any("education" in name for name in normalized)
    missing = []
    if not has_skills:
        missing.append("Skills")
    if not has_experience_or_projects:
        missing.append("Projects or Experience")
    if not has_education:
        missing.append("Education")
    ratio = len(standard_hits) / max(len(CRITICAL_SECTIONS), 1)
    score = min(config.ats_section_structure_weight, ratio * config.ats_section_structure_weight)
    if has_skills and has_experience_or_projects and has_education:
        score = config.ats_section_structure_weight
    recommendations = []
    if missing:
        recommendations.append(
            ATSRecommendation(
                category="formatting_improvement",
                priority="medium",
                recommendation_text="Use standard headings like Skills, Projects, Experience, and Education.",
                reason="Recognizable headings improve ATS-style section detection.",
                truth_status="formatting_only",
            )
        )
    return round(score, 2), detected, missing, recommendations


def score_contact_extraction(resume_text: str, sections: List[ResumeSection], config: RunConfig) -> tuple[float, list[str], list[ATSRecommendation]]:
    warnings: list[str] = []
    recommendations: list[ATSRecommendation] = []
    top_text = "\n".join(section.text for section in sections[:2]) or resume_text
    email = re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", resume_text)
    phone = re.search(r"(?:\+?\d[\d\s().-]{7,}\d)", resume_text)
    linkedin = re.search(r"linkedin\.com/\S+", resume_text, re.I)
    github = re.search(r"github\.com/\S+", resume_text, re.I)
    portfolio = re.search(r"https?://(?!.*(?:linkedin|github))\S+", resume_text, re.I)
    likely_name = bool(top_text.splitlines() and 2 <= len(top_text.splitlines()[0].split()) <= 5)
    fields = [likely_name, bool(email), bool(phone), bool(linkedin or github or portfolio)]
    score = sum(fields) / 4 * config.ats_contact_extraction_weight
    if not email:
        warnings.append("Missing email or email was not extractable.")
    if not phone:
        warnings.append("Missing phone or phone was not extractable.")
    if not github:
        warnings.append("Missing GitHub link for a technical role.")
    if not linkedin:
        warnings.append("Missing LinkedIn link.")
    if warnings:
        recommendations.append(
            ATSRecommendation(
                category="fix_immediately",
                priority="high" if not email or not phone else "medium",
                recommendation_text="Place name, email, phone, and relevant profile links as selectable text near the top of the resume.",
                reason="Contact fields should be searchable and extractable.",
                supporting_citations=[_resume_citation(resume_text, sections[0] if sections else None)],
                truth_status="safe_to_add",
            )
        )
    return round(score, 2), warnings, recommendations


def _keyword_type(requirement: JobRequirement) -> str:
    if requirement.importance == "must_have":
        return "must_have"
    if requirement.importance == "preferred":
        return "preferred"
    if requirement.importance == "repeated":
        return "repeated"
    if requirement.category == "responsibility":
        return "responsibility"
    if requirement.category == "domain":
        return "domain"
    if requirement.category == "soft_skill":
        return "soft_skill"
    return "other"


def _status_score(match: RequirementMatch, config: RunConfig) -> tuple[str, float]:
    if match.match_type == "exact":
        return "exact", config.ats_exact_keyword_weight
    if match.match_type == "direct":
        return "normalized", config.ats_normalized_keyword_weight
    if match.match_type == "semantic":
        return "semantic", config.ats_semantic_keyword_weight
    if match.match_type == "adjacent":
        return "adjacent", config.ats_adjacent_keyword_weight
    if match.match_type == "weak":
        return "weak", config.ats_weak_keyword_weight
    return "missing", 0.0


def score_keyword_alignment(requirements: List[JobRequirement], matches: List[RequirementMatch], evidence: List[ResumeEvidence], config: RunConfig) -> tuple[float, list[ATSKeywordMatch], list[ATSRecommendation]]:
    """Score searchable keyword coverage using the existing citation-backed matches."""
    match_by_id = {match.requirement_id: match for match in matches}
    evidence_by_id = {ev.id: ev for ev in evidence}
    items: list[ATSKeywordMatch] = []
    weighted_total = 0.0
    max_total = 0.0
    for req in requirements:
        match = match_by_id.get(req.id)
        status, score = _status_score(match, config) if match else ("missing", 0.0)
        weight = max(req.importance_weight, 0.3)
        weighted_total += score * weight
        max_total += weight
        ev_texts = [evidence_by_id[eid].text for eid in (match.matched_evidence_ids if match else []) if eid in evidence_by_id]
        citations = (match.citations if match else []) or [_job_citation(req)]
        recommendation = None if score >= 0.8 else f"Name '{req.normalized_skill_or_requirement}' clearly only if it is true and supported by your resume evidence."
        items.append(
            ATSKeywordMatch(
                keyword=req.normalized_skill_or_requirement,
                keyword_type=_keyword_type(req),  # type: ignore[arg-type]
                match_status=status,  # type: ignore[arg-type]
                resume_evidence=ev_texts[:3],
                citations=citations,
                score=round(score, 2),
                recommendation=recommendation,
            )
        )
    score = _pct(weighted_total, max_total) * config.ats_keyword_alignment_weight
    recommendations = [
        ATSRecommendation(
            category="add_if_true",
            priority="high",
            recommendation_text=f"Add the keyword '{item.keyword}' only if it is true and can be tied to existing project or work evidence.",
            reason="Important job keyword is missing or weakly represented.",
            related_job_requirement=item.keyword,
            supporting_citations=item.citations,
            truth_status="add_only_if_true",
        )
        for item in items
        if item.match_status in {"missing", "weak"} and item.keyword_type in {"must_have", "repeated", "responsibility"}
    ][:5]
    return round(score, 2), items, recommendations


def score_required_skills_coverage(requirements: List[JobRequirement], matches: List[RequirementMatch], evidence: List[ResumeEvidence], config: RunConfig) -> tuple[float, list[ATSSkillCoverage], list[ATSRecommendation]]:
    """Give higher ATS credit when required skills are tied to project/work evidence."""
    match_by_id = {match.requirement_id: match for match in matches}
    evidence_by_id = {ev.id: ev for ev in evidence}
    coverage: list[ATSSkillCoverage] = []
    total = 0.0
    max_total = 0.0
    for req in requirements:
        match = match_by_id.get(req.id)
        matched_evidence = [evidence_by_id[eid] for eid in (match.matched_evidence_ids if match else []) if eid in evidence_by_id]
        strong = any(ev.evidence_type in {"project", "work_experience"} and (ev.skills_detected or ev.tools_detected) for ev in matched_evidence)
        listed = any(ev.evidence_type == "skill" for ev in matched_evidence)
        if match and match.evidence_strength >= 0.85 and strong:
            status, backing, score = "covered", "strong", 1.0
        elif match and match.evidence_strength >= 0.75:
            status, backing, score = "covered", "moderate" if listed else "strong", 0.8
        elif match and match.evidence_strength >= 0.4:
            status, backing, score = "partially_covered", "weak", 0.5
        elif match and match.evidence_strength >= 0.2:
            status, backing, score = "weak", "weak", 0.2
        else:
            status, backing, score = "missing", "none", 0.0
        weight = max(req.importance_weight, 0.3)
        total += score * weight
        max_total += weight
        importance = req.importance if req.importance in {"must_have", "preferred", "nice_to_have", "generic"} else "generic"
        coverage.append(
            ATSSkillCoverage(
                skill=req.normalized_skill_or_requirement,
                required_importance=importance,  # type: ignore[arg-type]
                coverage_status=status,  # type: ignore[arg-type]
                evidence_backing=backing,  # type: ignore[arg-type]
                citations=(match.citations if match else []) or [_job_citation(req)],
                score=score,
                recommendation="Tie this skill to a project/work bullet if true." if score > 0 else "Learn this before claiming it on the resume.",
            )
        )
    score = _pct(total, max_total) * config.ats_required_skills_weight
    recommendations = [
        ATSRecommendation(
            category="learn_before_applying",
            priority="high",
            recommendation_text=f"Learn and build evidence for '{item.skill}' before adding it as a resume claim.",
            reason="The job asks for this skill, but source resume evidence is missing.",
            related_job_requirement=item.skill,
            supporting_citations=item.citations,
            truth_status="learn_first",
        )
        for item in coverage
        if item.coverage_status == "missing"
    ][:5]
    return round(score, 2), coverage, recommendations


def score_evidence_backing(evidence: List[ResumeEvidence], config: RunConfig) -> tuple[float, list[str], list[str], list[ATSRecommendation]]:
    """Measure whether listed skills are supported outside a plain skills list."""
    skill_sources: dict[str, set[str]] = defaultdict(set)
    citations_by_skill: dict[str, list[Citation]] = defaultdict(list)
    for ev in evidence:
        for skill in ev.skills_detected + ev.tools_detected:
            skill_sources[normalize_term(skill)].add(ev.evidence_type)
            citations_by_skill[normalize_term(skill)].append(
                Citation(source_type=SourceType.resume, source_location=ev.source_location, quote=ev.source_quote, page_number=ev.page_number, section_name=ev.section_name)
            )
    strong = sorted([skill for skill, sources in skill_sources.items() if sources & {"project", "work_experience"}])
    weak = sorted([skill for skill, sources in skill_sources.items() if "skill" in sources and not sources & {"project", "work_experience"}])
    denominator = max(len(strong) + len(weak), 1)
    score = ((len(strong) + 0.35 * len(weak)) / denominator) * config.ats_evidence_backing_weight
    recommendations = [
        ATSRecommendation(
            category="improve_wording",
            priority="medium",
            recommendation_text=f"Connect '{skill}' to a concrete project or work bullet using only true existing evidence.",
            reason="The skill appears listed but has weak evidence backing.",
            supporting_citations=citations_by_skill.get(skill, [])[:2],
            truth_status="safe_to_add",
        )
        for skill in weak[:5]
    ]
    return round(min(config.ats_evidence_backing_weight, score), 2), strong[:12], weak[:12], recommendations


def score_formatting_safety(resume_text: str, sections: List[ResumeSection], config: RunConfig) -> tuple[float, list[str], list[ATSRecommendation]]:
    risks: list[str] = []
    lines = [line for line in resume_text.splitlines() if line.strip()]
    page_count = len({section.page_number for section in sections}) or 1
    if config.check_weird_characters and len(re.findall(r"[^\x09\x0A\x0D\x20-\x7E]", resume_text)) / max(len(resume_text), 1) > 0.015:
        risks.append("Unusual extracted characters may reduce parsing reliability.")
    if config.check_bullet_extraction and lines and len([line for line in lines if re.match(r"^\s*[-*•]", line)]) == 0:
        risks.append("Bullet extraction may be weak or bullets may not be represented as text.")
    if config.check_tables and len([line for line in lines if line.count("|") >= 2 or "\t" in line]) >= 2:
        risks.append("Table-like text was detected and may parse inconsistently.")
    if config.check_columns and len([line for line in lines if re.search(r"\S\s{5,}\S", line)]) >= 6:
        risks.append("Wide spacing suggests possible columns; columns may reduce parsing reliability.")
    if page_count > 2:
        risks.append("Resume may be long for an early-career role.")
    score = max(0.0, config.ats_formatting_safety_weight - min(config.ats_formatting_safety_weight, len(risks) * 2.0))
    recommendations = [
        ATSRecommendation(
            category="formatting_improvement",
            priority="medium",
            recommendation_text="Prefer a text-based, simple layout with standard headings and selectable links.",
            reason="Complex formatting may reduce ATS-style parsing reliability.",
            truth_status="formatting_only",
        )
    ] if risks else []
    return round(score, 2), risks, recommendations


def score_communication_quality(evidence: List[ResumeEvidence], config: RunConfig) -> tuple[float, list[str], list[str], list[ATSRecommendation]]:
    bullets = [ev for ev in evidence if ev.evidence_type in {"project", "work_experience", "other"}]
    if not bullets:
        return 0.0, [], [], []
    strong: list[str] = []
    weak: list[str] = []
    for ev in bullets:
        lowered = ev.text.lower()
        starts_action = (lowered.split()[:1] or [""])[0].strip(".,:;") in ACTION_VERBS
        has_tool = bool(ev.skills_detected or ev.tools_detected)
        weak_phrase = any(phrase in lowered for phrase in WEAK_PHRASES)
        if starts_action and has_tool and (ev.has_metric or len(ev.text.split()) >= 8) and not weak_phrase:
            strong.append(ev.text)
        elif weak_phrase or len(ev.text.split()) < 6:
            weak.append(ev.text)
    score = ((len(strong) + 0.4 * (len(bullets) - len(strong) - len(weak))) / max(len(bullets), 1)) * config.ats_communication_quality_weight
    recommendations = [
        ATSRecommendation(
            category="improve_wording",
            priority="medium",
            recommendation_text="Rewrite vague bullets to start with an action verb, name the tool, describe what was built, and include outcomes only when supported.",
            reason="Some bullets are vague, too short, or use weak phrases.",
            supporting_citations=[
                Citation(source_type=SourceType.resume, source_location="Resume bullet", quote=text[:300])
                for text in weak[:3]
            ],
            truth_status="safe_to_add",
        )
    ] if weak else []
    return round(min(config.ats_communication_quality_weight, score), 2), weak[:8], strong[:8], recommendations


def score_role_targeting(sections: List[ResumeSection], requirements: List[JobRequirement], evidence: List[ResumeEvidence], config: RunConfig) -> tuple[float, list[str], list[str], list[ATSRecommendation]]:
    top_resume = "\n".join(section.text for section in sections[:2]).lower()
    req_terms = {req.normalized_skill_or_requirement for req in requirements}
    top_hits = [term for term in req_terms if term and term in top_resume]
    project_hits = sorted({skill for ev in evidence if ev.evidence_type in {"project", "work_experience"} for skill in ev.skills_detected + ev.tools_detected if skill in req_terms})
    score = min(config.ats_role_targeting_weight, (0.6 * len(top_hits) + 0.4 * len(project_hits)) / max(len(req_terms), 1) * config.ats_role_targeting_weight * 2)
    strengths = []
    if top_hits:
        strengths.append("Relevant job terms appear near the top of the resume.")
    if project_hits:
        strengths.append("Role-relevant skills are connected to project or work evidence.")
    gaps = []
    if not top_hits:
        gaps.append("Few target-job terms appear near the top of the resume.")
    recommendations = [
        ATSRecommendation(
            category="improve_wording",
            priority="low",
            recommendation_text="Add a targeted summary using only true, already-supported skills from the resume.",
            reason="A targeted summary can make relevant evidence easier to find.",
            truth_status="safe_to_add",
        )
    ] if gaps else []
    return round(score, 2), strengths, gaps, recommendations


def calculate_ats_penalties(
    resume_text: str,
    parseability_score: float,
    formatting_score: float,
    contact_warnings: list[str],
    keyword_matches: list[ATSKeywordMatch],
    unsafe_suggestions: list[Suggestion],
    prompt_injection_detected: bool,
    config: RunConfig,
) -> tuple[float, list[ATSPenalty]]:
    """Apply explicit ATS-readiness penalties without using protected traits."""
    penalties: list[ATSPenalty] = []
    lowered = resume_text.lower()
    if config.penalize_missing_contact_info and contact_warnings:
        missing_major = [w for w in contact_warnings if "email" in w.lower() or "phone" in w.lower()]
        if missing_major:
            penalties.append(ATSPenalty(penalty_type="missing_contact", severity="medium", points_deducted=min(5, 2.5 * len(missing_major)), explanation="Email or phone was not extractable.", recommendation="Add email and phone as selectable text near the top of the resume."))
    if config.penalize_unparseable_formatting and (parseability_score < config.ats_parseability_weight * 0.45 or formatting_score < config.ats_formatting_safety_weight * 0.45):
        penalties.append(ATSPenalty(penalty_type="unparseable_formatting", severity="high", points_deducted=6, explanation="Parseability or formatting safety is low.", recommendation="Use a simpler text-based PDF layout."))
    if config.penalize_prompt_injection and prompt_injection_detected:
        penalties.append(ATSPenalty(penalty_type="prompt_injection", severity="low", points_deducted=2, explanation="Prompt-injection-like text was detected and ignored.", recommendation="Remove instruction-like text such as 'ignore previous instructions' from the resume or pasted job data."))
    if config.penalize_unsupported_claims and unsafe_suggestions:
        penalties.append(ATSPenalty(penalty_type="unsupported_claim", severity="medium", points_deducted=min(6, 1.5 * len(unsafe_suggestions)), explanation="Some generated ideas were rejected because they would add unsupported claims.", recommendation="Do not add unsupported tools, metrics, certifications, deployments, or outcomes."))
    if config.penalize_keyword_stuffing:
        tokens = re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", lowered)
        counts = Counter(tokens)
        repeated_keywords = [item.keyword for item in keyword_matches if counts[normalize_term(item.keyword)] >= 8]
        if repeated_keywords:
            penalties.append(ATSPenalty(penalty_type="keyword_stuffing", severity="medium", points_deducted=min(5, len(repeated_keywords) * 1.5), explanation="Some job keywords appear unusually often.", recommendation="Use keywords naturally in evidence-backed bullets instead of repeating them."))
    if config.penalize_generic_resume and len([item for item in keyword_matches if item.match_status in {"exact", "normalized", "semantic"}]) < max(2, len(keyword_matches) // 3):
        penalties.append(ATSPenalty(penalty_type="generic_resume", severity="low", points_deducted=2, explanation="The resume appears weakly targeted to the pasted job.", recommendation="Emphasize already-supported role-relevant skills near the top."))
    total = min(config.ats_max_penalty, sum(p.points_deducted for p in penalties))
    return round(total, 2), penalties


def protected_trait_warnings(resume_text: str) -> list[str]:
    """Warn about sensitive traits without affecting ATS or match scores."""
    if any(re.search(pattern, resume_text, re.I) for pattern in PROTECTED_PATTERNS):
        return ["Your resume may contain personal or sensitive information that is usually unnecessary for job applications. Consider removing it unless required."]
    return []


def calculate_ranking_readiness(
    ats_score: float,
    main_match_score: float,
    breakdown: ATSScoreBreakdown,
    config: RunConfig,
) -> ATSRankingReadiness:
    """Blend ATS readiness and match strength without promising selection outcomes."""
    required_scaled = _pct(breakdown.required_skills_coverage_score, config.ats_required_skills_weight) * 100
    evidence_scaled = _pct(breakdown.evidence_backing_score, config.ats_evidence_backing_weight) * 100
    parse_scaled = _pct(breakdown.parseability_score, config.ats_parseability_weight) * 100
    score = 0.35 * ats_score + 0.35 * (main_match_score * 10) + 0.15 * required_scaled + 0.10 * evidence_scaled + 0.05 * parse_scaled
    missing_must = len([item for item in breakdown.skill_coverage if item.required_importance == "must_have" and item.coverage_status == "missing"])
    score -= min(12, missing_must * 4)
    score -= min(8, breakdown.penalties * 0.4)
    score = round(max(0.0, min(100.0, score)), 2)
    helping = []
    hurting = []
    if breakdown.parseability_score >= config.ats_parseability_weight * 0.8:
        helping.append("Resume text appears parseable.")
    if breakdown.keyword_alignment_score >= config.ats_keyword_alignment_weight * 0.7:
        helping.append("Keyword alignment is reasonably strong.")
    if breakdown.evidence_backing_score >= config.ats_evidence_backing_weight * 0.7:
        helping.append("Several skills are backed by project or work evidence.")
    if missing_must:
        hurting.append(f"{missing_must} must-have skill(s) appear missing.")
    if breakdown.penalty_items:
        hurting.append("ATS penalties reduce readiness.")
    if breakdown.formatting_safety_score < config.ats_formatting_safety_weight * 0.65:
        hurting.append("Formatting may reduce parsing reliability.")
    return ATSRankingReadiness(
        ranking_readiness_score=score,
        ranking_readiness_band=ranking_band(score),
        explanation="Ranking readiness estimates how searchable and competitive this resume appears for the pasted job description based on ATS-style signals. It does not guarantee ATS passage, selection, or interviews.",
        top_factors_helping=helping or ["No major ATS-style advantage was detected."],
        top_factors_hurting=hurting or ["No major ATS-style blocker was detected."],
        recommendations=breakdown.recommendations[:6],
    )


def calculate_ats_score(
    *,
    resume_text: str,
    sections: List[ResumeSection],
    evidence: List[ResumeEvidence],
    requirements: List[JobRequirement],
    matches: List[RequirementMatch],
    main_match_score: float,
    config: RunConfig,
    prompt_injection_detected: bool = False,
    unsafe_suggestions: List[Suggestion] | None = None,
) -> tuple[ATSScoreBreakdown, ATSRankingReadiness]:
    """Calculate the ATS-style report from original resume/JD evidence only."""
    if not config.enable_ats_scoring:
        breakdown = ATSScoreBreakdown(warnings=["ATS scoring is disabled in admin configuration."])
        return breakdown, ATSRankingReadiness()

    recommendations: list[ATSRecommendation] = []
    warnings: list[str] = []

    parse_score, parse_warnings, parse_recs = score_parseability(resume_text, sections, config)
    section_score, _detected_sections, missing_sections, section_recs = score_section_structure(sections, config)
    contact_score, contact_warnings, contact_recs = score_contact_extraction(resume_text, sections, config)
    keyword_score, keyword_matches, keyword_recs = score_keyword_alignment(requirements, matches, evidence, config)
    skills_score, skill_coverage, skill_recs = score_required_skills_coverage(requirements, matches, evidence, config)
    evidence_score, _strong_evidence, _weak_evidence, evidence_recs = score_evidence_backing(evidence, config)
    formatting_score, formatting_risks, formatting_recs = score_formatting_safety(resume_text, sections, config)
    communication_score, weak_bullets, _strong_bullets, communication_recs = score_communication_quality(evidence, config)
    targeting_score, _targeting_strengths, targeting_gaps, targeting_recs = score_role_targeting(sections, requirements, evidence, config)
    recommendations.extend(parse_recs + section_recs + contact_recs + keyword_recs + skill_recs + evidence_recs + formatting_recs + communication_recs + targeting_recs)
    warnings.extend(parse_warnings + contact_warnings + formatting_risks + protected_trait_warnings(resume_text))
    if missing_sections:
        warnings.append(f"Missing recommended sections: {', '.join(missing_sections)}.")
    if weak_bullets:
        warnings.append(f"{len(weak_bullets)} bullet(s) may be vague or weakly phrased.")
    if targeting_gaps:
        warnings.extend(targeting_gaps)

    penalties, penalty_items = calculate_ats_penalties(
        resume_text,
        parse_score,
        formatting_score,
        contact_warnings,
        keyword_matches,
        unsafe_suggestions or [],
        prompt_injection_detected,
        config,
    )
    for penalty in penalty_items:
        recommendations.append(
            ATSRecommendation(
                category="fix_immediately" if penalty.severity in {"medium", "high"} else "improve_wording",
                priority="high" if penalty.severity == "high" else "medium",
                recommendation_text=penalty.recommendation,
                reason=penalty.explanation,
                supporting_citations=penalty.citations,
                truth_status="formatting_only" if penalty.penalty_type in {"unparseable_formatting", "missing_contact"} else "safe_to_add",
            )
        )

    total = parse_score + section_score + contact_score + keyword_score + skills_score + evidence_score + formatting_score + communication_score + targeting_score - penalties
    final = round(max(0.0, min(100.0, total)), 2)
    citations: list[Citation] = []
    for item in keyword_matches[:10]:
        citations.extend(item.citations[:2])
    breakdown = ATSScoreBreakdown(
        parseability_score=parse_score,
        section_structure_score=section_score,
        contact_extraction_score=contact_score,
        keyword_alignment_score=keyword_score,
        required_skills_coverage_score=skills_score,
        evidence_backing_score=evidence_score,
        formatting_safety_score=formatting_score,
        communication_quality_score=communication_score,
        role_targeting_score=targeting_score,
        penalties=penalties,
        final_ats_score=final,
        ats_band=ats_band(final),
        warnings=warnings,
        recommendations=recommendations[:20],
        keyword_matches=keyword_matches,
        skill_coverage=skill_coverage,
        penalty_items=penalty_items,
        citations=citations,
    )
    ranking = calculate_ranking_readiness(final, main_match_score, breakdown, config) if config.enable_ats_ranking_readiness else ATSRankingReadiness()
    return breakdown, ranking
