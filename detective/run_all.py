import json
from pathlib import Path
from evaluate import evaluate

TRANSCRIPTS_DIR = Path("transcripts")
VERDICTS_FILE = TRANSCRIPTS_DIR / "verdicts.json"


def load_verdicts():
    """Load human verdicts"""
    if not VERDICTS_FILE.exists():
        return {}

    with open(VERDICTS_FILE, encoding="utf-8") as f:
        data = json.load(f)

    return {k: v["verdict"] for k, v in data["verdicts"].items()}


def main():

    verdicts = load_verdicts()

    files = sorted(TRANSCRIPTS_DIR.glob("call_*.json"))

    print(f"\nRunning evaluator on {len(files)} transcripts\n")

    results = []

    for i, file in enumerate(files, 1):

        print(f"[{i}/{len(files)}] {file.name}")

        r = evaluate(str(file))

        call_id = r["call_id"]

        human = verdicts.get(call_id)

        if human:
            print(f"  predicted={r['verdict']} | human={human}")

        results.append(r)

    # Calculate accuracy
    correct = 0
    total = 0

    for r in results:

        human = verdicts.get(r["call_id"])

        if human is None:
            continue

        total += 1

        if human == r["verdict"]:
            correct += 1

    accuracy = correct / total if total else 0

    print("\n==============================")
    print("RESULTS SUMMARY")
    print("==============================")
    print(f"Accuracy: {correct}/{total} = {accuracy:.0%}")

    avg_score = sum(r["score"] for r in results) / len(results)

    print(f"Average Score: {avg_score:.1f}/100")


if __name__ == "__main__":
    main()
