from traceroot.evaluation.deepeval_setup import create_test_case


def test_create_test_case_maps_input():
    test_case = create_test_case(
        input_text="What caused the incident?",
        actual_output="Database connection contention.",
    )

    assert test_case.input == "What caused the incident?"


def test_create_test_case_maps_actual_output():
    test_case = create_test_case(
        input_text="What caused the incident?",
        actual_output="Database connection contention.",
    )

    assert test_case.actual_output == "Database connection contention."


def test_create_test_case_maps_expected_output():
    test_case = create_test_case(
        input_text="What caused the incident?",
        actual_output="Database connection contention.",
        expected_output="Database connection pool configuration regression.",
    )

    assert (
        test_case.expected_output
        == "Database connection pool configuration regression."
    )


def test_create_test_case_allows_missing_expected_output():
    test_case = create_test_case(
        input_text="What caused the incident?",
        actual_output="Database connection contention.",
    )

    assert test_case.expected_output is None
