# Personal Finance Decision Engine
A system that turns raw spending data into defensible financial decisions, not just insights.

## Key distinction:
This is not a tracker and not a chatbot. It’s a decision engine with explicit reasoning.

## What it actually does
* Normalizes financial reality
    * Ingests transactions
    * Categorizes with confidence scores
    * Tracks recurring vs discretionary spend
* Builds a user financial model
    * Fixed vs variable costs
    * Savings rate, burn rate, cash runway
    * Behavioral patterns (weekends, subscriptions, drift)
* Generates decisions, not tips
    * “You should cap dining at $X because it reduces savings below Y%”
    * “Cancel subscription A before date B to avoid waste”
    * Every recommendation has a justification chain
* Explains tradeoffs
    * “If you keep spending pattern A, goal B is delayed by C months”
    * Scenario comparisons, not advice dumping

## How it works (if it’s not a tracker and not a chatbot)
Think of it as a decision service, not an interface.

### Operating modes
1. Scheduled evaluation (default)
    * Periodically ingests new transactions
    * Recomputes financial state
    * Emits decisions when thresholds are crossed
* Example: “Spending drift detected → dining exceeds plan by 18% → recommend cap or offset”

2. Event-driven evaluation
    * Triggered by specific events:
    * New large transaction
    * Subscription renewal upcoming
    * Goal risk detected

3. On-demand decision queries
    * You ask a specific question
    * The engine evaluates it against current constraints

### Making it a dynamic agent (without turning it into a chatbot)
The key: **structured inputs, structured outputs.**

``` markdown
- “Is this hat worth buying?”
```

What actually happens:
* Input is normalized into a decision request, not free chat:
    * Item cost
    * Category
    * Timing
* Optional subjective weight (“I really want it”)
    * Engine evaluates:
    * Current discretionary budget
    * Impact on savings rate
    * Goal delays or conflicts

* Output is a decision with rationale:
    * Approve / discourage / warn
    * Explicit tradeoffs (“delays trip by 2 weeks”)

The LLM only:
* Translates your natural language → structured request
* Explains the result in human terms