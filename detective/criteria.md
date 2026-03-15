# Scoring Criteria — AI Debt Collection Agent Evaluator

This document defines the rubric used by `evaluate.py`. The criteria are designed to be
**deterministic enough** that two independent implementations would produce similar scores
(within ±5 points on any individual call).

---

## Overview

| Dimension             | Max Points | Measures |
|-----------------------|-----------|---------|
| Phase Progression     | 15        | Did the call follow Opening→Discovery→Negotiation→Closing in the right order? |
| Discovery Quality     | 15        | Did the agent understand WHY the borrower hasn't paid before trying to negotiate? |
| Language Handling     | 15        | Did the agent detect and switch to the customer's preferred language, promptly and consistently? |
| Empathy & Tone        | 10        | Was the agent warm, patient, and appropriate — no robotic pressure? |
| Offer / Info Clarity  | 10        | Were amounts (TOS/POS/settlement) explained correctly without confusion? |
| Edge Case Handling    | 10        | Was the special situation (wrong number, already paid, dispute, death) handled correctly? |
| No Repetition         | 10        | Did each agent turn advance the conversation, or was it looping? |
| Resolution Quality    | 10        | Was the right resolution reached and properly communicated? |
| Call Efficiency       | 5         | Was call duration proportionate to the outcome? |
| **TOTAL**             | **100**   | |

**Verdict threshold**: `score >= 60` → `"good"`, `score < 60` → `"bad"`

---

## Dimension 1 — Phase Progression (0–15)

The agent must move through phases in this order:
**Opening → Discovery → Negotiation → Closing**

Optional detours: Dispute phase (between Discovery and Negotiation) is acceptable when the borrower explicitly disputes the loan.

| Score | Criteria |
|-------|----------|
| 15    | All function calls (`proceed_to_*`) happen at the correct moment. No looping, no skipping. |
| 10    | Mostly correct. One function call slightly early or late, but overall flow is maintained. |
| 5     | Phase skip (e.g., jumped to Negotiation without Discovery) OR repeated loop between two phases. |
| 0     | Completely wrong phase management. Negotiation before Discovery, or no phase transitions at all when needed. |

**Red flags:**
- `proceed_to_negotiation` called with `willingness: "unclear"` after fewer than 5 agent turns in discovery.
- `proceed_to_closing` called without any payment commitment, callback, or clear disposition.
- `end_call` called in Opening without exhausting quick-exit protocols.

---

## Dimension 2 — Discovery Quality (0–15)

Before negotiating, the agent must understand the borrower's situation.

| Score | Criteria |
|-------|----------|
| 15    | Identified root cause (job loss / dispute / hardship / barriers). Correct borrower category logged. Follow-up questions asked. |
| 10    | Root cause partially understood. Some follow-up, but key question missed. |
| 5     | Minimal discovery — asked one question and moved on. |
| 0     | No discovery. Jumped to amounts immediately without understanding the borrower. |

**What counts as good discovery:**
- Agent asked about employment/financial situation
- Agent probed whether the situation is temporary or ongoing
- Agent identified borrower category (see system prompt categories A–F)
- Agent did NOT rush past repeated "Hello?" / connectivity issues as if they were genuine responses

**What does NOT count:**
- Counting silence breaks ("Hello? Are you there?") as discovery turns
- Repeating the outstanding amount as a "discovery" question

---

## Dimension 3 — Language Handling (0–15)

The agent must detect the customer's preferred language from the **first** customer response and switch immediately.

| Score | Criteria |
|-------|----------|
| 15    | Language detected from Turn 1 of customer speech. `switch_language` called before next agent turn. Language maintained for rest of call. |
| 10    | Switch happened within 3 customer turns. OR minor 1–2 sentence reversion to English. |
| 5     | Switch happened but agent kept reverting. `switch_language` called 3+ times (sign of instability). |
| 0     | Customer clearly requested or spoke non-English throughout. Agent ignored it or only briefly attempted it. |

**N/A rule**: If the customer spoke only English throughout, award full **15 points** (no language issue to handle).

**Key evidence patterns:**
- Customer says "हिंदी में बात करिए" → agent must switch immediately
- Customer says "do you know Tamil?" → agent must call `switch_language("ta")` on the next turn
- Agent calling `switch_language` 3 times in one call = serious instability = 5 pts max

---

## Dimension 4 — Empathy & Tone (0–10)

| Score | Criteria |
|-------|----------|
| 10    | Genuine empathy shown. Patient with connectivity issues. No inappropriate pressure. Acknowledged customer emotions (grief, frustration, financial stress). |
| 7     | Mostly empathetic. One instance of sounding robotic or slightly pressuring. |
| 3     | Formulaic empathy ("I understand") without substance. Used credit-score pressure in clearly inappropriate context (e.g., immediately after learning about a spouse's death). |
| 0     | Cold, dismissive, or pressuring. Used urgency language in situations where empathy was clearly needed first. |

**Automatic deductions:**
- Mentioning credit score damage within 2 turns of hearing about a borrower's spouse's death: −5 pts
- Using "firm" pressure language when borrower just expressed inability to pay due to unemployment: −3 pts
- Repeated "Hello?" after a clear "No": −2 pts (per system prompt: "No is NOT silence")

---

## Dimension 5 — Offer / Information Clarity (0–10)

| Score | Criteria |
|-------|----------|
| 10    | Correct amounts stated at the right time. TOS to establish the "before", POS/closure as the offer, settlement only as last resort. |
| 7     | Mostly correct, but one figure was inconsistently mentioned (e.g., stated POS before confirming borrower identity). |
| 3     | Amounts confused or contradicted. Or agent never disclosed the closure offer clearly. |
| 0     | Wrong amounts used throughout. Borrower left without understanding what they owe or what the offer is. |

**Red flags:**
- Disclosing amounts before confirming identity
- Quoting TOS as "what you need to pay" (system prompt explicitly forbids this)
- Quoting a closure amount of "zero" when `closure_amount` field is populated

---

## Dimension 6 — Edge Case Handling (0–10)

**Edge cases and expected handling:**

| Situation | Expected Agent Action | Bad Agent Action |
|-----------|----------------------|------------------|
| Wrong number | Ask for customer name. If denied, end call immediately with `wrong_party`. Share no loan details. | Continue collection pitch. |
| Already paid (with UTR) | Acknowledge, take UTR once, direct to support@demolender.com, end with `claims_already_paid`. | Loop asking for UTR 5+ times. Keep verifying in real-time. |
| Dispute (institute closed/cancelled) | Move to dispute phase, empathise, explain separate dispute path, offer email escalation. | Continue trying to collect payment. |
| Language barrier after switch | Attempt switch; if still incomprehensible after 2-3 exchanges, offer to callback or escalate. | Keep saying the same thing louder in a language the customer doesn't understand. |
| Death of co-borrower/payer | Offer sincere condolences first. Give email for documentation. Do NOT push credit pressure immediately. | Pivot to credit score argument within 2 turns of learning about the death. |
| Blank call / no response | Three "Hello?" attempts → ask for customer name → end call with `voicemail`. | Repeat full pitch to silence. |

**N/A case**: If no edge case occurred, award full **10 points**.

---

## Dimension 7 — No Unnecessary Repetition (0–10)

| Score | Criteria |
|-------|----------|
| 10    | No repeated phrases. Every agent turn is distinct. |
| 7     | 1–2 minor repetitions (e.g., restating amount once after connectivity issue). |
| 3     | Same question or statement appears 3+ times verbatim or near-verbatim. |
| 0     | Call is dominated by repetition. Agent makes no progress across many turns. |

**Scoring note**: Restating something ONCE after a connectivity issue ("Hello? Can you hear me?") is acceptable and should NOT count as repetition. Only count it if the same substantive content (not just "Hello?") is repeated without new information added.

---

## Dimension 8 — Resolution Quality (0–10)

| Score | Criteria |
|-------|----------|
| 10    | Resolution is clear, specific, and correct for the situation: PTP with date/amount confirmed; callback with specific date/time; dispute noted with support path offered; wrong number ended cleanly. |
| 7     | Resolution reached but lacks specifics (e.g., "end of month" callback without a specific date). |
| 3     | Vague resolution. Borrower's intent unclear at end of call. |
| 0     | No resolution. Call ends abruptly or in mid-conversation confusion. |

---

## Dimension 9 — Call Efficiency (0–5)

| Score | Criteria |
|-------|----------|
| 5     | Call length appropriate to outcome achieved. |
| 3     | Somewhat long for the outcome, or slightly rushed for a complex case. |
| 0     | Grossly miscalibrated: e.g., 15 minutes (105 turns) with no resolution and escalating customer frustration; OR 9 turns total when the borrower needed more probing. |

**Reference benchmarks** (from the 10 calls):
- Simple wrong number → should end in <15 turns ✓ (call_08 did well)
- Dispute with resolution → 15–25 turns is appropriate
- Full PTP with empathy → 25–45 turns is appropriate
- "Already paid" claim → should resolve to support escalation in <20 turns

---

## Verdict Threshold

```
score >= 60  →  verdict = "good"
score < 60   →  verdict = "bad"
```

This threshold was calibrated against the human verdicts. The five "bad" calls (02, 03, 07, 09, 10)
all share systemic failures in at least two major dimensions, pushing them below 60 reliably.

---

## Re-implementation Notes

If you reimplement this rubric, you should get similar results by:

1. **Annotating language switch latency**: Count the number of customer turns between the first non-English response and the `switch_language` function call. > 2 turns = deduction.
2. **Counting repetition**: Tokenize agent turns and flag if any 5-gram appears 3+ times.
3. **Checking discovery depth**: Count genuinely distinct discovery questions asked before `proceed_to_negotiation`. < 2 questions = 5 pts or below.
4. **Checking edge case completion**: For each edge case type, verify the 2–3 mandatory steps were taken (per the table in Dimension 6).
5. **Checking efficiency**: `total_turns` divided by a baseline per outcome type. Ratios > 2× baseline = 0 pts.
