#!/usr/bin/env python3
"""Fill the official Redrob PPTX template with this solution's content."""

from __future__ import annotations

import argparse
import copy
import re
import zipfile
from pathlib import Path

from lxml import etree


NS = {
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

SLIDE_CONTENT = {
    1: {
        "Team Name :": [
            "Team Name : india-runs-data-ai",
            "Team Leader Name : Mohamed Fasidh",
            "Problem Statement : Build an offline AI system that ranks candidates for Redrob's Senior AI Engineer founding-team role by understanding production ML fit, behavioral availability, logistics, and profile consistency beyond keyword matching.",
        ],
        "Problem Statement :": [""],
        "Team Leader Name :": [""],
    },
    2: {
        "What is your proposed solution? What differentiates your approach from traditional candidate matching systems?": [
            "Proposed solution: an offline deterministic ranker that streams the 100K candidate JSONL, extracts JD-aligned signals, scores every candidate, and writes a validated top-100 CSV.",
            "It is designed for the exact Redrob JD: Senior AI Engineer with production retrieval, ranking, vector search, evaluation, Python, product-engineering, and India/Pune/Noida fit.",
            "Differentiator: the ranker does not count AI keywords. It combines career evidence, skill trust, Redrob behavior, logistics, education, and honeypot/profile consistency checks.",
            "Every selected candidate receives a grounded 1-2 sentence reason using only facts present in the candidate profile.",
        ],
    },
    3: {
        "What are the key requirements extracted from the JD? Which candidate signals are most important for determining relevance? / How does your solution evaluate candidate fit beyond keyword matching?": [
            "JD requirements extracted: 5-9 years preferred, production embeddings/retrieval, vector or hybrid search, ranking evaluation (NDCG/MRR/MAP/A-B tests), strong Python, and product-company shipping judgment.",
            "Positive career signals: applied ML/AI/search/recommendation titles, shipped production ranking/search systems, product or marketplace company exposure, recent hands-on coding, and mentoring ability.",
            "Negative fit signals: pure research without deployment, recent-only LangChain demos, services-only career history, non-technical current titles with AI keyword stuffing, and weak NLP/IR exposure.",
            "Behavioral signals: open_to_work, recent activity, recruiter response rate, notice period, interview completion, GitHub activity, verification, recruiter saves, and relocation/hybrid readiness.",
        ],
    },
    4: {
        "How does your system retrieve, score, and rank candidates? What models, algorithms, or heuristics are used? How are multiple candidate signals combined into a final ranking?": [
            "Retrieval/ranking: all candidates are scored in one streaming pass, then sorted by score and candidate_id for deterministic output.",
            "Skill component: Python, retrieval/RAG, vector databases, ranking/recommendations, evaluation, LLM/fine-tuning, and production system evidence with endorsement/duration/assessment trust.",
            "Career component: current title, experience band, role descriptions, product-company exposure, services-only penalties, shipped search/ranking/recommendation evidence, and research/demo-only penalties.",
            "Final score: weighted combination of skill (30%), career (34%), behavior (16%), logistics (12%), education (8%), minus honeypot penalties.",
        ],
    },
    5: {
        "How are ranking decisions explained? How do you prevent hallucinations or unsupported justifications? How does your solution handle inconsistent, low-quality, or suspicious profiles?": [
            "Explanations are generated from candidate fields already loaded by the scorer: title, years, location, matched skill groups, top profile skills, response rate, notice period, and open_to_work.",
            "No hosted LLM is used for reasoning, so justifications cannot invent employers, skills, or achievements outside the profile.",
            "The tone changes by rank bucket: strong fit, good fit, or borderline fit. Obvious concerns such as long notice, inactivity, weak relocation, or consistency flags are included.",
            "Suspicious profiles are downweighted for expert skills with near-zero duration, broad skill lists with low experience, AI keyword-heavy non-technical titles, and timeline inconsistency.",
        ],
    },
    6: {
        "What is the complete workflow from JD input to ranked candidate output?": [
            "1. Read the Senior AI Engineer JD and convert it into explicit feature groups.",
            "2. Stream each candidate JSON object from candidates.jsonl or candidates.jsonl.gz.",
            "3. Build a profile text blob from profile, career history, skills, education, certifications, and Redrob signals.",
            "4. Score skills, career, behavior, logistics, education, and honeypot risk.",
            "5. Sort candidates by final score and deterministic candidate_id tie-break.",
            "6. Write candidate_id, rank, score, and grounded reasoning to submission.csv.",
            "7. Validate using the official validate_submission.py script.",
        ],
    },
    7: {
        "__ADD_BODY__": [
            "Input Layer: candidates.jsonl + Redrob JD + candidate schema.",
            "Feature Layer: text evidence, skill trust, career history, Redrob behavior, logistics, education, and consistency checks.",
            "Scoring Layer: weighted interpretable components and honeypot penalties.",
            "Ranking Layer: deterministic sort, strictly decreasing displayed scores, top-100 selection.",
            "Output Layer: validated submission.csv, metadata YAML, README, GitHub repo, and Colab sandbox demo.",
        ],
    },
    8: {
        "What results or insights demonstrate ranking quality? How does your solution meet the challenge's runtime and compute constraints?": [
            "Generated the required 100-row submission.csv and passed the official validator: 'Submission is valid.'",
            "Full 100K-candidate run completed locally in about 54-100 seconds, under the 5 minute CPU-only challenge limit.",
            "Memory footprint is small: the script streams input and stores compact score rows before sorting.",
            "Ranking quality is driven by JD-specific evidence rather than generic similarity: top candidates show retrieval/ranking/vector/evaluation production signals plus availability.",
            "Colab sandbox demo runs successfully on demo_candidates.jsonl and prints 'Demo ranking generated successfully.'",
        ],
    },
    9: {
        "What technologies, frameworks, and tools were used and why were they selected for this solution?": [
            "Python standard library for ranking: json, csv, gzip, argparse, datetime, pathlib, math, and regex.",
            "No external model, GPU, or network dependency during ranking, matching the reproduction constraints.",
            "Pandas is used only in the Colab demo to display the generated demo_submission.csv.",
            "Matplotlib/lxml are used only for documentation/deck generation, not for ranking.",
            "GitHub hosts source code and artifacts; Google Colab provides the sandbox/demo notebook.",
        ],
    },
    10: {
        "Github video etc": [
            "GitHub repository: https://github.com/Mohamed-Fasidh/redrob-candidate-ranker",
            "Sandbox/demo: https://colab.research.google.com/github/Mohamed-Fasidh/redrob-candidate-ranker/blob/main/redrob_ranker_demo_colab.ipynb",
            "Submission CSV: submission.csv (validated with official script)",
            "Reproduce command: python rank.py --candidates ./candidates.jsonl --out ./submission.csv",
            "Contact: Mohamed Fasidh | mohamedfasidh045@gmail.com | +91-8015334576",
        ],
    },
    11: {
        "__ADD_BODY__": [
            "Thank you",
            "The solution package is complete, reproducible, offline, and ready for Redrob review.",
            "Team: india-runs-data-ai",
        ],
    },
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def shape_text(shape: etree._Element) -> str:
    return normalize(" ".join(shape.xpath(".//a:t/text()", namespaces=NS)))


def set_text(shape: etree._Element, lines: list[str]) -> None:
    tx_body = shape.find("p:txBody", namespaces=NS)
    if tx_body is None:
        return
    body_pr = tx_body.find("a:bodyPr", namespaces=NS)
    lst_style = tx_body.find("a:lstStyle", namespaces=NS)
    for child in list(tx_body):
        if child.tag.endswith("}p"):
            tx_body.remove(child)

    insert_at = 0
    if body_pr is not None:
        insert_at += 1
    if lst_style is not None:
        insert_at += 1

    for line in lines:
        p = etree.Element(f"{{{NS['a']}}}p")
        r = etree.SubElement(p, f"{{{NS['a']}}}r")
        r_pr = etree.SubElement(r, f"{{{NS['a']}}}rPr")
        r_pr.set("lang", "en-US")
        t = etree.SubElement(r, f"{{{NS['a']}}}t")
        t.text = line
        tx_body.insert(insert_at, p)
        insert_at += 1


def add_body_shape(slide_xml: etree._Element, lines: list[str]) -> None:
    sp_tree = slide_xml.find(".//p:spTree", namespaces=NS)
    if sp_tree is None:
        return
    max_id = 1000
    for c_nv_pr in slide_xml.xpath(".//p:cNvPr", namespaces=NS):
        try:
            max_id = max(max_id, int(c_nv_pr.get("id", "0")))
        except ValueError:
            pass

    sp = etree.Element(f"{{{NS['p']}}}sp")
    nv_sp_pr = etree.SubElement(sp, f"{{{NS['p']}}}nvSpPr")
    c_nv_pr = etree.SubElement(nv_sp_pr, f"{{{NS['p']}}}cNvPr")
    c_nv_pr.set("id", str(max_id + 1))
    c_nv_pr.set("name", "Generated Body")
    etree.SubElement(nv_sp_pr, f"{{{NS['p']}}}cNvSpPr").set("txBox", "1")
    etree.SubElement(nv_sp_pr, f"{{{NS['p']}}}nvPr")
    sp_pr = etree.SubElement(sp, f"{{{NS['p']}}}spPr")
    xfrm = etree.SubElement(sp_pr, f"{{{NS['a']}}}xfrm")
    etree.SubElement(xfrm, f"{{{NS['a']}}}off").attrib.update({"x": "480500", "y": "1278500"})
    etree.SubElement(xfrm, f"{{{NS['a']}}}ext").attrib.update({"cx": "8121600", "cy": "3198900"})
    prst = etree.SubElement(sp_pr, f"{{{NS['a']}}}prstGeom")
    prst.set("prst", "rect")
    etree.SubElement(prst, f"{{{NS['a']}}}avLst")
    tx_body = etree.SubElement(sp, f"{{{NS['p']}}}txBody")
    body_pr = etree.SubElement(tx_body, f"{{{NS['a']}}}bodyPr")
    body_pr.set("wrap", "square")
    etree.SubElement(tx_body, f"{{{NS['a']}}}lstStyle")
    for line in lines:
        p = etree.SubElement(tx_body, f"{{{NS['a']}}}p")
        r = etree.SubElement(p, f"{{{NS['a']}}}r")
        r_pr = etree.SubElement(r, f"{{{NS['a']}}}rPr")
        r_pr.set("lang", "en-US")
        r_pr.set("sz", "1700")
        t = etree.SubElement(r, f"{{{NS['a']}}}t")
        t.text = line
    sp_tree.append(sp)


def fill_pptx(template: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    replacements_by_path: dict[str, bytes] = {}
    with zipfile.ZipFile(template, "r") as zin:
        for slide_num, replacements in SLIDE_CONTENT.items():
            slide_path = f"ppt/slides/slide{slide_num}.xml"
            xml = etree.fromstring(zin.read(slide_path))
            if "__ADD_BODY__" in replacements:
                add_body_shape(xml, replacements["__ADD_BODY__"])
            for shape in xml.xpath(".//p:sp", namespaces=NS):
                current = shape_text(shape)
                if current in replacements:
                    set_text(shape, replacements[current])
            replacements_by_path[slide_path] = etree.tostring(
                xml, xml_declaration=True, encoding="UTF-8", standalone=True
            )

        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = replacements_by_path.get(item.filename)
                if data is None:
                    data = zin.read(item.filename)
                zout.writestr(item, data)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    fill_pptx(args.template, args.out)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
