import pytest

from traceroot.evaluation.retrieval_metrics import recall_at_k


def test_full_recall():
    relevant_sources = ["source1", "source2", "source3"]
    retrieved_sources = ["source1", "source2", "source3", "source4", "source5"]
    k = 5

    recall = recall_at_k(relevant_sources, retrieved_sources, k)
    assert recall == 1.0  # All relevant sources are found in the top k


def test_partial_recall():
    relevant_sources = ["source1", "source2", "source3"]
    retrieved_sources = ["source1", "source4", "source5"]
    k = 3

    recall = recall_at_k(relevant_sources, retrieved_sources, k)
    assert recall == 1 / 3  # Only one relevant source is found in the top k


def test_zero_recall():
    relevant_sources = ["source1", "source2", "source3"]
    retrieved_sources = ["source4", "source5", "source6"]
    k = 3

    recall = recall_at_k(relevant_sources, retrieved_sources, k)
    assert recall == 0.0  # No relevant sources are found in the top k


def test_duplicate_retrieved_source():
    relevant_sources = ["source1", "source2", "source3"]
    retrieved_sources = ["source2", "source2", "source6"]
    k = 3

    recall = recall_at_k(relevant_sources, retrieved_sources, k)
    assert recall == 1 / 3  # The duplicate relevant source is counted only once


def test_k_actually_matters():
    relevant_sources = ["source1", "source2", "source3"]
    retrieved_sources = ["source1", "source2", "source3", "source4", "source5"]
    k = 2

    recall = recall_at_k(relevant_sources, retrieved_sources, k)
    assert recall == 2 / 3  # All relevant sources are found in the top k


def test_empty_relevant_sources():
    with pytest.raises(ValueError):
        recall_at_k([], ["source1", "source2"], 2)


def test_zero_k():
    with pytest.raises(ValueError):
        recall_at_k(["source1"], ["source1"], 0)


def test_negative_k():
    with pytest.raises(ValueError):
        recall_at_k(["source1"], ["source1"], -1)
