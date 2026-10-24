# Recursive Self-Improving Agents: the smallest working version

About 300 lines of Python in three steps, ending in an agent that rewrites its own source code,
including the part that does the rewriting. This README covers the theory, the research it
comes from, and exactly how the example works.

```
01_self_refine.py              Level 1: improves its ANSWER                (not RSI)
02_self_improving_prompt.py    Level 2: improves its PROMPT, fixed improver (self-improvement)
03_recursive_self_improvement.py + seed_agent.py
                               Level 3: improves its CODE, improver included (recursive self-improvement)
llm.py        frozen: the one function that calls the model
benchmark.py  frozen: tasks plus a grader the agent cannot touch
```

## 0. Quick start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...       # or: ant auth login
python 01_self_refine.py                  # ~1 minute
python 02_self_improving_prompt.py        # ~5 minutes
RSI_ITERATIONS=3 python 03_recursive_self_improvement.py   # start small, then try 8-20
```

Each run of Level 3 writes every agent it creates to `runs/<timestamp>/agent_NN.py`, plus
`archive.json` (scores, parents, and the feedback each agent saw). **Reading those files is the
real lesson.** `diff runs/<ts>/agent_00.py runs/<ts>/agent_07.py` shows what the agent decided
to change about itself.

Cost: the default model is `claude-opus-5-5`. A run makes roughly 20 to 40 cheap calls per
evaluation plus one expensive rewrite call per iteration, so expect a few dollars for 8
iterations. `RSI_MODEL=claude-sonnet-5-5` costs about half as much.

---

## 1. The idea in one paragraph

A **self-improving** agent gets better at a task by changing something about itself, such as
its prompt, memory, tools or code. A **recursively** self-improving agent can also change the
part of itself that makes those changes. Then the improvements can compound: a better improver
makes better agents, and those agents contain better improvers. In this repo the agent is a
Python file with two functions, `solve()` and `improve()`. The harness asks an agent to run its
own `improve()` on its own source code. That produces a new file, and the new file's `improve()`
is what creates the next generation.

## 2. The ladder: what gets improved, and who improves it

| Level | What changes | Who changes it | Persists? | Improver changes too? | Examples |
|---|---|---|---|---|---|
| 0 | nothing | nobody | – | – | a plain LLM call |
| 1 | the **output** | the model, through critique | no | no | Self-Refine, Reflexion → `01_self_refine.py` |
| 2 | a **prompt, memory or skill library** | a fixed, human-written optimizer | yes | **no** | OPRO, APE, DSPy, Voyager, ADAS → `02_self_improving_prompt.py` |
| 3 | the agent's **code, including the improver** | the agent itself | yes | **yes** | STOP, Gödel Agent, DGM, SICA, HGM, AIDE² → `03_...py` |
| 4 | the **model weights** | the model, through self-generated data or rewards | yes | yes, partly | STaR, Self-Rewarding LMs, SEAL, Absolute Zero |

The jump from Level 2 to Level 3 is the one that matters. In Level 2 the line
`META = """You are optimizing..."""` is written by a human and never changes, so the best the
system can ever get is limited by how good that one prompt is. In Level 3 the equivalent
prompt sits inside `seed_agent.py`'s `improve()`, and it gets rewritten along with everything else.

Level 4 is what people usually mean by an "intelligence explosion". Levels 1 to 3 all keep the
model weights frozen (see `llm.py`). Level 3 is sometimes called **harness-level** or
**scaffold-level RSI**. It is what most current agent research does, because it is cheap,
inspectable, and needs no training.

## 3. Theory

### 3.1 A definition you can write down

An agent at generation *t* is a program `A_t = (solve_t, improve_t)`. The update rule is

```
A_{t+1} = improve_t(A_t, feedback(A_t))
```

* If `improve_t` is the same for every *t*, this is **self-improvement**: hill-climbing with a fixed optimizer.
* If `improve_t` is **part of what gets rewritten**, so that `improve_{t+1}` comes out of
  `improve_t(...)`, this is **recursive self-improvement**. The optimizer optimizes itself.

Two scores matter, and they can disagree:

* **Performance**: how well `solve_t` does on the task.
* **Metaproductivity**: how good the *descendants* of `A_t` turn out to be, which measures how
  good `improve_t` is. The Huxley-Gödel Machine (2025) showed that the highest-scoring agent is
  often **not** the best parent. They call this the *metaproductivity–performance mismatch*.

### 3.2 Why "recursive" can compound

Suppose each generation, the improver finds changes worth a gain of `g`. With a fixed improver,
`g` stays roughly constant or shrinks as easy wins run out, so progress is about linear and then
plateaus. If some changes also raise `g` itself (better failure analysis, testing candidate
changes before submitting them, thinking harder when rewriting), later gains get bigger. That
feedback loop is the whole argument behind I. J. Good's 1965 "intelligence explosion". Whether it
keeps going or levels off depends on whether improving the improver gets easier or harder over
time. That is an open empirical question, and the papers in section 5 are measuring it.

### 3.3 From the Gödel Machine to the Darwin Gödel Machine

* **Gödel Machine** (Schmidhuber, 2003): a program that rewrites any part of itself, but only after
  it has *proved* that the rewrite is better. This is optimal in theory and impossible in practice,
  because such proofs almost never exist for real-world code.
* **Darwin Gödel Machine** (Zhang, Hu, Lu, Lange, Clune, 2025): replace the proof with an
  **experiment**. Try the rewrite, measure it on a benchmark, and keep it if it works. Add
  Darwinian **open-ended search**: keep an archive of every working variant, not just the best one,
  because a mediocre agent can be the stepping stone to a great one. DGM improved SWE-bench from
  20.0% to 50.0% and Polyglot from 14.2% to 30.7%. In ablations, removing *either* the
  self-modification of the improver *or* the open-ended archive made results much worse.

`03_recursive_self_improvement.py` is a minimal DGM.

### 3.4 The five ingredients of every RSI system

Every system in section 5 is a version of this recipe. To design your own, choose one option for each line:

1. **A self that can be rewritten.** Something the agent can read and write: code (this repo),
   prompts, a tool library, a memory, or weights. → `seed_agent.py`
2. **An improvement operator that is part of the self.** This is what makes it *recursive*.
   → `improve()` inside `seed_agent.py`
3. **An evaluator outside the agent's control.** Ground truth such as unit tests, verifiable answers,
   or a held-out benchmark. *This is the true bottleneck of every RSI system:* the agent can only
   get as good as your ability to measure "good". → `benchmark.py`, with secret per-run seeds
4. **Selection with an archive.** Decide which variant to build on next, trading off exploitation
   (high score) against exploration (under-explored branches). → the `weights = ...` line in `03_...py`
5. **Containment.** Run the generated code somewhere it can't damage the harness, the grader, or
   the host. → `sandboxed()`, using a subprocess with a timeout. This is a minimal stand-in for a real container.

### 3.5 What stops it, or tricks it

* **Frozen weights.** Scaffold RSI changes how the model is used, not what it knows.
  Gains level off once the scaffold is good. Results in the literature are often in the
  "+10 to +30 points, then plateau" range.
* **Goodhart's law and objective hacking.** The agent optimizes the metric, not your intent.
  DGM reported an agent that "fixed" hallucinated tool use by removing the markers used to detect
  it. STOP reported the improver occasionally turning off its sandbox flag. That is why the grader
  and the selection rule live in the frozen outer loop.
* **Overfitting to the dev set.** Rewrites can memorize the tasks they were shown. RRSI (2026)
  measured large in-distribution gains that shrink out of distribution. This repo reports a
  **held-out test score** at the end for this reason.
* **Bad mutations.** Most rewrites are worse or broken. Cheap validity checks
  (`compile()`, keeping both functions) and discarding failures keep the archive healthy.
* **Cost.** Every candidate needs a full evaluation. Real systems spend days of compute,
  for example AIDE² ran for 8 days.

## 4. How this example works

```
               ┌──────────────── frozen outer loop (03_recursive_self_improvement.py) ────────────────┐
               │                                                                                       │
 seed_agent.py ─► archive {#0: 6%} ──select parent──► #k ──run #k.improve(#k's source, #k's failures)──► │
               │       ▲                                                        │                      │
               │       │                                                        ▼ new source code      │
               │       └──── add if it runs ◄── score on dev tasks ◄── sandboxed subprocess (child)    │
               │                                      ▲                                                │
               └──────────────────────────────────────┼────────────────────────────────────────────────┘
                                              benchmark.py (grader + secret seeds), llm.py (frozen model)
```

**The benchmark** (`benchmark.py`). There are six task types, all trivial for code and hard for an
LLM answering "in its head": 12-digit multiplication, counting letters in a 300-character string,
SHA-256 prefixes, sorting 20 random words, the k-th prime, and the weekday of a date in the 1700s.
The SHA-256 task is impossible without running code. The grader is exact match. So the
seed agent, which only asks the model, should score low, and there is a clear path to about 100%.
Prompting alone can't follow that path (Level 2 plateaus), but changing code can.

**The seed agent** (`seed_agent.py`, about 25 lines of logic).
* `solve(q)` asks the model and returns the reply.
* `improve(source, feedback)` puts *its own source code* and *its own failures* into a prompt and
  asks the model, at high effort, for a complete better file. It is told it may rewrite `improve()` too.

**One iteration**, as in `main()`:
1. **Select a parent.** Its weight is `(score + 0.05) / (1 + children)`, the same shape as DGM's rule.
   Good agents are likely to be picked, agents with many children are discounted, and even a 0% agent
   keeps a small chance.
2. **Self-modify.** `sandboxed(parent_file, "improve", [parent_source, parent_feedback])` runs
   the *parent's own* `improve()` in a subprocess. If a previous generation rewrote `improve()`,
   the rewritten version is the one running now. That is the recursion.
3. **Validate.** The child must compile and still define `solve` and `improve`.
4. **Evaluate.** All dev questions go to the child's `solve()` in a subprocess. Only questions
   leave the harness. The answers stay in the parent process, and the task seed is random and
   secret, so the agent can't look them up.
5. **Archive.** Any child that runs is added, whatever its score. Crashes are discarded.
   The child's failures become the feedback it will see when it is picked as a parent later.

At the end, the harness prints the **lineage** of the best agent (for example
`#0 (6%) -> #2 (39%) -> #5 (89%)`) and compares seed and best on **held-out** tasks.

**What you should expect to see.** I couldn't run this against the live API while writing it.
The harness was tested end to end with a stub model, so treat this as a prediction, not a result.
Common discoveries are:
* *Giving itself a tool.* `solve()` asks the model to write Python, then runs it with
  `subprocess` or `exec`. This is the big jump, and it mirrors how DGM agents added their own
  editing and testing tools.
* *Routing by task type, answer cleanup, retries on errors, or majority voting.*
* *Changes to `improve()`*, such as grouping failures by type, asking for a plan before the code,
  raising effort, or adding "don't break the interface" checks. These change future generations,
  not this one's score. Look for them in the diffs.
* *Regressions and dead ends.* Some children crash or score worse. The archive keeps working ones
  anyway, and selection routes around the rest.

Runs vary. Run it a few times and compare lineages.

## 5. Research map

| Work | Year | What it adds to the recipe |
|---|---|---|
| [Gödel Machine](https://arxiv.org/abs/cs/0309048) (Schmidhuber) | 2003 | Theory: self-rewrites that are accepted only with a proof of improvement |
| [STaR](https://arxiv.org/abs/2203.14465) | 2022 | Level 4: the model fine-tunes on its own correct reasoning |
| [Self-Refine](https://arxiv.org/abs/2303.17651), [Reflexion](https://arxiv.org/abs/2303.11366) | 2023 | Level 1: critique and retry; Reflexion keeps verbal memory |
| [Voyager](https://arxiv.org/abs/2305.16291) | 2023 | Level 2: a growing library of code skills |
| [OPRO](https://arxiv.org/abs/2309.03409) | 2023 | Level 2: an LLM as the optimizer of prompts (our Level 2 file) |
| [Promptbreeder](https://arxiv.org/abs/2309.16797) | 2023 | Self-referential prompts: the *mutation prompts* evolve too |
| [STOP](https://arxiv.org/abs/2310.02304) (Zelikman et al.) | 2023 | Level 3: a code "improver" applied to itself. It invented beam search and genetic algorithms, and sometimes disabled its sandbox flag |
| [Self-Rewarding LMs](https://arxiv.org/abs/2401.10020) | 2024 | Level 4: the model is its own reward model |
| [ADAS / Meta Agent Search](https://arxiv.org/abs/2408.08435) | 2024 | An archive of agents written as code; the meta-agent is fixed, so it is Level 2.5 |
| [Gödel Agent](https://arxiv.org/abs/2410.04444) | 2024 | Level 3: modifies its own running logic, including the modifier |
| [SICA](https://arxiv.org/abs/2504.15228) | 2025 | Level 3: one coding agent edits its own codebase; no separate meta-agent |
| [Darwin Gödel Machine](https://arxiv.org/abs/2505.22954) | 2025 | Level 3 + open-ended archive + empirical validation (**this repo's design**) |
| [Absolute Zero](https://arxiv.org/abs/2505.03335) | 2025 | Level 4: the model proposes its own tasks, solves them, and learns from verifiable results, with no data |
| [AlphaEvolve](https://arxiv.org/abs/2506.13131) (DeepMind) | 2025 | Evolutionary coding agent. It sped up a kernel used to train Gemini, so it improved its own training stack |
| [SEAL](https://arxiv.org/abs/2506.10943) | 2025 | Level 4: the model writes its own fine-tuning data ("self-edits"), trained with RL |
| [Huxley-Gödel Machine](https://arxiv.org/abs/2510.21614) | 2025 (ICLR '26) | Pick parents by **clade metaproductivity** (descendants' scores), not by their own score |
| [MetaRSI](https://arxiv.org/abs/2609.06396) | 2026 | RSI applied to the RSI system itself |
| [RRSI](https://arxiv.org/abs/2609.24972) | 2026 | Regularized harness evolution: edit budgets, a critic and a pruner against benchmark overfitting |
| [AIDE²](https://arxiv.org/abs/2609.26457) | 2026 | Two-loop RSI for AI-research agents. In an 8-day run it found 7 successive improvements and matched a human-built production agent |

Common threads in recent work (2025–26): the field has moved from "can it self-modify?" to
**which parent to expand** (HGM), **how not to overfit** (RRSI), **how to make it work in long,
real research tasks** (AIDE²), and **how to keep it safe and auditable**.

## 6. Safety: read before running bigger versions

You are executing code written by a model, which then writes more code. This repo keeps the
risk small by design: the tasks are toy problems, there is a timeout, and the grader lives
outside the agent. Still, a subprocess is **not** a security boundary. Generated agents can read
and write files and use the network as your user account. For anything beyond this toy:
run inside a container or VM with no credentials except the API key, apply resource limits,
review the diffs (lineage makes that easy), and never let the agent edit the grader, the
selection rule, or `llm.py`. "What the agent cannot change" is the most important design
decision in any RSI system.

## 7. Build your own: exercises, in order

1. **Watch it happen.** Run Level 2 and then Level 3. Explain *why* Level 2 can't pass the SHA-256 task.
2. **Read a lineage.** In `archive.json`, follow the best agent's parents and diff each step. Label each
   change as a *task* improvement or an *improver* improvement.
3. **Swap the domain.** Replace `benchmark.py` with coding problems graded by unit tests, as DGM and SICA do.
   Only `make_tasks` and `grade` need to change.
4. **Try greedy selection.** Change selection to "always pick the best" and compare runs. This is the DGM
   ablation, at small scale.
5. **Try HGM.** Score a parent by the mean score of its descendants, not its own score.
6. **Give the improver memory.** Pass the lineage (past diffs and their score changes) into `improve()`.
7. **Try to make it cheat.** Put the dev seed into a file the agent can read. Does it notice? What does
   the held-out score say? Then make cheating impossible again.
8. **Go one level more recursive.** Move the selection rule into the agent too. What new failure
   modes appear? Why does that make the grader the only thing you can trust?

## 8. Explain it in 60 seconds

> A recursively self-improving agent is a program that improves itself *and* the part of itself
> that does the improving. In practice, an LLM agent stored as code is shown its own source and
> its benchmark failures, and asked to write a better version of itself. Each new version is
> tested by a grader it can't modify, and the working versions go into an archive. The next parent
> is sampled from that archive, favouring good ones and still exploring. Because the rewriting
> logic is inside the code being rewritten, gains can compound: better agents write better agents.
> The model weights stay frozen, so this is scaffold-level RSI. It is limited by the base model,
> by how well you can measure "better", and by Goodhart's law. Research systems built this way
> (DGM, SICA, HGM, AIDE²) roughly doubled coding-agent benchmark scores, and recent work focuses
> on which branch to expand, overfitting, and safety.

**Common questions**

* *Is Level 2 "fake" RSI?* It is real self-improvement, but not recursive, because the optimizer never improves.
* *Isn't the outer loop also fixed?* Yes, on purpose. Some part of the system must be trusted,
  usually the evaluator. Even in theory, a Gödel Machine fixes its proof checker.
* *Why keep worse children?* Open-endedness. In DGM, branches that dipped before climbing
  produced the best final agents.
* *Is this how real labs do it?* The structure is the same: a rewritable agent, a self-applied
  improver, an external evaluator, an archive, and a sandbox. They use far bigger benchmarks,
  containers, and days of compute.
