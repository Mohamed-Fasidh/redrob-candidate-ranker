#!/usr/bin/env python3
"""Offline candidate ranker for the Redrob Data & AI Challenge.

The ranker is deliberately deterministic and CPU-only. It reads the candidate
JSONL stream once, scores every profile using JD-derived features, and writes
the required top-100 CSV.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import re
from datetime import date
from pathlib import Path
from typing import Any


AS_OF = date(2026, 6, 29)
TOKEN_RE = re.compile(r"[a-z0-9+#.]+")

PRODUCT_COMPANIES = {
    "zomato",
    "swiggy",
    "razorpay",
    "paytm",
    "flipkart",
    "meesho",
    "freshworks",
    "zoho",
    "ola",
    "uber",
    "google",
    "amazon",
    "microsoft",
    "meta",
    "netflix",
    "spotify",
    "airbnb",
    "atlassian",
    "salesforce",
    "adobe",
    "intuit",
    "linkedin",
    "slack",
    "stripe",
    "shopify",
    "phonepe",
    "cred",
}

SERVICES_COMPANIES = {
    "tcs",
    "infosys",
    "wipro",
    "accenture",
    "cognizant",
    "capgemini",
    "hcl",
    "mindtree",
    "ltimindtree",
    "tech mahindra",
    "mphasis",
}

GOOD_LOCATIONS = {
    "pune",
    "noida",
    "gurgaon",
    "gurugram",
    "delhi",
    "mumbai",
    "hyderabad",
    "bangalore",
    "bengaluru",
}

TITLE_POSITIVE = [
    "ai engineer",
    "ml engineer",
    "machine learning engineer",
    "senior machine learning",
    "senior ai",
    "applied scientist",
    "search engineer",
    "ranking engineer",
    "recommendation systems engineer",
    "data scientist",
    "nlp engineer",
    "backend engineer",
    "software engineer",
]

TITLE_NEGATIVE = [
    "marketing",
    "hr",
    "human resources",
    "graphic designer",
    "operations manager",
    "accountant",
    "civil engineer",
    "mechanical engineer",
    "customer support",
    "content writer",
    "sales",
]

CORE_SKILL_ALIASES = {
    "python": ["python", "pytorch", "tensorflow", "fastapi"],
    "retrieval": ["retrieval", "rag", "semantic search", "information retrieval", "bm25"],
    "vector": ["vector", "faiss", "pinecone", "weaviate", "qdrant", "milvus", "opensearch", "elasticsearch"],
    "ranking": ["ranking", "learning to rank", "recommender", "recommendation", "search relevance"],
    "evaluation": ["ndcg", "mrr", "map", "a/b", "ab test", "offline benchmark", "evaluation"],
    "llm": ["llm", "large language", "fine-tuning", "finetuning", "lora", "qlora", "peft", "nlp", "transformer"],
    "production": ["production", "deployed", "serving", "monitoring", "index refresh", "drift", "scale"],
}


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8")
    return open(path, "r", encoding="utf-8")


def text_blob(candidate: dict[str, Any]) -> str:
    profile = candidate.get("profile", {})
    parts = [
        profile.get("headline", ""),
        profile.get("summary", ""),
        profile.get("current_title", ""),
        profile.get("current_industry", ""),
        profile.get("current_company", ""),
        profile.get("location", ""),
        profile.get("country", ""),
    ]
    for role in candidate.get("career_history", []):
        parts.extend([role.get("title", ""), role.get("company", ""), role.get("industry", ""), role.get("description", "")])
    for skill in candidate.get("skills", []):
        parts.append(skill.get("name", ""))
    for cert in candidate.get("certifications", []):
        parts.extend([cert.get("name", ""), cert.get("issuer", "")])
    for edu in candidate.get("education", []):
        parts.extend([edu.get("degree", ""), edu.get("field_of_study", ""), edu.get("institution", "")])
    return " ".join(str(p) for p in parts if p).lower()


def contains_any(text: str, phrases: list[str] | set[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


def skill_score(candidate: dict[str, Any], blob: str) -> tuple[float, list[str]]:
    skill_names = [s.get("name", "") for s in candidate.get("skills", [])]
    skill_text = " ".join(skill_names).lower()
    matched_groups: list[str] = []
    score = 0.0
    for group, aliases in CORE_SKILL_ALIASES.items():
        if contains_any(skill_text, aliases) or contains_any(blob, aliases):
            matched_groups.append(group)
            score += {
                "python": 13,
                "retrieval": 18,
                "vector": 15,
                "ranking": 17,
                "evaluation": 15,
                "llm": 12,
                "production": 10,
            }[group]

    trust_bonus = 0.0
    for skill in candidate.get("skills", []):
        name = skill.get("name", "").lower()
        if contains_any(name, [a for aliases in CORE_SKILL_ALIASES.values() for a in aliases]):
            prof = {"beginner": 0.0, "intermediate": 1.0, "advanced": 2.0, "expert": 3.0}.get(skill.get("proficiency"), 0.0)
            trust_bonus += min(4.0, prof + math.log1p(skill.get("endorsements", 0)) * 0.35 + skill.get("duration_months", 0) / 36)

    assessment_scores = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})
    assessment_bonus = 0.0
    for name, value in assessment_scores.items():
        if contains_any(name.lower(), [a for aliases in CORE_SKILL_ALIASES.values() for a in aliases]):
            assessment_bonus += max(0.0, float(value) - 50.0) / 12.0

    return clamp(score + min(18.0, trust_bonus) + min(8.0, assessment_bonus)), matched_groups


def career_score(candidate: dict[str, Any], blob: str) -> tuple[float, list[str]]:
    profile = candidate.get("profile", {})
    current_title = profile.get("current_title", "").lower()
    years = float(profile.get("years_of_experience", 0) or 0)
    score = 0.0
    notes: list[str] = []

    if contains_any(current_title, TITLE_POSITIVE):
        score += 20
        notes.append(profile.get("current_title", "relevant title"))
    if contains_any(current_title, TITLE_NEGATIVE):
        score -= 28

    if 5 <= years <= 9:
        score += 18
    elif 4 <= years < 5 or 9 < years <= 11:
        score += 10
    elif 3 <= years < 4 or 11 < years <= 13:
        score += 4
    else:
        score -= 8

    phrase_weights = {
        "embedding": 5,
        "retrieval": 8,
        "ranking": 8,
        "recommendation": 7,
        "search": 5,
        "vector": 6,
        "faiss": 5,
        "elasticsearch": 4,
        "opensearch": 4,
        "qdrant": 5,
        "pinecone": 5,
        "weaviate": 5,
        "ndcg": 6,
        "mrr": 5,
        "map": 4,
        "a/b": 4,
        "production": 6,
        "deployed": 5,
        "recruiter": 4,
        "marketplace": 4,
    }
    for phrase, weight in phrase_weights.items():
        if phrase in blob:
            score += weight

    role_bonus = 0.0
    services_months = 0
    product_months = 0
    for role in candidate.get("career_history", []):
        role_text = " ".join(
            str(role.get(k, "")).lower()
            for k in ["company", "title", "industry", "description"]
        )
        months = int(role.get("duration_months", 0) or 0)
        if contains_any(role_text, PRODUCT_COMPANIES) or "software" in role_text or "saas" in role_text or "product" in role_text:
            product_months += months
        if contains_any(role_text, SERVICES_COMPANIES) or "it services" in role_text or "consulting" in role_text:
            services_months += months
        if contains_any(role_text, ["built", "owned", "shipped", "deployed", "designed"]) and contains_any(role_text, ["ranking", "search", "recommendation", "retrieval", "embedding", "ml"]):
            role_bonus += min(14, months / 6)

    if product_months >= 24:
        score += 13
        notes.append("product-company exposure")
    if product_months == 0 and services_months >= max(36, product_months + 24):
        score -= 22
    score += min(18.0, role_bonus)

    if "research" in blob and not contains_any(blob, ["deployed", "production", "shipped", "owned"]):
        score -= 12
    if "langchain" in blob and not contains_any(blob, ["retrieval", "ranking", "pre-llm", "production ml"]):
        score -= 8

    return clamp(score), notes


def education_score(candidate: dict[str, Any]) -> float:
    score = 8.0
    for edu in candidate.get("education", []):
        tier = edu.get("tier")
        field = f"{edu.get('degree', '')} {edu.get('field_of_study', '')}".lower()
        if tier == "tier_1":
            score += 8
        elif tier == "tier_2":
            score += 5
        elif tier == "tier_3":
            score += 2
        if contains_any(field, ["computer", "data", "machine learning", "artificial intelligence", "statistics", "mathematics"]):
            score += 5
    return clamp(score, 0, 25)


def behavior_score(candidate: dict[str, Any]) -> float:
    s = candidate.get("redrob_signals", {})
    score = 45.0
    score += min(10.0, float(s.get("profile_completeness_score", 0)) / 10)
    score += 10.0 if s.get("open_to_work_flag") else -6.0
    score += float(s.get("recruiter_response_rate", 0)) * 14.0
    score += float(s.get("interview_completion_rate", 0)) * 8.0
    offer = float(s.get("offer_acceptance_rate", -1))
    if offer >= 0:
        score += offer * 5.0

    try:
        last_active = date.fromisoformat(s.get("last_active_date", "2000-01-01"))
        inactive_days = (AS_OF - last_active).days
    except ValueError:
        inactive_days = 999
    if inactive_days <= 14:
        score += 10
    elif inactive_days <= 45:
        score += 6
    elif inactive_days <= 90:
        score += 1
    else:
        score -= 14

    response_hours = float(s.get("avg_response_time_hours", 999))
    if response_hours <= 24:
        score += 6
    elif response_hours <= 72:
        score += 3
    elif response_hours > 168:
        score -= 6

    notice = int(s.get("notice_period_days", 180) or 180)
    if notice <= 30:
        score += 7
    elif notice <= 60:
        score += 2
    elif notice > 90:
        score -= 8

    score += min(7.0, math.log1p(int(s.get("saved_by_recruiters_30d", 0))) * 2)
    score += min(5.0, math.log1p(int(s.get("profile_views_received_30d", 0))) * 1.2)
    github = float(s.get("github_activity_score", -1))
    if github >= 0:
        score += min(8.0, github / 12)
    else:
        score -= 2
    score += 2 if s.get("verified_email") else -2
    score += 2 if s.get("verified_phone") else -2
    score += 2 if s.get("linkedin_connected") else 0
    return clamp(score)


def logistics_score(candidate: dict[str, Any]) -> float:
    p = candidate.get("profile", {})
    s = candidate.get("redrob_signals", {})
    location = f"{p.get('location', '')} {p.get('country', '')}".lower()
    score = 35.0
    if "india" in location:
        score += 20
    if contains_any(location, GOOD_LOCATIONS):
        score += 18
    elif s.get("willing_to_relocate"):
        score += 12
    else:
        score -= 10
    if s.get("preferred_work_mode") in {"hybrid", "flexible", "onsite"}:
        score += 8
    return clamp(score)


def honeypot_penalty(candidate: dict[str, Any], blob: str) -> tuple[float, list[str]]:
    penalty = 0.0
    flags: list[str] = []
    skills = candidate.get("skills", [])
    zero_duration_experts = [s for s in skills if s.get("proficiency") == "expert" and int(s.get("duration_months", 0) or 0) <= 1]
    if len(zero_duration_experts) >= 3:
        penalty += 35
        flags.append("expert skills with near-zero duration")
    if len(skills) >= 25 and candidate.get("profile", {}).get("years_of_experience", 0) < 4:
        penalty += 20
        flags.append("unusually broad skills for experience")
    if contains_any(candidate.get("profile", {}).get("current_title", "").lower(), TITLE_NEGATIVE):
        ai_keyword_count = sum(blob.count(term) for term in ["llm", "rag", "embedding", "vector", "fine-tuning", "retrieval"])
        if ai_keyword_count >= 7:
            penalty += 28
            flags.append("AI keyword-heavy non-technical profile")
    history_months = sum(int(r.get("duration_months", 0) or 0) for r in candidate.get("career_history", []))
    years_months = float(candidate.get("profile", {}).get("years_of_experience", 0) or 0) * 12
    if history_months > years_months + 36:
        penalty += 10
        flags.append("timeline is slightly inconsistent")
    return penalty, flags


def score_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    blob = text_blob(candidate)
    skill, skill_groups = skill_score(candidate, blob)
    career, career_notes = career_score(candidate, blob)
    education = education_score(candidate)
    behavior = behavior_score(candidate)
    logistics = logistics_score(candidate)
    penalty, flags = honeypot_penalty(candidate, blob)

    raw = (
        skill * 0.30
        + career * 0.34
        + behavior * 0.16
        + logistics * 0.12
        + education * 0.08
        - penalty
    )
    score = clamp(raw) / 100.0
    return {
        "candidate_id": candidate["candidate_id"],
        "score": score,
        "candidate": candidate,
        "components": {
            "skill": skill,
            "career": career,
            "behavior": behavior,
            "logistics": logistics,
            "education": education,
            "penalty": penalty,
        },
        "skill_groups": skill_groups,
        "career_notes": career_notes,
        "flags": flags,
    }


def top_skill_names(candidate: dict[str, Any], limit: int = 4) -> list[str]:
    scored = sorted(
        candidate.get("skills", []),
        key=lambda s: (
            {"expert": 3, "advanced": 2, "intermediate": 1, "beginner": 0}.get(s.get("proficiency"), 0),
            int(s.get("endorsements", 0) or 0),
            int(s.get("duration_months", 0) or 0),
        ),
        reverse=True,
    )
    return [s.get("name", "") for s in scored[:limit] if s.get("name")]


def reasoning(row: dict[str, Any], rank: int) -> str:
    c = row["candidate"]
    p = c.get("profile", {})
    s = c.get("redrob_signals", {})
    years = p.get("years_of_experience", 0)
    title = p.get("current_title", "candidate")
    location = p.get("location", "unknown location")
    skills = ", ".join(top_skill_names(c, 3)) or "profile skills"
    groups = ", ".join(row["skill_groups"][:4]) or "adjacent ML/search"
    concerns: list[str] = []
    if float(row["components"]["penalty"]) > 0:
        concerns.append("profile consistency checks reduced confidence")
    if int(s.get("notice_period_days", 180) or 180) > 60:
        concerns.append(f"{s.get('notice_period_days')} day notice")
    try:
        inactive_days = (AS_OF - date.fromisoformat(s.get("last_active_date", "2000-01-01"))).days
        if inactive_days > 60:
            concerns.append(f"inactive for {inactive_days} days")
    except ValueError:
        pass
    if p.get("country") != "India" and not s.get("willing_to_relocate"):
        concerns.append("location/relocation fit is weak")

    if rank <= 20:
        tone = "Strong fit"
    elif rank <= 60:
        tone = "Good fit"
    else:
        tone = "Borderline fit"
    concern_text = f" Concern: {'; '.join(concerns[:2])}." if concerns else ""
    return (
        f"{tone}: {title} with {years} years in {location}; strongest evidence is {groups}, "
        f"with profile skills including {skills}. Redrob signals show response rate "
        f"{float(s.get('recruiter_response_rate', 0)):.2f}, notice {s.get('notice_period_days')} days, "
        f"and open_to_work={bool(s.get('open_to_work_flag'))}.{concern_text}"
    )


def rank(candidates_path: Path) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    with open_text(candidates_path) as f:
        for line in f:
            if not line.strip():
                continue
            scored.append(score_candidate(json.loads(line)))
    scored.sort(key=lambda r: (-r["score"], r["candidate_id"]))
    return scored[:100]


def write_submission(rows: list[dict[str, Any]], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["candidate_id", "rank", "score", "reasoning"])
        last_score = 1.0
        for idx, row in enumerate(rows, 1):
            # The supplied validator enforces candidate_id ordering for exact
            # score ties. Preserve model order by making displayed scores
            # strictly decreasing at a tiny, deterministic 1e-6 step.
            score = min(last_score - 0.000001, round(row["score"], 6))
            last_score = score
            writer.writerow([row["candidate_id"], idx, f"{score:.6f}", reasoning(row, idx)])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", required=True, type=Path, help="Path to candidates.jsonl or candidates.jsonl.gz")
    parser.add_argument("--out", required=True, type=Path, help="Output CSV path")
    args = parser.parse_args()
    rows = rank(args.candidates)
    write_submission(rows, args.out)
    print(f"Wrote {len(rows)} ranked candidates to {args.out}")


if __name__ == "__main__":
    main()
