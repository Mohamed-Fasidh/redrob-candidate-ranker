# Redrob Data & AI Challenge Candidate Ranker

This repository contains an offline, deterministic ranker for the Redrob Intelligent Candidate Discovery & Ranking Challenge.

## Approach

The target role is a Senior AI Engineer for Redrob's founding AI team. The ranker scores every candidate once using JD-derived evidence:

- Production retrieval, ranking, vector search, evaluation, Python, LLM, and deployment signals.
- Career fit: relevant current title, 5-9 year preference, product-company exposure, shipped search/ranking/recommendation systems, and penalties for services-only or non-technical keyword-stuffed profiles.
- Behavioral availability: Redrob response rate, recent activity, open-to-work flag, notice period, interview completion, GitHub activity, verification, profile saves, and recruiter views.
- Logistics: India/Pune/Noida/Delhi NCR/Mumbai/Hyderabad/Bangalore signal, hybrid/onsite/flexible work mode, and relocation willingness.
- Honeypot resistance: penalties for impossible-looking expert skills, excessive skills for low experience, AI keyword-heavy non-technical profiles, and timeline inconsistencies.

No external APIs, network calls, GPU, or hosted LLMs are used during ranking.

## Reproduce

From this repo root:

```powershell
python rank.py --candidates "D:\Download\[PUB] India_runs_data_and_ai_challenge\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl" --out submission.csv
```

Validate:

```powershell
python "D:\Download\[PUB] India_runs_data_and_ai_challenge\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\validate_submission.py" submission.csv
```

## Files

- `rank.py` - complete offline ranking pipeline.
- `submission.csv` - generated top-100 candidate ranking.
- `submission_metadata.yaml` - portal metadata template filled with this method.
- `approach_deck.md` - deck content.
- `approach_deck.pdf` - PDF version of the approach deck.
- `requirements.txt` - no third-party dependency required for ranking.

## Runtime

The script streams `candidates.jsonl`, keeps only scored rows in memory, and sorts 100,000 compact score records. It is designed for CPU-only execution under the 5 minute / 16 GB challenge constraint.
