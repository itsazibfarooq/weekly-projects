"""The frozen benchmark and grader. This is the ground truth the agent cannot touch.

Every task is trivial for a program but hard for an LLM answering "in its head".
That leaves room to improve: an agent that gives itself a Python tool can reach
~100%, and one that only rewords its prompt can't.
"""
import datetime
import hashlib
import random
import string


def nth_prime(k: int) -> int:
    sieve = bytearray([1]) * 60_000
    sieve[:2] = b"\0\0"
    for i in range(2, 245):
        if sieve[i]:
            sieve[i * i :: i] = bytearray(len(sieve[i * i :: i]))
    return [i for i, is_prime in enumerate(sieve) if is_prime][k - 1]


def make_tasks(seed: int, n: int = 18) -> list[tuple[str, str]]:
    """Return n (question, expected_answer) pairs. Same seed -> same tasks."""
    rng = random.Random(seed)
    word = lambda k: "".join(rng.choices(string.ascii_lowercase, k=k))
    tasks = []
    for i in range(n):
        kind = i % 6
        if kind == 0:
            a, b = rng.randrange(10**11, 10**12), rng.randrange(10**11, 10**12)
            tasks.append((f"What is {a} * {b}?", str(a * b)))
        elif kind == 1:
            s, c = "".join(rng.choices("abc", k=300)), rng.choice("abc")
            tasks.append((f"How many times does the letter '{c}' appear in this string? {s}", str(s.count(c))))
        elif kind == 2:
            w = word(12)
            tasks.append((f"What are the first 10 hex characters of the SHA-256 hash of the string '{w}'?",
                          hashlib.sha256(w.encode()).hexdigest()[:10]))
        elif kind == 3:
            words = [word(6) for _ in range(20)]
            tasks.append(("Sort these words alphabetically. Answer comma-separated with no spaces: " + " ".join(words),
                          ",".join(sorted(words))))
        elif kind == 4:
            k = rng.randrange(2000, 5000)
            tasks.append((f"What is the {k}th prime number?", str(nth_prime(k))))
        else:
            d = datetime.date(1700, 1, 1) + datetime.timedelta(days=rng.randrange(100_000))
            tasks.append((f"What day of the week was {d.isoformat()}?", d.strftime("%A")))
    return tasks


def grade(answer: str, expected: str) -> bool:
    return str(answer).strip().strip(".").lower() == expected.lower()
