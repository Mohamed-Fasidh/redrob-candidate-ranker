# Redrob Candidate Ranker

## Problem

Recruiters need a trusted shortlist for a Senior AI Engineer founding-team role. The JD explicitly warns against simple keyword matching, so the system ranks for real production retrieval/ranking experience, shipping judgment, platform activity, and logistics.

## Target Candidate

- 5-9 years preferred, with flexibility for strong signals.
- Applied ML/AI engineer with production embeddings, vector search, hybrid retrieval, ranking, and evaluation experience.
- Product-company or marketplace exposure preferred over services-only career history.
- India location or relocation fit for Pune/Noida hybrid work.
- Available and responsive on the Redrob platform.

## Scoring Model

The ranker combines five interpretable components:

- Skills: Python, retrieval, vector databases, ranking/recommendations, evaluation, LLM/fine-tuning, and production systems.
- Career: current title, shipped search/ranking/recommendation systems, product-company exposure, experience band, and negative fit signals.
- Behavior: open-to-work, response rate, recent activity, notice period, interview completion, GitHub activity, verification, recruiter saves, and profile views.
- Logistics: India, Pune/Noida/Delhi NCR/Mumbai/Hyderabad/Bangalore, relocation, and hybrid/onsite/flexible preference.
- Education: relevant CS/data/AI fields and institution tier.

## Honeypot Resistance

The model downweights profiles that look strong only by keyword count:

- Expert skills with near-zero duration.
- Very broad skill lists for low experience.
- AI-keyword-heavy non-technical current titles.
- Timeline inconsistencies between total experience and career history.
- Services-only profiles without product or production ML evidence.

## Reproducibility

`rank.py` streams `candidates.jsonl`, scores candidates deterministically, sorts by score and candidate ID, and writes exactly 100 rows with grounded 1-2 sentence reasoning. It uses only Python standard library modules and makes no network calls.

## Submission Artifacts

- `submission.csv`: required top-100 ranking.
- `rank.py`: complete ranking code.
- `submission_metadata.yaml`: portal metadata mirror.
- `README.md`: reproduce and validation commands.
- `approach_deck.pdf`: this methodology as a PDF.
