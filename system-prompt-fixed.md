# System Prompt Flaw Analysis

**File analyzed**: `system-prompt.md`  
**Evidence from**: call_02, call_03, call_07, call_09, call_10

---

## Flaw 1 — Language Switch Has No Trigger Rule and No Stability Rule

### What the prompt says
The global prompt mentions `switch_language` exists as a function. The Opening phase
has zero instruction about WHEN to call it. There is no rule about how quickly to switch
or what to do after switching.

### What went wrong

**call_07 (Meera Joshi / Tamil):**
- Customer asked `"do you know Tamil?"` on turn ~15.
- Agent switched to Tamil only at turn 19 — 4 full English turns after the explicit request.
- After switching, the Tamil conversation went nowhere. No resolution reached.
- Human verdict: *"Language barrier not handled well. No fallback strategy."*

**call_02 (Rahul Verma / Hindi):**
- Customer's 2nd message: `"Hello? Please amount repeat."` — clearly struggling with English.
- Agent's next turn was broken code-mixed gibberish:
  `"Theek नमस्ते, hai, main aapke आपके saath अट्ठाईस Hindi mein baat हज़ार karta hoon. पाँच"`
- `switch_language("hi")` was called **3 times** across the call (turns 4, 10, 23).
- Agent kept reverting to English after each switch.
- Customer explicitly complained:
  *"मैं बार बार request कर रही हूं आपको हिंदी में बात करिए, लेकिन आप english में repeat करे चले जा रहे हैं."*

**call_03 (Anjali Reddy / Tamil → Hindi):**
- `switch_language("ta")` at turn 1 (good start), then `switch_language("hi")` at turn 20,
  then `switch_language("ta")` again at turn 86 — three language switches total.
- Customer had to repeatedly beg the agent to speak her language and slow down.

### Root cause in the prompt
No instruction says: *"detect the customer's language on the very first response and
switch immediately."* No stability rule says: *"once switched, never revert."*
The LLM treats language switching as a background feature rather than a top-priority action.

### Fix added in `system-prompt-fixed.md` — `[FIX 1]`

Added **LANGUAGE DETECTION — HIGHEST PRIORITY RULE** to Global System Prompt:

> On your VERY FIRST interaction, detect the language of the customer's response.  
> If the customer responds in Hindi / Tamil / Telugu / Kannada / Bengali / Marathi:  
> 1. Call `switch_language` IMMEDIATELY — before your next spoken response.  
> 2. Stay in that language for the ENTIRE call. Do NOT revert to English.  
> 3. Call `switch_language` ONLY ONCE per call.  
> If the customer explicitly says "speak in Hindi" / "हिंदी में बात करिए" / "தமிழ்ல பேசு"
> — this is a direct instruction. Switch immediately and stay switched.

---

## Flaw 2 — No Escalation Path for "Already Paid" Claims

### What the prompt says
Opening phase mentions `end_call` with reason `claims_already_paid` but gives NO protocol
for how to get there. The agent is implicitly expected to "verify" UTR numbers in real-time
— which it absolutely cannot do.

### What went wrong

**call_03 (Anjali Reddy) — the smoking gun:**
- Duration: **901 seconds (15 minutes)**, 105 turns.
- Customer provided UTR number `CM552522` repeatedly across 30+ turns.
- Agent kept responding: *"मुझे इस नंबर से कोई भुगतान नहीं मिल रहा है"*
  ("I can't find this payment") — then asked for the UTR again.
- The call ended with no `end_call` function call — abrupt cutoff with zero resolution.
- Human verdict: *"Agent loops instead of escalating."*

**call_02 (Rahul Verma):**
- Customer's husband had died; she claimed the loan was paid via PhonePe.
- Agent empathised but then immediately pivoted to:
  *"six hundred and sixty-eight days past due, every month adds another negative entry"*
  — said within 2 turns of hearing about the husband's death.
- Eventually gave the support email but only after an exhausting 82-turn call.
- No `end_call` was ever called — call ended without a proper closing function.

### Root cause in the prompt
The prompt never tells the agent: *"you cannot verify UTR numbers in real-time."*
Without this explicit constraint, the LLM improvises a fake "verification loop"
that goes on indefinitely. There is also no maximum-exchange limit for this scenario.

### Fix added in `system-prompt-fixed.md` — `[FIX 2]`

Added **ALREADY PAID PROTOCOL** to the Discovery phase:

> 1. Acknowledge: "I'm sorry for the confusion. Can you share a UTR/reference number?"  
> 2. Note it once. Do NOT ask again.  
> 3. Say: "Please email that to support@demolender.com with your payment screenshot.
>    Our team verifies within 24–48 hours and will ensure no further calls."  
> 4. Call `end_call(reason="claims_already_paid")`.  
>
> **CRITICAL**: You CANNOT verify payments in real-time. Do not pretend to check.
> Maximum 2 exchanges on this topic before directing to support and ending.

Also added: if a customer discloses the death of a family member, acknowledge sincerely
for at least 2 turns before any mention of financial obligations or credit impact.

---

## Flaw 3 — No Callback Context Protocol

### What the prompt says
The Opening phase has exactly one greeting template — designed for cold outbound calls.
There is no phase, no flag, and no instruction for **scheduled callback calls** where the
borrower already has context from a prior conversation.

### What went wrong

**call_09 (Kavita Menon):**
- Disposition: `INQUIRY`. Phases include `callback_opening`.
- Agent opened with the full cold-call script:
  *"I see you have fifty thousand rupees pending. There might be some penalty and
  delay charges included in this."* — re-pitching from scratch.
- Customer responded sarcastically: *"Yeah. Saturday evening also, you will call. Right?"*
  — clearly frustrated at being treated as a new cold lead.
- Agent repeated the same intro **twice more** (turns 6 and 7), ignoring her signal.
- No `proceed_to_negotiation` called at start despite `callback_opening` in phases.
- Only 1 function call in the entire call: `end_call` at turn 36 with no prior resolution.
- Human verdict: *"Agent doesn't adapt to the context. Connection drops, no recovery."*

### Root cause in the prompt
There is no `callback_opening` phase. When the call is a callback, the agent has no
instruction to skip re-introductions or jump directly to negotiation. The LLM defaults
to the cold-call Opening script because that is the only opening it knows.

### Fix added in `system-prompt-fixed.md` — `[FIX 3]`

Added new **Phase 0: Callback Opening** (before existing Opening phase):

> Use this phase when `is_callback = true`.  
> Do NOT re-introduce yourself at length.  
> Opening line: "Hi [Name], Alex calling you back as requested. Ready to continue?"  
> Move DIRECTLY to Negotiation if prior intent to pay existed, or Discovery if unclear.  
> Do NOT restart the full collection pitch. The borrower knows why you are calling.

---

## Flaw 4 — No Minimum Discovery Requirement

### What the prompt says
Discovery phase: *"After 5-6 genuinely circular exchanges where the borrower repeats
the same point without progress, call proceed_to_negotiation."*

This defines the **maximum** effort before giving up. Nothing defines the **minimum**
effort required before proceeding. Nothing prevents jumping to Negotiation after 2 turns.

### What went wrong

**call_10 (Ravi Gupta):**
- Total turns: **9**. Duration: **110 seconds**.
- Customer said *"I can't say"* (possible speech recognition error). Agent never probed.
- After customer got irritated (*"You asked me a question. Why are you pulling out my
  account details now?"*), agent immediately called `proceed_to_closing` with
  `resolution_type: "needs_time"`.
- Agent never established: why the borrower can't pay, whether temporary or permanent,
  any timeline, or what amount they could manage.
- Human verdict: *"Agent doesn't dig into why the customer is evasive. Gives up too quickly."*

### Root cause in the prompt
The "5-6 circular exchanges" rule was designed to prevent infinite loops, but it
inadvertently signals that getting to `proceed_to_negotiation` quickly is fine.
Nothing sets a floor: the agent has no requirement to actually understand the borrower
before moving on.

### Fix added in `system-prompt-fixed.md` — `[FIX 4]`

Added **MINIMUM DISCOVERY REQUIREMENT** to the Discovery phase:

> Do NOT call `proceed_to_negotiation` until you have established:  
> 1. The borrower's stated reason for non-payment  
> 2. Whether the situation is temporary or ongoing  
> 3. An approximate timeline (when do they expect income or resolution?)  
>
> Minimum 3 genuine discovery exchanges before `proceed_to_negotiation`.  
> If the borrower gives vague or one-word responses, probe:
> "I want to make sure I can help — could you tell me a bit more about what's been happening?"  
> If their response is confusing, do NOT interpret it as positive. Ask one clarifying question.

---

## Flaw 5 — Missing Mandatory end_call + Broken Disposition Logic

### What the prompt says
Closing phase says: *"After closing remarks, call end_call."*
There is no rule that `end_call` is **mandatory on every call without exception**.
If `end_call` is never called, the disposition the system assigns is undefined.

### What went wrong

**call_02 (Rahul Verma):**
- Disposition in the manifest: **`BLANK_CALL`**
- Actual transcript: **154 lines** of real conversation in Hindi.
- `end_call` was never called — the call just stopped mid-conversation.
- Because no `end_call` was fired with a reason, the system fell back to `BLANK_CALL`
  — the complete opposite of what happened.

**call_08 (Suresh Rao / Wrong Number):**
- Global prompt says: *"NEVER disclose amounts to anyone other than the confirmed borrower."*
- But Discovery phase header says: *"You have already disclosed the amounts."*
- This contradiction caused the agent to state the pending amount to the wrong person
  before identity confusion was even resolved.

### Root cause in the prompt
No rule says: *"every call, no matter how it ends, must terminate with end_call."*
The agent treats it as optional. Also, the identity-check rule in the global prompt is
contradicted by an assumption in the Discovery phase header.

### Fix added in `system-prompt-fixed.md` — `[FIX 5]`

Added to Closing phase:

> **ALWAYS CLOSE WITH A FUNCTION CALL:**  
> Every call must end with `end_call`. No exceptions.  
> If the borrower disconnects mid-call, still call `end_call` with the appropriate reason.

Added to Opening phase:

> **IDENTITY VERIFICATION BEFORE AMOUNT DISCLOSURE:**  
> Confirm you are speaking with `{{customer_name}}` before stating any loan amounts.  
> If the person denies being `{{customer_name}}`:  
> call `end_call(reason="wrong_party")` immediately. Share NO loan details.

---

## Flaw → Transcript Mapping

| # | Flaw | Primary Evidence | Secondary Evidence |
|---|------|------------------|--------------------|
| 1 | No language switch trigger or stability rule | call_07 (Tamil ignored 4 turns) | call_02 (3 switch calls), call_03 (3 language switches) |
| 2 | No already-paid escalation path | call_03 (15-min UTR loop, no end_call) | call_02 (82 turns, no end_call, credit pressure after death) |
| 3 | No callback opening phase | call_09 (cold-call script on return call) | — |
| 4 | No minimum discovery requirement | call_10 (gave up in 9 turns) | — |
| 5 | No mandatory end_call + broken disposition | call_02 (BLANK_CALL despite 154-line call) | call_08 (amount disclosed to wrong person) |