from unittest.mock import MagicMock

from traceroot.evaluation.evidence import evaluate_evidence_precision_recall


def test_evidence_precision_recall_perfect_match():
    result = MagicMock(evidence_ids=["E1", "E2"])
    ground_truth = MagicMock(supporting_evidence_ids=["E1", "E2"])

    precision, recall = evaluate_evidence_precision_recall(result, ground_truth)

    assert precision.score == 1.0
    assert recall.score == 1.0


def test_evidence_precision_with_extra_evidence():
    result = MagicMock(evidence_ids=["E1", "E2", "E3"])
    ground_truth = MagicMock(supporting_evidence_ids=["E1", "E2"])

    precision, recall = evaluate_evidence_precision_recall(result, ground_truth)

    assert precision.score == 2 / 3
    assert recall.score == 1.0


def test_evidence_recall_with_missing_evidence():
    result = MagicMock(evidence_ids=["E1"])
    ground_truth = MagicMock(supporting_evidence_ids=["E1", "E2"])

    precision, recall = evaluate_evidence_precision_recall(result, ground_truth)

    assert precision.score == 1.0
    assert recall.score == 0.5


def test_evidence_precision_recall_no_overlap():
    result = MagicMock(evidence_ids=["E1"])
    ground_truth = MagicMock(supporting_evidence_ids=["E2"])

    precision, recall = evaluate_evidence_precision_recall(result, ground_truth)

    assert precision.score == 0.0
    assert recall.score == 0.0


def test_evidence_precision_handles_empty_prediction():
    result = MagicMock(evidence_ids=[])
    ground_truth = MagicMock(supporting_evidence_ids=["E1"])

    precision, recall = evaluate_evidence_precision_recall(result, ground_truth)

    assert precision.score == 0.0
    assert recall.score == 0.0


def test_evidence_metrics_ignore_duplicate_ids():
    result = MagicMock(evidence_ids=["E1", "E1", "E2"])
    ground_truth = MagicMock(supporting_evidence_ids=["E1", "E2", "E2"])

    precision, recall = evaluate_evidence_precision_recall(result, ground_truth)

    assert precision.score == 1.0
    assert recall.score == 1.0
