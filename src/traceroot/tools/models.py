from enum import StrEnum


class ToolName(StrEnum):
    LOGS = "logs"
    METRICS = "metrics"
    DEPLOYMENTS = "deployments"
    CODE_CHANGES = "code_changes"
