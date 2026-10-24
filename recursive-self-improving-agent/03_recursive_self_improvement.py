"""Level 3: recursive self-improvement (a minimal Darwin Gödel Machine).

    repeat:
      1. pick a parent agent from the archive (favouring high scores and agents with few children yet)
      2. the parent runs ITS OWN improve() on ITS OWN source code    <- the recursive step
      3. score the child on the benchmark, in a separate process
      4. if it runs, add it to the archive (even if it scored worse: it may be a stepping stone)

improve() lives inside the code being improved, so one change can make an agent better
at the task AND better at improving itself. Everything in this file is the frozen outer
loop: the agent can never rewrite its own grader or its own selection rule.

    python 03_recursive_self_improvement.py          # RSI_ITERATIONS=8 by default
"""
import json
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from benchmark import grade, make_tasks

HERE = Path(__file__).parent
ITERATIONS = int(os.environ.get("RSI_ITERATIONS", 8))
RUN_DIR = HERE / "runs" / time.strftime("%Y%m%d-%H%M%S")
# Secret per-run seeds: the agent sees questions but can't regenerate the answers.
DEV_SEED, TEST_SEED = random.randrange(10**9), random.randrange(10**9)

# Runs inside the child process: load the agent file, call one of its functions.
WORKER = """
import importlib.util, json, sys
from concurrent.futures import ThreadPoolExecutor
spec = importlib.util.spec_from_file_location("agent", sys.argv[1])
agent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent)
args = json.load(sys.stdin)
def safe_solve(q):
    try:
        return str(agent.solve(q))
    except Exception as e:
        return f"ERROR: {e!r}"
if sys.argv[2] == "solve":
    with ThreadPoolExecutor(8) as pool:
        out = list(pool.map(safe_solve, args))
else:
    out = agent.improve(*args)
json.dump(out, open(sys.argv[3], "w"))
"""


def sandboxed(agent_file: Path, fn: str, args, timeout: int = 900):
    """Run untrusted agent code in a subprocess, so a broken or looping agent can't take down the loop.
    (A process is not a real security boundary. Use a container or VM for anything serious.)"""
    with tempfile.NamedTemporaryFile(suffix=".json") as out:
        proc = subprocess.run([sys.executable, "-c", WORKER, str(agent_file), fn, out.name], cwd=HERE,
                              input=json.dumps(args), capture_output=True, text=True, timeout=timeout)
        if proc.returncode != 0:
            raise RuntimeError(proc.stderr[-1500:])
        return json.load(open(out.name))


def evaluate(agent_file: Path, seed: int) -> tuple[float, str]:
    """Score the agent and write the feedback its improve() will read."""
    tasks = make_tasks(seed)
    answers = sandboxed(agent_file, "solve", [q for q, _ in tasks])
    fails = [(q, a, e) for (q, e), a in zip(tasks, answers) if not grade(a, e)]
    score = 1 - len(fails) / len(tasks)
    report = "\n".join(f"- Q: {q[:200]}\n  agent answered: {a[:200]!r}\n  expected: {e}" for q, a, e in fails)
    return score, f"Score: {score:.0%} ({len(tasks) - len(fails)}/{len(tasks)} correct)\nFailures:\n{report or 'none'}"


def main():
    RUN_DIR.mkdir(parents=True)
    archive = {}  # id -> every working agent ever made. Agent #n lives in agent_<n>.py

    def try_add(source: str, parent: int | None, id: int):
        path = RUN_DIR / f"agent_{id:02d}.py"
        path.write_text(source)
        compile(source, path.name, "exec")  # syntax check before spending money on evaluation
        assert "def solve" in source and "def improve" in source, "child lost solve() or improve()"
        score, feedback = evaluate(path, DEV_SEED)
        archive[id] = dict(id=id, file=path.name, parent=parent, score=score, children=0, feedback=feedback)
        print(f"  + agent #{id} ({'seed' if parent is None else f'child of #{parent}'}): dev score {score:.0%}")

    print(f"run dir: {RUN_DIR}\n[seed]")
    try_add((HERE / "seed_agent.py").read_text(), None, 0)

    for it in range(1, ITERATIONS + 1):
        # Open-ended selection: high scorers are likely, but every agent gets a chance.
        # A purely greedy loop (always take the best) gets stuck in local optima.
        agents = list(archive.values())
        weights = [(a["score"] + 0.05) / (1 + a["children"]) for a in agents]
        parent = random.choices(agents, weights=weights)[0]
        parent["children"] += 1
        print(f"[iteration {it}] parent #{parent['id']} ({parent['score']:.0%}) is rewriting itself...")
        try:
            parent_file = RUN_DIR / parent["file"]
            child_source = sandboxed(parent_file, "improve", [parent_file.read_text(), parent["feedback"]])
            try_add(child_source, parent["id"], it)
        except Exception as e:  # broken children are discarded, which is natural selection at its simplest
            print(f"  x child discarded: {str(e).strip().splitlines()[-1][:200]}")
        (RUN_DIR / "archive.json").write_text(json.dumps(archive, indent=2))

    best = max(archive.values(), key=lambda a: a["score"])
    lineage, node = [], best
    while node is not None:
        lineage.insert(0, f"#{node['id']} ({node['score']:.0%})")
        node = archive.get(node["parent"])
    print("\nlineage of best agent:", " -> ".join(lineage))
    # Held-out tasks the improvers never saw. Did the agent improve, or just overfit to dev?
    print(f"held-out test: seed agent {evaluate(RUN_DIR / 'agent_00.py', TEST_SEED)[0]:.0%}"
          f"  vs  best agent {evaluate(RUN_DIR / best['file'], TEST_SEED)[0]:.0%}")
    print(f"diff them:  diff {RUN_DIR / 'agent_00.py'} {RUN_DIR / best['file']}")


if __name__ == "__main__":
    main()
