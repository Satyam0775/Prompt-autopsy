# System Prompt Flaw Analysis

File analyzed: `system-prompt.md`  
Evidence transcripts: call_02, call_03, call_07, call_09, call_10

The original system prompt contains several design flaws that directly caused
failures in the bad calls. Each flaw below includes transcript evidence,
the root cause, and the fix implemented in `system-prompt-fixed.md`.

---

# Flaw 1 — Language Switching Happens Too Late

## Evidence

### call_02
Customer repeatedly requested Hindi:

> "मैं बार बार request कर रही हूं आपको हिंदी में बात करिए"

The agent switched languages multiple times and continued returning to English.

The function `switch_language` was called three different times during the call,
showing that language switching was unstable.

---

### call_07
Customer asked:

> "Do you know Tamil?"

The agent continued speaking English for several turns before switching.

---

## Root Cause

The system prompt defines the `switch_language` function but does **not define when
it must be triggered**. As a result, the agent delays switching or switches
multiple times.

---

## Fix

Add a strict rule:

- Detect the customer's language on the **first response**
- Call `switch_language` immediately if needed
- After switching, **do not revert to English unless the customer asks**

---

# Flaw 2 — No Protocol for "Already Paid" Claims

## Evidence

### call_03
The customer repeatedly provided a UTR number.

The agent kept responding:

> "I cannot find this payment."

The conversation lasted **over 15 minutes** with the agent repeatedly asking
for the same UTR number.

No escalation or call resolution occurred.

---

### call_02
The borrower claimed the loan had already been paid by her deceased husband.
The agent acknowledged the statement but returned to collection pressure
instead of escalating the case.

---

## Root Cause

The prompt assumes the agent can verify payments in real time, which it cannot.
Because no escalation rule exists, the agent enters a **verification loop**.

---

## Fix

Add an **Already Paid Protocol**:

1. Ask for the UTR number once
2. Tell the borrower to email payment proof to support
3. Escalate to human verification
4. End the call with `end_call(reason="claims_already_paid")`

Also add a rule to handle sensitive cases such as a family death with empathy.

---

# Flaw 3 — Callback Calls Treated Like Cold Calls

## Evidence

### call_09
The call was a scheduled callback.

Agent opening:

> "Hi Kavita Menon, this is Alex from DemoCompany. You had asked us to call you back."

However, the agent immediately restarted the **entire cold-call script**, repeating
the loan explanation multiple times.

Customer reaction:

> "Yeah. Saturday evening also, you will call. Right?"

The agent did not adapt to the callback context.

---

## Root Cause

The prompt only defines behaviour for **cold outbound calls**.
There is no phase or rule for **scheduled callbacks**.

---

## Fix

Add a new phase: **Callback Opening**

Example:

"Hi [Name], Alex calling you back as requested. Ready to continue?"

Then continue directly to negotiation or discovery without repeating the
entire collection script.

---

# Flaw 4 — No Minimum Discovery Requirement

## Evidence

### call_10

The customer responded:

> "I can't say."

The agent did not probe further and ended discovery early.

The call ended after only **9 turns** without understanding the borrower's
financial situation.

---

## Root Cause

The prompt defines the maximum discovery effort but does **not define a minimum**.

This allows the agent to move to closing too quickly.

---

## Fix

Require the agent to establish:

- the reason for non-payment
- whether the situation is temporary or long-term
- a possible repayment timeline

Minimum **3 discovery exchanges** before negotiation.

---

# Flaw 5 — Missing Mandatory `end_call`

## Evidence

### call_02

Manifest disposition: **BLANK_CALL**

However, the transcript shows a long real conversation.

Because `end_call` was never triggered, the system recorded the call
incorrectly.

---

## Root Cause

The system prompt does not require `end_call` to be called on every call.

---

## Fix

Add a rule:

Every call **must end with `end_call`**.

Even if the borrower disconnects, the agent must trigger `end_call`
before the turn finishes.

---

# Summary of Identified Prompt Failures

| Flaw | Evidence | Impact |
|-----|------|------|
| Language switching delay | call_02, call_07 | Confusing multilingual interactions |
| No already-paid protocol | call_03 | Infinite verification loop |
| Callback treated as cold call | call_09 | Frustrated borrower |
| Weak discovery | call_10 | Agent gives up too early |
| Missing end_call rule | call_02 | Incorrect call disposition |

---

# Conclusion

The original system prompt fails because it lacks:

- clear language switching rules
- escalation protocols for payment disputes
- callback handling logic
- minimum discovery requirements
- mandatory call termination rules

These issues were corrected in `system-prompt-fixed.md`.