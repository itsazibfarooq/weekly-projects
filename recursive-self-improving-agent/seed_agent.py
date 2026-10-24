"""Generation 0 of the self-improving agent.

THIS WHOLE FILE IS WHAT GETS IMPROVED, including improve() itself. Every new agent
is a rewritten copy of this file. The harness (03_recursive_self_improvement.py)
only relies on these two functions:

    solve(question) -> str            answer one task
    improve(source, feedback) -> str  return the full source code of a better agent
"""
from llm import llm


def solve(question: str) -> str:
    return llm(f"{question}\n\nReply with only the final answer, nothing else.").strip()


def improve(source: str, feedback: str) -> str:
    prompt = f"""You are a self-improving AI agent. This is your own source code:

<source>
{source}
</source>

This is how that code did on a benchmark of tasks:

<feedback>
{feedback}
</feedback>

Write an improved version of the code that will score higher on new, unseen tasks of the same kinds.
You may change anything, including improve() itself, which will be used to create your future versions.
Keep these signatures working: solve(question: str) -> str and improve(source: str, feedback: str) -> str.
Available: Python 3 standard library, and `from llm import llm`, where llm(prompt, effort="low") -> str
(effort can be "low", "medium", "high", "xhigh" or "max"; higher is smarter but slower).

Reply with the complete new file between <new_agent> and </new_agent> tags. Raw Python only, no markdown fences."""
    reply = llm(prompt, effort="high")
    return reply.split("<new_agent>", 1)[1].rsplit("</new_agent>", 1)[0].strip() + "\n"
