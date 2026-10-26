"""AI 审查结果的数据结构定义。"""

from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


Severity = Literal[
    "CRITICAL",
    "HIGH",
    "MEDIUM",
    "LOW",
]

ReviewStatus = Literal[
    "completed",
    "partial",
    "failed",
]


class Finding(BaseModel):
    """单条审查发现。"""

    model_config = ConfigDict(extra="forbid")

    rule_id: str = Field(
        min_length=1,
        max_length=80,
    )

    severity: Severity

    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )

    file: str = Field(min_length=1)

    line: int = Field(ge=1)

    title: str = Field(
        min_length=1,
        max_length=200,
    )

    description: str = Field(min_length=1)

    evidence: str = Field(min_length=1)

    suggestion: str = Field(min_length=1)

    introduced_by_change: bool

    @field_validator("file")
    @classmethod
    def validate_relative_path(
        cls,
        value: str,
    ) -> str:
        """禁止绝对路径和路径穿越。"""

        normalized = value.replace("\\", "/")

        if normalized.startswith("/"):
            raise ValueError(
                "file 必须是仓库相对路径"
            )

        if (
            len(normalized) >= 2
            and normalized[1] == ":"
        ):
            raise ValueError(
                "file 不允许使用 Windows 绝对路径"
            )

        if any(
            part == ".."
            for part in normalized.split("/")
        ):
            raise ValueError(
                "file 不允许包含 .. 路径段"
            )

        return normalized


class ReviewResult(BaseModel):
    """完整审查结果。"""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0"] = "1.0"

    review_status: ReviewStatus

    summary: str

    allow_merge: bool = False

    findings: list[Finding] = Field(
        default_factory=list,
    )

    limitations: list[str] = Field(
        default_factory=list,
    )


def apply_allow_merge(result: ReviewResult) -> ReviewResult:
    """审查完成且没有发现时，才允许放行。"""

    result.allow_merge = (
        result.review_status == "completed"
        and not result.findings
    )

    return result