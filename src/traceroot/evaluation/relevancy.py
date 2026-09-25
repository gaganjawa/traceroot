from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

from traceroot.evaluation.schemas import EvaluatorType, MetricResult
from traceroot.llm.client import LLM_MODEL_GPT_5_4_MINI


def evaluate_relevancy(
    input_text: str,
    actual_output: str,
) -> MetricResult:

    llm_test_case = LLMTestCase(
        input=input_text,
        actual_output=actual_output,
    )

    metric = AnswerRelevancyMetric(
        threshold=0.7,
        model=LLM_MODEL_GPT_5_4_MINI,
        include_reason=True,
    )

    metric.measure(llm_test_case)

    return MetricResult(
        name="Relevancy",
        score=metric.score,
        passed=metric.is_successful(),
        evaluator_type=EvaluatorType.DEEPEVAL,
        reason=metric.reason,
    )
