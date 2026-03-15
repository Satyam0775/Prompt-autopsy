"""
detective/evaluate.py

Usage (CLI):
    python detective/evaluate.py transcripts/call_01.json

Usage (import):
    from evaluate import evaluate_transcript
    result = evaluate_transcript(transcript_dict)
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct")


# ─────────────────────────────────────────────────────────────────────────────
# Rule checks — deterministic, no API cost
# ─────────────────────────────────────────────────────────────────────────────

def rule_checks(call):
    penalties = 0
    problems  = []

    transcript    = call.get("transcript", [])
    agent_msgs    = [m["text"] for m in transcript if m["speaker"] == "agent"]
    customer_msgs = [m["text"] for m in transcript if m["speaker"] == "customer"]
    total_turns   = call.get("total_turns", 0)
    disposition   = call.get("disposition", "")

    # Repetition — agent saying same thing 4+ times
    seen = {}
    for msg in agent_msgs:
        key = msg.lower()[:40]
        seen[key] = seen.get(key, 0) + 1
    for v in seen.values():
        if v >= 4:
            penalties += 15
            problems.append("Agent repeating same message")
            break

    # Call too long
    if total_turns > 90:
        penalties += 10
        problems.append("Call too long")

    # Call too short — only penalise if NOT a valid quick exit
    # Wrong number, already paid, blank calls SHOULD be short
    valid_short_exits = ("WRONG_NUMBER", "ALREADY_PAID", "BLANK_CALL")
    if total_turns < 12 and disposition not in valid_short_exits:
        penalties += 10
        problems.append("Call ended too early")

    # Customer had to ask for language switch — agent did not detect it
    for msg in customer_msgs:
        text = msg.lower()
        if "hindi" in text or "tamil" in text or "telugu" in text:
            penalties += 10
            problems.append("Customer had to request language switch")
            break

    # Disposition mismatch — BLANK_CALL but transcript has real content
    if disposition == "BLANK_CALL" and len(transcript) > 20:
        penalties += 15
        problems.append("Disposition mismatch: BLANK_CALL but transcript exists")

    return penalties, problems


# ─────────────────────────────────────────────────────────────────────────────
# LLM judge
# ─────────────────────────────────────────────────────────────────────────────

JUDGE_PROMPT = """\
Score this AI debt collection call from 0 to 100.

Criteria:
- Empathy and tone (was the agent warm and patient?)
- Clarity (were amounts explained correctly?)
- No repetition (did the agent keep repeating the same thing?)
- Discovery (did the agent understand WHY the borrower hasn't paid?)
- Resolution quality (did the call end with a clear outcome?)

Respond with JSON ONLY. No markdown. No explanation outside the JSON.
Example: {{"score": 72, "reason": "Good empathy but repeated the amount too many times."}}

Transcript:
{transcript_text}"""


def llm_score(call):
    transcript = call.get("transcript", [])
    text = "\n".join(
        f'{m["speaker"]}: {m["text"]}'
        for m in transcript[:60]
    )

    prompt = JUDGE_PROMPT.format(transcript_text=text)

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=120,
        )

        content = resp.choices[0].message.content.strip()

        # Strip markdown fences if model added them despite instructions
        content = re.sub(r"```json|```", "", content).strip()

        # Extract first JSON object if model added extra text around it
        match = re.search(r'\{.*?\}', content, re.S)
        if match:
            content = match.group()

        data = json.loads(content)

        # Ensure score is a valid integer
        data["score"] = max(0, min(100, int(data.get("score", 50))))

        return data

    except Exception as e:
        print(f"  [LLM judge warning: {e}]")
        return {"score": 50, "reason": "LLM judge failed — defaulting to 50"}


# ─────────────────────────────────────────────────────────────────────────────
# Main evaluator — accepts a transcript dict
# Called by run_pipeline.py and run_all.py
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_transcript(call: dict) -> dict:
    """
    Score a transcript dict. Returns:
        call_id, score, verdict, rule_penalty, rule_problems,
        reasoning, worst_messages, dimension_scores
    """
    penalty, problems = rule_checks(call)
    llm               = llm_score(call)

    score   = max(0, min(100, llm["score"] - penalty))
    verdict = "good" if score >= 60 else "bad"

    return {
        "call_id":          call.get("call_id", "unknown"),
        "score":            score,
        "verdict":          verdict,
        "rule_penalty":     penalty,
        "rule_problems":    problems,
        "reasoning":        llm.get("reason", ""),
        "worst_messages":   [],
        "dimension_scores": {},
    }


# ─────────────────────────────────────────────────────────────────────────────
# CLI — run directly on a single transcript file
# ─────────────────────────────────────────────────────────────────────────────

def evaluate(path):
    """Load a JSON file and score it. Used when running from command line."""
    try:
        with open(path, encoding="utf-8") as f:
            call = json.load(f)
    except Exception as e:
        return {"call_id": str(path), "score": 0, "verdict": "bad", "error": str(e)}

    result = evaluate_transcript(call)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", help="Path to call_XX.json")
    args = parser.parse_args()
    evaluate(args.transcript)