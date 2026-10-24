"""Level 1: improve the OUTPUT (Self-Refine / Reflexion style). Not RSI.

draft -> critique -> rewrite, repeated. The answer gets better, but the agent
doesn't. Ask a new question and it starts from zero again. Nothing persists.

    python 01_self_refine.py ["your question"]
"""
import sys

from llm import llm

A, B = 738261904417, 551902377163
question = sys.argv[1] if len(sys.argv) > 1 else f"What is {A} * {B}?"

answer = llm(question)
print(f"--- first draft ---\n{answer}\n")
for step in range(3):
    critique = llm(f"Question: {question}\nAnswer: {answer}\n\nFind any mistakes in this answer. Be specific.")
    answer = llm(f"Question: {question}\nAnswer: {answer}\nCritique: {critique}\n\nWrite an improved answer.")
    print(f"--- refinement {step + 1} ---\n{answer}\n")
if len(sys.argv) == 1:
    print("true answer:", A * B)
