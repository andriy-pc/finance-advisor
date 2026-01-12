# LLM Constraints and Responsibilities

## Purpose of This Document

This document explains **why and how Large Language Models (LLMs) are deliberately constrained** in the *Personal
Finance Decision Engine* project.

The goal is not to downplay the role of AI, but to **use LLMs responsibly and intentionally** in a system that deals
with financial data, correctness, and user trust.

This document should be read alongside [README.md](./README.md). Together, they describe *what the system does* and *why the LLM is
designed the way it is*.

---

## Core Principle

> **The LLM is not the brain. It is the interface and narrator.**

All financial reasoning, decisions, and state changes are handled by **deterministic application code**.
The LLM exists to make that system usable by humans.

This separation is intentional and foundational.

---

## Why the LLM Is Not the Brain

### 1. Determinism and Correctness

Financial systems require:

- Predictable behavior
- Reproducible decisions
- Clear explanations for *why* something happened

LLMs are:

- Probabilistic
- Non-deterministic
- Sensitive to phrasing and context

Allowing an LLM to:

- Decide budgets
- Perform calculations
- Mutate financial state

would make the system **untestable and unsafe**.

Therefore:

- All calculations are deterministic
- All constraints are explicit
- All decisions are reproducible

---

### 2. Auditability and Trust

Users must be able to ask:
> “I want to by X that costs Y, how does it impact my budget/goals?”

The system must answer with:

- Concrete numbers
- Explicit thresholds
- Clear tradeoffs

If an LLM were the decision-maker:

- There would be no audit trail
- Decisions would be difficult to justify
- Errors would be hard to detect

By constraining the LLM:

- Every decision can be traced to data and rules
- User trust is preserved
- The system remains explainable

---

### 3. Separation of Concerns

This project enforces a strict separation:

| Concern                 | Responsible Component |
|-------------------------|-----------------------|
| Financial state         | Application code      |
| Budget rules            | Application code      |
| Goal evaluation         | Application code      |
| Decision logic          | Application code      |
| Natural language input  | LLM                   |
| Natural language output | LLM                   |

This separation makes the system:

- Easier to reason about
- Easier to test
- Easier to evolve

---

## What the LLM Is Allowed to Do

The LLM is intentionally limited to **human-facing tasks**.

### 1. Intent Parsing

The LLM converts natural language into a **structured intent** from a closed set.

Example:

```json
{
  "intent": "evaluate_purchase",
  "amount": 80,
  "category": "discretionary"
}
```

Rules:

* Only supported intents are allowed
* Missing information triggers clarification
* No assumptions are silently made

### 2. Explanation and Narration

The LLM explains:

* Decisions produced by the engine
* Tradeoffs and impacts
* Financial summaries derived from structured data

The LLM does not invent reasons.
It translates structured outputs into human-readable text.

### 3. Clarification

When required data is missing or ambiguous, the LLM may ask:

* Follow-up questions
* Narrow clarification prompts

* This is a controlled interaction loop, not free-form conversation.

## What the LLM Is Explicitly Forbidden to Do

The LLM must never:

* Perform financial calculations
* Decide whether an action is “good” or “bad”
* Modify financial state
* Execute operations
* Create or adjust budgets
* Invent goals or constraints
* Reason outside provided structured data

Any of the above would break:

* Determinism
* Testability
* User trust

## Why the Intent Set Is Narrow

The system supports a closed set of user intents by design.

Reasons:

* Prevents misinterpretation
* Makes behavior predictable
* Allows precise validation
* Enables safe refusal

Unsupported requests are:

* Rejected
* Or clarified

This is not a limitation — it is a correctness feature.