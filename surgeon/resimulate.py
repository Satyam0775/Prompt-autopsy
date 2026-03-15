"""
Re-simulates bad calls with the fixed system prompt.

Run:
    python surgeon/resimulate.py
    python surgeon/resimulate.py --calls call_02 call_10
"""

import json
import os
import sys
import argparse
import re
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# -----------------------------
# OpenRouter Client
# -----------------------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "prompt-autopsy"
    }
)

MODEL = os.getenv("OPENROUTER_MODEL", "mistralai/mistral-7b-instruct:free")

# -----------------------------
# Paths
# -----------------------------
ROOT         = Path(__file__).parent.parent
TRANSCRIPTS  = ROOT / "transcripts"
RESULTS_DIR  = ROOT / "results"
COMPARISONS  = Path(__file__).parent / "comparisons"

SELECTED = {
    "call_02": "Flaw 1+2 — Language switch chaos + already-paid claim with deceased husband",
    "call_03": "Flaw 2 — Agent looped asking for UTR instead of escalating",
    "call_10": "Flaw 4 — Agent gave up without proper discovery",
}

# -----------------------------
# Short System Prompt
# -----------------------------
AGENT_SYSTEM = """
You are Alex, a debt collection agent for DemoCompany calling about a DemoLender education loan.

CALL CONTEXT:
Customer: {customer_name}
Total owed: {tos} rupees
Closure offer: {pos} rupees
Settlement: {settlement_amount} rupees
Days past due: {dpd}

RULES:
1. Speak in 1-3 short sentences.
2. If customer speaks Hindi, switch to Hindi and stay in Hindi.
3. If customer speaks Tamil, switch to Tamil and stay in Tamil.
4. Never switch back to English once switched.
5. If customer says they already paid:
   Say once: "Please email payment reference to support@demolender.com for verification."
   Then end politely.
6. Do not ask for UTR more than once.
7. Ask why they haven't paid before discussing payment options.
8. Probe at least 3 times before concluding.
9. Never output JSON or code.
"""


# -----------------------------
# Helpers
# -----------------------------
def extract_values(transcript):
    c = transcript.get("customer", {})
    return {
        "customer_name": c.get("name", "borrower"),
        "tos": c.get("pending_amount", "unknown"),
        "pos": c.get("closure_amount", "unknown"),
        "settlement_amount": c.get("settlement_amount", "unknown"),
        "dpd": c.get("dpd", "unknown"),
    }


def customer_turns(transcript):
    return [
        t["text"]
        for t in transcript.get("transcript", [])
        if t["speaker"] == "customer"
    ]


def clean_agent_response(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    return text.strip()


# -----------------------------
# Simulation
# -----------------------------
def run_simulation(customer_lines, system_prompt, max_turns=12):
    messages = []
    turns = []

    for line in customer_lines[:max_turns]:

        messages.append({"role": "user", "content": line})
        turns.append({"speaker": "customer", "text": line})

        try:
            resp = client.chat.completions.create(
                model=MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *messages
                ],
                temperature=0,
                max_tokens=150,
            )

            agent_text = clean_agent_response(
                resp.choices[0].message.content or ""
            )

        except Exception as e:
            agent_text = f"[ERROR: {e}]"

        messages.append({"role": "assistant", "content": agent_text})
        turns.append({"speaker": "agent", "text": agent_text})

    return turns


# -----------------------------
# Format comparison
# -----------------------------
def format_comparison(call_id, flaw, original, fixed):

    lines = []
    lines.append("="*70)
    lines.append(f"BEFORE / AFTER — {call_id.upper()}")
    lines.append(f"Flaw: {flaw}")
    lines.append("="*70)
    lines.append("")
    lines.append("--- BEFORE (original broken prompt) ---")
    lines.append("")

    for t in original[:20]:
        spk = "AGENT" if t["speaker"] == "agent" else "CUSTOMER"
        lines.append(f"[{spk}] {t['text']}")

    lines.append("")
    lines.append("--- AFTER (fixed prompt) ---")
    lines.append("")

    for t in fixed:
        spk = "AGENT" if t["speaker"] == "agent" else "CUSTOMER"
        lines.append(f"[{spk}] {t['text']}")

    lines.append("")
    return "\n".join(lines)


# -----------------------------
# Main
# -----------------------------
def main():

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--calls",
        nargs="+",
        default=list(SELECTED.keys()),
        choices=list(SELECTED.keys()),
    )
    parser.add_argument("--max-turns", type=int, default=12)

    args = parser.parse_args()

    if not os.getenv("OPENROUTER_API_KEY"):
        print("ERROR: OPENROUTER_API_KEY missing in .env")
        sys.exit(1)

    RESULTS_DIR.mkdir(exist_ok=True)
    COMPARISONS.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*70)
    print(f"SURGEON — Re-simulation | model: {MODEL}")
    print("="*70 + "\n")

    for call_id in args.calls:

        flaw = SELECTED[call_id]
        path = TRANSCRIPTS / f"{call_id}.json"

        if not path.exists():
            print(f"{call_id}.json not found")
            continue

        transcript = json.loads(path.read_text(encoding="utf-8"))

        original = transcript.get("transcript", [])
        cust = customer_turns(transcript)

        values = extract_values(transcript)

        print(f"📞 {call_id}")
        print(f"Flaw: {flaw}")
        print(f"Customer: {values['customer_name']}")
        print(f"Simulating first {args.max_turns} turns...")

        system_prompt = AGENT_SYSTEM.format(**values)

        fixed_sim = run_simulation(cust, system_prompt, args.max_turns)

        comp_text = format_comparison(call_id, flaw, original, fixed_sim)

        print("done.\n")

        (COMPARISONS / f"{call_id}_comparison.md").write_text(
            comp_text,
            encoding="utf-8"
        )

        (RESULTS_DIR / f"before_after_{call_id}.md").write_text(
            comp_text,
            encoding="utf-8"
        )

    print("Results saved:")
    print("surgeon/comparisons/")
    print("results/")


if __name__ == "__main__":
    main()