#!/usr/bin/env python3
"""
AI Reasoning Evaluation Script — AI Morphasis 2.0
==================================================
Runs a series of deterministic, self-contained checks that model
AI learning, research, reasoning, and thinking.

Checks
------
1. Logic / Reasoning consistency  — syllogism & chain-of-thought validation
2. Learning / Adaptation          — in-memory example-set incremental learning
3. Research / Summarization       — keyword coverage over a short text fixture
4. Self-check / Reflection        — uncertainty detection and evidence gaps

Exit codes
----------
0  All checks passed.
1  One or more checks failed.
"""

from __future__ import annotations

import sys
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# 1. Logic / Reasoning Consistency
# ---------------------------------------------------------------------------

def evaluate_syllogism(premises: List[str], conclusion: str) -> bool:
    """Return True if the conclusion's key terms appear in the premises."""
    combined = " ".join(premises).lower()
    conclusion_words = set(conclusion.lower().split())
    # A valid syllogism must ground every content word in at least one premise.
    stop_words = {"is", "are", "a", "an", "the", "if", "then", "therefore", "all", "no"}
    content_words = conclusion_words - stop_words
    return all(word in combined for word in content_words)


def check_reasoning_consistency(
    cases: List[Tuple[List[str], str, bool]]
) -> Tuple[int, int, List[str]]:
    """
    Evaluate a list of (premises, conclusion, expected_valid) cases.

    Returns (passed, total, failures).
    """
    passed, failures = 0, []
    for premises, conclusion, expected in cases:
        result = evaluate_syllogism(premises, conclusion)
        if result == expected:
            passed += 1
        else:
            failures.append(
                f"  FAIL syllogism: premises={premises!r}, "
                f"conclusion={conclusion!r}, "
                f"expected={expected}, got={result}"
            )
    return passed, len(cases), failures


# ---------------------------------------------------------------------------
# 2. Learning / Adaptation
# ---------------------------------------------------------------------------

def incremental_learn(
    examples: List[Tuple[str, str]],
    query: str,
) -> Optional[str]:
    """
    Simulate lightweight k-NN style retrieval from an in-memory example set.

    Given labelled (input, label) examples, return the label of the example
    whose input shares the most tokens with *query*.  Returns None when the
    example set is empty.
    """
    if not examples:
        return None
    query_tokens = set(query.lower().split())
    best_label, best_score = None, -1
    for text, label in examples:
        text_tokens = set(text.lower().split())
        overlap = len(query_tokens & text_tokens)
        if overlap > best_score:
            best_score, best_label = overlap, label
    return best_label


def check_learning(
    cases: List[Tuple[List[Tuple[str, str]], str, str]]
) -> Tuple[int, int, List[str]]:
    """
    Evaluate a list of (examples, query, expected_label) cases.

    Returns (passed, total, failures).
    """
    passed, failures = 0, []
    for examples, query, expected in cases:
        result = incremental_learn(examples, query)
        if result == expected:
            passed += 1
        else:
            failures.append(
                f"  FAIL learning: query={query!r}, "
                f"expected={expected!r}, got={result!r}"
            )
    return passed, len(cases), failures


# ---------------------------------------------------------------------------
# 3. Research / Summarization Quality
# ---------------------------------------------------------------------------

def summarize_keywords(text: str, top_n: int = 5) -> List[str]:
    """
    Return the *top_n* most frequent non-stop-words from *text* (lower-cased).
    Ties are broken alphabetically so the result is deterministic.
    """
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "is", "are", "was", "were", "be", "been",
        "have", "has", "had", "do", "does", "did", "will", "would",
        "can", "could", "may", "might", "shall", "should", "it", "its",
        "this", "that", "these", "those", "as", "by", "from", "into",
        "through", "during", "before", "after", "above", "below", "between",
        "each", "more", "also", "not", "no", "so", "if", "then", "than",
        "our", "we", "they", "their", "he", "she", "his", "her", "i",
        "you", "your", "my", "me", "us", "which", "who", "what",
    }
    words: Dict[str, int] = {}
    for raw in text.lower().split():
        word = raw.strip(".,;:!?\"'()-")
        if word and word not in stop_words:
            words[word] = words.get(word, 0) + 1
    sorted_words = sorted(words.items(), key=lambda kv: (-kv[1], kv[0]))
    return [w for w, _ in sorted_words[:top_n]]


def check_summarization(
    cases: List[Tuple[str, List[str]]]
) -> Tuple[int, int, List[str]]:
    """
    For each (text, required_keywords) case verify that all required keywords
    appear in the summarize_keywords() output.

    Returns (passed, total, failures).
    """
    passed, failures = 0, []
    for text, required in cases:
        keywords = summarize_keywords(text, top_n=max(len(required), 5))
        missing = [kw for kw in required if kw not in keywords]
        if not missing:
            passed += 1
        else:
            failures.append(
                f"  FAIL summarization: missing keywords {missing!r} "
                f"from extracted {keywords!r}"
            )
    return passed, len(cases), failures


# ---------------------------------------------------------------------------
# 4. Self-check / Reflection
# ---------------------------------------------------------------------------

_UNCERTAINTY_MARKERS = frozenset(
    [
        "unknown", "unclear", "uncertain", "missing", "insufficient",
        "cannot", "unsure", "ambiguous", "no evidence", "not enough",
        "undetermined", "inconclusive", "possibly", "maybe", "might",
    ]
)


def detect_uncertainty(statement: str) -> bool:
    """Return True if *statement* contains at least one uncertainty marker."""
    lower = statement.lower()
    return any(marker in lower for marker in _UNCERTAINTY_MARKERS)


def check_reflection(
    cases: List[Tuple[str, bool]]
) -> Tuple[int, int, List[str]]:
    """
    For each (statement, should_flag_uncertainty) case verify detect_uncertainty().

    Returns (passed, total, failures).
    """
    passed, failures = 0, []
    for statement, expected in cases:
        result = detect_uncertainty(statement)
        if result == expected:
            passed += 1
        else:
            failures.append(
                f"  FAIL reflection: statement={statement!r}, "
                f"expected_uncertain={expected}, got={result}"
            )
    return passed, len(cases), failures


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

SYLLOGISM_CASES: List[Tuple[List[str], str, bool]] = [
    (
        ["All humans are mortal", "Socrates is a human"],
        "Socrates is mortal",
        True,
    ),
    (
        ["All birds can fly", "Penguins are birds"],
        "Penguins can fly",
        True,  # syntactically grounded — factual accuracy is not the scope here
    ),
    (
        ["The sky is blue"],
        "Gravity is strong",
        False,  # conclusion terms not grounded in premises
    ),
    (
        ["If it rains then the ground is wet", "It is raining"],
        "The ground is wet",
        True,
    ),
]

LEARNING_CASES: List[Tuple[List[Tuple[str, str]], str, str]] = [
    (
        [
            ("neural networks learn from data", "ml"),
            ("photosynthesis converts sunlight to energy", "biology"),
            ("the stock market reflects economic trends", "finance"),
        ],
        "deep learning trains on large datasets",
        "ml",
    ),
    (
        [
            ("chlorophyll absorbs sunlight in leaves", "biology"),
            ("gradient descent optimises loss functions", "ml"),
            ("bond yields inversely affect prices", "finance"),
        ],
        "plants use chlorophyll for energy production",
        "biology",
    ),
    (
        [
            ("inflation reduces purchasing power", "finance"),
            ("backpropagation computes gradients", "ml"),
            ("mitosis divides cells into two", "biology"),
        ],
        "interest rates affect inflation and borrowing costs",
        "finance",
    ),
]

_RESEARCH_TEXT = (
    "Artificial intelligence research focuses on creating systems that can learn, "
    "reason, and adapt. Machine learning, a subfield of AI, uses data-driven "
    "algorithms to train models. Deep learning leverages neural networks with "
    "many layers to learn complex representations. Reinforcement learning trains "
    "agents to maximise rewards through interaction. Research in AI also covers "
    "natural language processing, computer vision, and reasoning systems. "
    "Recent advances include large language models trained on vast corpora of text. "
    "AI safety research ensures that intelligent systems remain aligned with "
    "human values and goals. Reasoning and planning are fundamental capabilities "
    "for intelligent agents operating in complex environments."
)

SUMMARIZATION_CASES: List[Tuple[str, List[str]]] = [
    (_RESEARCH_TEXT, ["learning", "ai", "research"]),
    (_RESEARCH_TEXT, ["systems", "agents"]),
]

REFLECTION_CASES: List[Tuple[str, bool]] = [
    ("The patient's diagnosis is unclear due to missing test results.", True),
    ("Water boils at 100 degrees Celsius at sea level.", False),
    ("It is uncertain whether the experiment succeeded.", True),
    ("The Earth orbits the Sun once every 365.25 days.", False),
    ("There is no evidence to support this hypothesis.", True),
    ("Gravity pulls objects towards the centre of the Earth.", False),
]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_checks() -> bool:
    """Execute all checks, print a report, return True if everything passed."""
    results = []
    all_passed = True

    sections = [
        (
            "1. Reasoning / Logic Consistency",
            check_reasoning_consistency(SYLLOGISM_CASES),
        ),
        (
            "2. Learning / Adaptation",
            check_learning(LEARNING_CASES),
        ),
        (
            "3. Research / Summarization Quality",
            check_summarization(SUMMARIZATION_CASES),
        ),
        (
            "4. Self-check / Reflection (Uncertainty Detection)",
            check_reflection(REFLECTION_CASES),
        ),
    ]

    print("\n" + "=" * 64)
    print("  AI MORPHASIS 2.0 — AI REASONING EVALUATION")
    print("=" * 64)

    for title, (passed, total, failures) in sections:
        status = "PASS" if not failures else "FAIL"
        print(f"\n[{status}] {title}")
        print(f"       {passed}/{total} cases passed")
        for msg in failures:
            print(msg)
        if failures:
            all_passed = False

    print("\n" + "=" * 64)
    if all_passed:
        print("  RESULT: ALL CHECKS PASSED ✔")
    else:
        print("  RESULT: ONE OR MORE CHECKS FAILED ✘")
    print("=" * 64 + "\n")

    return all_passed


def main() -> None:
    ok = run_all_checks()
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
