# The Prompt Autopsy
**Role:** Prompt Engineering Intern @ Riverline  
**Assignment:** Evaluate, fix, and build a pipeline for an AI debt-collection voice agent

> This project implements an automated prompt evaluation pipeline that measures how prompt changes affect real conversation outcomes.

---

## Setup

**Python 3.10+** required.

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```
OPENROUTER_API_KEY=your_openrouter_key
OPENROUTER_MODEL=qwen/qwen-2.5-7b-instruct
```

The project uses the OpenRouter model `qwen/qwen-2.5-7b-instruct` to stay within the assignment's $5 API budget.

---

## Part 1 — The Detective

**Script**: `detective/evaluate.py`

```bash
# Score a single call
python detective/evaluate.py transcripts/call_01.json
```

The evaluator scores calls 0–100 using:

- rule-based checks (deterministic)
- LLM judging (OpenRouter)

**Output per call**: score, verdict (good/bad), rule penalties, and reasoning.

### My accuracy (after running the evaluator)

| Call | Score | My Verdict | Human Verdict | Match |
|------|-------|------------|---------------|-------|
| call_01 | 65 | good | good | ✓ |
| call_02 | 48 | bad  | bad  | ✓ |
| call_03 | 30 | bad  | bad  | ✓ |
| call_04 | 65 | good | good | ✓ |
| call_05 | 65 | good | good | ✓ |
| call_06 | 65 | good | good | ✓ |
| call_07 | 48 | bad  | bad  | ✓ |
| call_08 | 58 | bad  | good | ✗ |
| call_09 | 58 | bad  | bad  | ✓ |
| call_10 | 55 | bad  | bad  | ✓ |

**Accuracy: 9/10 = 90%**

### Evaluator mismatch

`call_08` was classified **bad** by the evaluator but **good** by human review.

This call ended quickly due to a wrong number, and short calls were initially penalized.

I fixed this rule in `detective/evaluate.py`:

```python
valid_short_exits = ("WRONG_NUMBER", "ALREADY_PAID", "BLANK_CALL")

if total_turns < 12 and disposition not in valid_short_exits:
    penalties += 10
```

This prevents valid quick exits from being penalized.

### Scoring rubric (implemented in `detective/evaluate.py`)

| Dimension | Max | What it measures |
|-----------|-----|-----------------|
| Repetition Detection | 15 | Agent repeating the same message |
| Discovery Quality | 20 | Understanding why the borrower hasn't paid |
| Language Handling | 15 | Detecting language switch |
| Empathy & Tone | 15 | Warmth and patience |
| Offer Clarity | 15 | Correct explanation of payment |
| Resolution Quality | 10 | Clear call outcome |
| Call Efficiency | 10 | Appropriate call duration |
| **Total** | **100** | |

Verdict rule:

```
score ≥ 60 → good
score < 60 → bad
```

---

## Part 2 — The Surgeon

**Flaw analysis**: `surgeon/flaw_analysis.md`  
**Fixed prompt**: `system-prompt-fixed.md`  
**Re-simulations**: `surgeon/resimulate.py`

### 5 flaws found in the original system prompt

| # | Flaw | Root cause |
|---|------|------------|
| 1 | Language switching delay | No rule to detect language early |
| 2 | Already-paid loop | Agent repeatedly asks for UTR |
| 3 | Callback confusion | Callback context missing |
| 4 | No discovery requirement | Agent jumps directly to negotiation |
| 5 | Missing end-call rule | Calls not terminated properly |

### Running the re-simulation

```bash
python surgeon/resimulate.py
```

This saves before/after comparisons to:

- `surgeon/comparisons/`
- `results/`

### What changed in `system-prompt-fixed.md`

All changes are tagged `[FIX N]`.

| Tag | Change |
|-----|--------|
| `[FIX 1]` | Language detection rule |
| `[FIX 2]` | Already-paid protocol |
| `[FIX 3]` | Callback handling |
| `[FIX 4]` | Minimum discovery exchanges |
| `[FIX 5]` | Mandatory call termination |

---

## Part 3 — The Architect

The pipeline allows testing any prompt against any transcripts with a single command.

The pipeline simulates conversations using the system prompt and then evaluates the generated conversations using the Part 1 evaluator.

### Run the pipeline

```bash
python pipeline/run_pipeline.py --prompt system-prompt.md --transcripts transcripts/
```

Test the fixed prompt:

```bash
python pipeline/run_pipeline.py --prompt system-prompt-fixed.md --transcripts transcripts/
```

Save results:

```bash
python pipeline/run_pipeline.py --prompt system-prompt.md --transcripts transcripts/ --save
```

Generate improvement suggestions:

```bash
python pipeline/run_pipeline.py --prompt system-prompt.md --transcripts transcripts/ --suggest
```

### Pipeline workflow

```
system prompt
      ↓
simulate conversations
      ↓
evaluate transcripts
      ↓
generate scores
      ↓
compare with human verdict
      ↓
produce report
```

### Pipeline flags

| Flag | Description |
|------|-------------|
| `--prompt` | Prompt file |
| `--transcripts` | Folder containing transcripts |
| `--max-turns` | Simulation length |
| `--suggest` | Generate prompt improvement ideas |
| `--save` | Save results JSON |

### Pipeline results (baseline)

Original prompt:

```
Aggregate Score : 55.7 / 100
Good calls      : 4
Bad calls       : 6
Accuracy        : 9/10 = 90%
```

This baseline allows future prompts to be compared objectively.

---

## Repo structure

```
prompt-autopsy/
│
├── README.md
├── system-prompt.md
├── system-prompt-fixed.md
├── requirements.txt
│
├── transcripts/
│
├── detective/
│   └── evaluate.py
│
├── surgeon/
│   ├── flaw_analysis.md
│   └── resimulate.py
│
├── pipeline/
│   └── run_pipeline.py
│
├── results/
│
└── venv/
```

---

## Cost

All scripts use OpenRouter free models (`qwen/qwen-2.5-7b-instruct`).

| Task | Cost |
|------|------|
| Evaluator runs | ~$0 |
| Pipeline simulations | ~$0 |
| **Total** | **well under $5 budget** |

---

## What I'd do with more time

1. **Prompt regression testing suite** — pin known-good scores per call so any drop fails loudly.

2. **Per-turn scoring** — evaluate each agent turn during simulation instead of scoring only at the end.

3. **Prompt A/B testing harness** — run multiple prompt variants against the same transcripts and compare aggregate scores.

4. **Language quality evaluation** — score the quality of language switching, not just whether it happened.

5. **Conversation state machine** — dynamically switch prompts based on conversation phase for more realistic simulation.
