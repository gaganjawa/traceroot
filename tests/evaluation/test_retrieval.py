import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from traceroot.evaluation.retrieval import (
    RetrievalEvaluationCase,
    load_retrieval_evaluation_cases,
)


def test_retrieval_case_valid():
    query = """{
        "id": "RQ-001",
        "query": "What causes checkout latency?",
        "relevant_sources": ["checkout-runbook.md"]
    }"""

    case = RetrievalEvaluationCase.model_validate_json(query)

    assert case.id == "RQ-001"
    assert case.query == "What causes checkout latency?"
    assert case.relevant_sources == ["checkout-runbook.md"]


def test_retrieval_queries_load_multiple_cases(tmp_path):

    queries = [
        {
            "id": "RQ-001",
            "query": "What causes checkout latency?",
            "relevant_sources": ["doc1.md", "doc2.md"],
        },
        {
            "id": "RQ-002",
            "query": "How to fix payment failures?",
            "relevant_sources": ["doc3.md"],
        },
    ]

    file_path = tmp_path / "retrieval_queries.json"
    with open(file_path, "w") as f:
        json.dump(queries, f)

    cases = load_retrieval_evaluation_cases(file_path)

    assert len(cases) == 2
    assert cases[0].id == "RQ-001"
    assert cases[0].query == "What causes checkout latency?"
    assert cases[0].relevant_sources == ["doc1.md", "doc2.md"]
    assert cases[1].id == "RQ-002"
    assert cases[1].query == "How to fix payment failures?"
    assert cases[1].relevant_sources == ["doc3.md"]


def test_retrieval_case_missing_relevant_sources():
    query = """{
        "id": "RQ-001",
        "query": "What causes checkout latency?"
    }"""

    with pytest.raises(ValidationError):
        RetrievalEvaluationCase.model_validate_json(query)


def test_retrieval_case_rejects_empty_relevant_sources():
    query = """{
        "id": "RQ-001",
        "query": "What causes checkout latency?",
        "relevant_sources": []
    }"""

    with pytest.raises(ValidationError):
        RetrievalEvaluationCase.model_validate_json(query)


def test_actual_retrieval_evaluation_dataset():
    path = Path("data/evaluation/retrieval_queries.json")

    cases = load_retrieval_evaluation_cases(path)

    assert len(cases) == 10
    assert all(case.relevant_sources for case in cases)
