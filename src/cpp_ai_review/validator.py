"""审查结果解析与校验模块。"""

import json
from pathlib import Path

from pydantic import ValidationError

from .diff_parser import ChangedFile
from .result_schema import ReviewResult


class ReviewValidationError(RuntimeError):
    """审查结果校验失败。"""


def parse_model_json(raw: str) -> ReviewResult:
    """将模型输出解析成合法的审查结果。"""

    cleaned = raw.strip()

    # 兼容模型偶尔输出 Markdown JSON 代码围栏。
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines and lines[0].startswith("```"):
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines)

    try:
        data = json.loads(cleaned)
        return ReviewResult.model_validate(data)

    except (json.JSONDecodeError, ValidationError) as exc:
        raise ReviewValidationError(
            f"模型输出不是符合约定的 JSON: {exc}"
        ) from exc


def validate_findings(
    result: ReviewResult,
    repo_root: Path,
    changed_files: dict[str, ChangedFile],
) -> ReviewResult:
    """校验发现的文件路径及行号。"""

    root = repo_root.resolve()

    valid_findings = []
    rejected = 0

    for finding in result.findings:
        relative_path = finding.file.replace("\\", "/")
        candidate = (root / relative_path).resolve()

        # 不允许访问仓库目录以外的文件。
        try:
            candidate.relative_to(root)
        except ValueError:
            rejected += 1
            continue

        # 第一版只接收本次 Diff 涉及的文件。
        if relative_path not in changed_files:
            rejected += 1
            continue

        changed = changed_files[relative_path]

        if not candidate.is_file():
            # 删除文件无法根据当前工作区校验源文件行号。
            if not changed.is_deleted:
                rejected += 1
                continue

        else:
            try:
                line_count = len(
                    candidate.read_text(
                        encoding="utf-8",
                        errors="replace",
                    ).splitlines()
                )
            except OSError:
                rejected += 1
                continue

            if finding.line > line_count:
                rejected += 1
                continue

        valid_findings.append(finding)

    result.findings = valid_findings

    if rejected:
        result.limitations.append(
            f"已过滤 {rejected} 条结果："
            "文件路径不合法、文件不属于本次变更、"
            "文件不存在或行号超出范围。"
        )

    return result