"""Level 2: improve the AGENT, but with a FIXED improver (OPRO / APE style). Self-improvement, not yet recursive.

The agent is a block of instructions. A hand-written meta-prompt (META below) reads
the failures and rewrites the instructions, and the change is kept if the score
doesn't drop. The improvement persists, unlike Level 1. Two ceilings remain:
  1. The agent can only change words. It can't give itself a calculator or code runner,
     so the SHA-256 and prime tasks stay out of reach.
  2. META never changes. The way the agent improves is as good as it will ever get.
Level 3 removes both limits.

    python 02_self_improving_prompt.py
"""
import random
from concurrent.futures import ThreadPoolExecutor

from benchmark import grade, make_tasks
from llm import llm

tasks = make_tasks(seed=random.randrange(10**9))


def evaluate(instructions: str) -> tuple[float, str]:
    with ThreadPoolExecutor(8) as pool:
        answers = list(pool.map(lambda t: llm(f"{instructions}\n\n{t[0]}"), tasks))
    fails = [f"Q: {q[:150]}\nGot: {a.strip()[:150]}\nExpected: {e}" for (q, e), a in zip(tasks, answers) if not grade(a, e)]
    return 1 - len(fails) / len(tasks), "\n\n".join(fails)


META = """You are optimizing the instructions given to an AI assistant.
Current instructions:
{instructions}

Current score: {score:.0%}. Failures:
{failures}

Write better instructions. Reply with ONLY the new instructions."""

instructions = "Reply with only the final answer, nothing else."
score, failures = evaluate(instructions)
print(f"step 0: {score:.0%}  {instructions!r}")
for step in range(1, 6):
    candidate = llm(META.format(instructions=instructions, score=score, failures=failures), effort="high")
    cand_score, cand_failures = evaluate(candidate)
    if cand_score >= score:  # greedy hill-climbing: keep the best so far
        instructions, score, failures = candidate, cand_score, cand_failures
    print(f"step {step}: candidate {cand_score:.0%} -> best {score:.0%}")
print(f"\nFinal instructions ({score:.0%}):\n{instructions}")
