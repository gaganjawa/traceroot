from deepeval.test_case import LLMTestCase


def create_test_case(
    input_text: str,
    actual_output: str,
    expected_output: str | None = None,
) -> LLMTestCase:
    return LLMTestCase(
        input=input_text,
        actual_output=actual_output,
        expected_output=expected_output,
    )
