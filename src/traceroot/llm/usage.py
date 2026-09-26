from pydantic import BaseModel, Field


class LLMUsage(BaseModel):
    input_tokens: int | None = Field(default=0, ge=0)
    output_tokens: int | None = Field(default=0, ge=0)
    llm_calls: int = Field(default=0, ge=0)

    @property
    def total_tokens(self) -> int | None:
        if self.input_tokens is None or self.output_tokens is None:
            return None

        return self.input_tokens + self.output_tokens

    def add(
        self,
        input_tokens: int | None,
        output_tokens: int | None,
    ) -> None:
        self.llm_calls += 1

        if input_tokens is None:
            self.input_tokens = None
        elif self.input_tokens is not None:
            self.input_tokens += input_tokens

        if output_tokens is None:
            self.output_tokens = None
        elif self.output_tokens is not None:
            self.output_tokens += output_tokens


def record_response_usage(
    llm_usage: LLMUsage | None,
    response,
) -> None:
    if llm_usage is None:
        return

    response_usage = response.usage

    llm_usage.add(
        input_tokens=(
            response_usage.input_tokens if response_usage is not None else None
        ),
        output_tokens=(
            response_usage.output_tokens if response_usage is not None else None
        ),
    )
