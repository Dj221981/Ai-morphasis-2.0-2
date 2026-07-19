"""
Unit tests for the pure functions in .github/scripts/run_ai_reasoning.py.
"""

import sys
import os

# Make the script importable without installing it as a package.
sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", ".github", "scripts"),
)

import run_ai_reasoning as rai


# ---------------------------------------------------------------------------
# 1. evaluate_syllogism
# ---------------------------------------------------------------------------


def test_valid_syllogism_socrates():
    premises = ["All humans are mortal", "Socrates is a human"]
    assert rai.evaluate_syllogism(premises, "Socrates is mortal") is True


def test_invalid_syllogism_unrelated_conclusion():
    premises = ["The sky is blue"]
    assert rai.evaluate_syllogism(premises, "Gravity is strong") is False


def test_valid_syllogism_rain():
    premises = ["If it rains then the ground is wet", "It is raining"]
    assert rai.evaluate_syllogism(premises, "The ground is wet") is True


# ---------------------------------------------------------------------------
# 2. incremental_learn
# ---------------------------------------------------------------------------


def test_learn_empty_examples():
    assert rai.incremental_learn([], "anything") is None


def test_learn_returns_best_match():
    examples = [
        ("neural networks learn from data", "ml"),
        ("photosynthesis converts sunlight to energy", "biology"),
    ]
    label = rai.incremental_learn(examples, "deep learning trains on large datasets")
    assert label == "ml"


def test_learn_biology_match():
    examples = [
        ("chlorophyll absorbs sunlight in leaves", "biology"),
        ("gradient descent optimises loss functions", "ml"),
    ]
    label = rai.incremental_learn(examples, "plants use chlorophyll for energy")
    assert label == "biology"


# ---------------------------------------------------------------------------
# 3. summarize_keywords
# ---------------------------------------------------------------------------


def test_summarize_keywords_top_n():
    text = "apple apple apple banana banana cherry"
    keywords = rai.summarize_keywords(text, top_n=2)
    assert keywords == ["apple", "banana"]


def test_summarize_keywords_stop_words_excluded():
    text = "the quick brown fox jumps over the lazy dog"
    keywords = rai.summarize_keywords(text, top_n=5)
    assert "the" not in keywords


def test_summarize_keywords_deterministic():
    text = "cat dog cat dog fish"
    first = rai.summarize_keywords(text, top_n=3)
    second = rai.summarize_keywords(text, top_n=3)
    assert first == second


# ---------------------------------------------------------------------------
# 4. detect_uncertainty
# ---------------------------------------------------------------------------


def test_detect_uncertainty_positive():
    assert rai.detect_uncertainty("The diagnosis is unclear.") is True


def test_detect_uncertainty_negative():
    assert rai.detect_uncertainty("Water boils at 100 degrees Celsius.") is False


def test_detect_uncertainty_no_evidence():
    assert rai.detect_uncertainty("There is no evidence to support this.") is True


def test_detect_uncertainty_case_insensitive():
    assert rai.detect_uncertainty("The outcome is UNKNOWN at this stage.") is True


# ---------------------------------------------------------------------------
# 5. Integration: run_all_checks passes cleanly
# ---------------------------------------------------------------------------


def test_run_all_checks_passes():
    assert rai.run_all_checks() is True
