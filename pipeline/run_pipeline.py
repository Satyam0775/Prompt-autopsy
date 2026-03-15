"""
pipeline/run_pipeline.py

Usage:
python pipeline/run_pipeline.py --prompt system-prompt.md --transcripts transcripts/
python pipeline/run_pipeline.py --prompt system-prompt-fixed.md --transcripts transcripts/ --save
python pipeline/run_pipeline.py --prompt system-prompt.md --transcripts transcripts/ --suggest
"""

import argparse
import json
import os
import sys
import re
import time
from datetime import datetime
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenRouter client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = os.getenv("OPENROUTER_MODEL", "qwen/qwen-2.5-7b-instruct")

# pipeline/run_pipeline.py is inside /pipeline so parent.parent = project root
ROOT        = Path(__file__).parent.parent
RESULTS_DIR = ROOT / "results"

# Import evaluator from detective/
sys.path.insert(0, str(ROOT / "detective"))
from evaluate import evaluate_transcript


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_transcripts(folder):
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in sorted(folder.glob("call_*.json"))
    ]


def load_verdicts(folder):
    vpath = folder / "verdicts.json"
    if not vpath.exists():
        return {}
    data = json.loads(vpath.read_text(encoding="utf-8"))
    return {k: v["verdict"] for k, v in data.get("verdicts", {}).items()}


def extract_values(transcript):
    c = transcript.get("customer", {})
    return {
        "customer_name":     c.get("name", "borrower"),
        "tos":               c.get("pending_amount", "unknown"),
        "pos":               c.get("closure_amount", "unknown"),
        "settlement_amount": c.get("settlement_amount", "unknown"),
        "dpd":               c.get("dpd", "unknown"),
    }


def customer_turns(transcript):
    return [
        t["text"]
        for t in transcript.get("transcript", [])
        if t["speaker"] == "customer"
    ]


def clean_response(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"\{\{.*?\}\}", "", text)
    return text.strip()


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Simulate: run customer turns through LLM with the given prompt
# ─────────────────────────────────────────────────────────────────────────────

AGENT_PREFIX = """\
You are Alex, a debt collection agent for DemoCompany.
You are on a live phone call about a DemoLender education loan.

CALL CONTEXT:
Customer      : {customer_name}
Total owed    : {tos} rupees
Closure offer : {pos} rupees (all penalty charges removed)
Settlement    : {settlement_amount} rupees (last resort only)
Days past due : {dpd}
Support email : support@demolender.com

RULES:
1. Speak in 1-3 short sentences only — this is a voice call.
2. If customer speaks Hindi, reply in Hindi and stay in Hindi.
3. If customer speaks Tamil, reply in Tamil and stay in Tamil.
4. Never revert to English once you have switched language.
5. If customer claims they already paid, say once:
   "Please email your reference to support@demolender.com for verification."
   Then close politely. Do NOT ask for UTR more than once.
6. Ask why they have not paid BEFORE discussing payment options.
7. Probe at least 3 times before giving up.
8. Never output JSON, code, or template variables.
9. Do not break character.

SYSTEM PROMPT:
{system_prompt}
"""


def simulate(transcript, prompt_text, max_turns):
    values = extract_values(transcript)
    system = AGENT_PREFIX.format(system_prompt=prompt_text, **values)

    turns     = customer_turns(transcript)[:max_turns]
    messages  = []
    sim_turns = []

    for text in turns:
        messages.append({"role": "user", "content": text})
        sim_turns.append({"speaker": "customer", "text": text})

        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system},
                    *messages
                ],
                temperature=0,
                max_tokens=150,
            )
            agent_text = clean_response(resp.choices[0].message.content or "")
        except Exception as e:
            agent_text = f"[ERROR: {e}]"

        messages.append({"role": "assistant", "content": agent_text})
        sim_turns.append({"speaker": "agent", "text": agent_text})

    sim = dict(transcript)
    sim["transcript"]     = sim_turns
    sim["function_calls"] = []
    sim["total_turns"]    = len(sim_turns)
    return sim


# ─────────────────────────────────────────────────────────────────────────────
# Bonus — Suggest improvements
# ─────────────────────────────────────────────────────────────────────────────

def suggest_improvements(prompt_text, results):
    bad = [r for r in results if r["verdict"] == "bad"]
    if not bad:
        return "All calls passed — no suggestions needed."

    bad_summary = "\n".join(
        f"{r['call_id']} score={r['score']} {r.get('reasoning','')[:100]}"
        for r in bad
    )

    prompt = (
        "You are a prompt engineer reviewing an AI debt-collection agent system prompt.\n\n"
        f"SYSTEM PROMPT (first 1200 chars):\n{prompt_text[:1200]}\n\n"
        f"WORST-SCORING CALLS:\n{bad_summary}\n\n"
        "Give exactly 3 short, specific, actionable improvements.\n"
        "Format:\n"
        "1. [Problem] → [Fix]\n"
        "2. [Problem] → [Fix]\n"
        "3. [Problem] → [Fix]"
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Suggestion error: {e}"


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Report
# ─────────────────────────────────────────────────────────────────────────────

def print_report(results, prompt_file, verdicts, suggestions=None):
    total = len(results)
    avg   = sum(r["score"] for r in results) / total if total else 0
    good  = sum(1 for r in results if r["verdict"] == "good")
    bad   = total - good

    matched = [r for r in results if verdicts.get(r["call_id"]) is not None]
    correct = sum(1 for r in matched
                  if r["verdict"] == verdicts.get(r["call_id"]))
    acc_str = (f"{correct}/{len(matched)} = {correct/len(matched):.0%}"
               if matched else "n/a")

    print(f"\n{'='*60}")
    print("  PIPELINE REPORT")
    print(f"  Prompt : {prompt_file}")
    print(f"  Model  : {MODEL}")
    print(f"{'='*60}")

    print(f"\n  {'Call':<12} {'Score':>5}  {'Verdict':<8}  {'Human':>6}  Match")
    print(f"  {'─'*48}")

    for r in results:
        hv    = verdicts.get(r["call_id"], "?")
        match = ("✓" if r["verdict"] == hv else "✗") if hv != "?" else " "
        icon  = "✅" if r["verdict"] == "good" else "❌"
        print(f"  {r['call_id']:<12} {r['score']:>5}  "
              f"{icon} {r['verdict']:<7} {hv:>6}  {match}")

    print(f"\n  {'─'*48}")
    print(f"  Aggregate Score : {avg:.1f} / 100")
    print(f"  Good / Bad      : {good} good, {bad} bad")
    print(f"  Accuracy        : {acc_str}")

    bad_calls = sorted([r for r in results if r["verdict"] == "bad"],
                       key=lambda x: x["score"])
    if bad_calls:
        print(f"\n  ⚠️  Failed calls:")
        for r in bad_calls:
            print(f"    • {r['call_id']} ({r['score']}/100) — "
                  f"{r.get('reasoning','')[:80]}")

    good_calls = sorted([r for r in results if r["verdict"] == "good"],
                        key=lambda x: -x["score"])
    if good_calls:
        print(f"\n  ✅ Passed calls:")
        for r in good_calls:
            print(f"    • {r['call_id']} ({r['score']}/100)")

    if suggestions:
        print(f"\n  {'─'*48}")
        print("  💡 SUGGESTED IMPROVEMENTS:")
        for line in suggestions.splitlines():
            print(f"  {line}")

    print(f"\n{'='*60}\n")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt",      required=True)
    parser.add_argument("--transcripts", required=True)
    parser.add_argument("--max-turns",   type=int, default=10)
    parser.add_argument("--suggest",     action="store_true")
    parser.add_argument("--save",        action="store_true")
    parser.add_argument("--quiet",       action="store_true")
    args = parser.parse_args()

    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY missing in .env")
        sys.exit(1)

    prompt_path     = ROOT / args.prompt
    transcripts_dir = ROOT / args.transcripts

    if not prompt_path.exists():
        print(f"ERROR: {prompt_path} not found")
        sys.exit(1)
    if not transcripts_dir.is_dir():
        print(f"ERROR: {transcripts_dir} not found")
        sys.exit(1)

    # encoding="utf-8" fixes Windows cp1252 crash
    prompt_text = prompt_path.read_text(encoding="utf-8")
    transcripts = load_transcripts(transcripts_dir)
    verdicts    = load_verdicts(transcripts_dir)

    if not transcripts:
        print(f"ERROR: No call_*.json in {transcripts_dir}")
        sys.exit(1)

    print(f"\n{'─'*60}")
    print(f"  Prompt Iteration Pipeline")
    print(f"  Prompt : {args.prompt}  |  Model : {MODEL}")
    print(f"  Calls  : {len(transcripts)}")
    print(f"{'─'*60}\n")

    results = []

    for i, transcript in enumerate(transcripts, 1):
        call_id = transcript.get("call_id", f"call_{i:02d}")

        if not args.quiet:
            print(f"[{i:02d}/{len(transcripts)}] {call_id}", end="  ", flush=True)

        # Step 2 — simulate with the provided prompt
        target = simulate(transcript, prompt_text, args.max_turns)

        # Step 3 — score with Part 1 evaluator
        try:
            result = evaluate_transcript(target)
            result["call_id"] = call_id
        except Exception as e:
            result = {
                "call_id":         call_id,
                "score":           0,
                "verdict":         "bad",
                "reasoning":       f"Eval error: {e}",
                "rule_problems":   [],
                "dimension_scores": {},
                "worst_messages":  [],
            }

        results.append(result)

        if not args.quiet:
            hv    = verdicts.get(call_id, "?")
            match = ("✓" if result["verdict"] == hv else "✗") if hv != "?" else ""
            print(f"score={result['score']:3d}  "
                  f"verdict={result['verdict']}  "
                  f"human={hv}  {match}")

        if i < len(transcripts):
            time.sleep(0.2)

    # Bonus
    suggestions = None
    if args.suggest:
        print("\n💡 Generating suggestions...")
        suggestions = suggest_improvements(prompt_text, results)

    # Step 4 — report
    print_report(results, args.prompt, verdicts, suggestions)

    # Save
    if args.save:
        RESULTS_DIR.mkdir(exist_ok=True)
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = RESULTS_DIR / f"pipeline_{Path(args.prompt).stem}_{ts}.json"
        out_path.write_text(
            json.dumps(
                {
                    "timestamp":       ts,
                    "prompt_file":     args.prompt,
                    "model":           MODEL,
                    "aggregate_score": round(
                        sum(r["score"] for r in results) / len(results), 2
                    ),
                    "good":        sum(1 for r in results if r["verdict"] == "good"),
                    "bad":         sum(1 for r in results if r["verdict"] == "bad"),
                    "results":     results,
                    "suggestions": suggestions,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"  💾 Saved → {out_path}\n")


if __name__ == "__main__":
    main()