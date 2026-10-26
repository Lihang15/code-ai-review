"""命令行入口。"""

import json
import os
from pathlib import Path

import typer
from pydantic import ValidationError

from .llm_client import (
    DeepSeekClient,
    LLMError,
)
from .review_engine import run_review
from .validator import ReviewValidationError


app = typer.Typer(
    name="ai-code-review",
    help="基于 DeepSeek 的 C/C++ AI 代码审查工具。",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """基于 DeepSeek 的 C/C++ AI 代码审查工具。"""


def write_json(
    path: Path,
    data: dict,
) -> None:
    """创建目录并写入 JSON 结果。"""

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )


@app.command()
def review(
    diff: Path = typer.Option(
        ...,
        "--diff",
        help="Git MR Diff 文件路径。",
    ),
    repo_root: Path = typer.Option(
        ...,
        "--repo-root",
        help="MR 源 Commit 对应的源码目录。",
    ),
    output: Path = typer.Option(
        Path("review-result.json"),
        "--output",
        help="审查结果 JSON 的输出路径。",
    ),
    skill_path: Path | None = typer.Option(
        None,
        "--skill-path",
        help="可选，自定义 SKILL.md 路径。",
    ),
    source_sha: str | None = typer.Option(
        None,
        "--source-sha",
        help="MR 源分支 Commit SHA。",
    ),
    target_sha: str | None = typer.Option(
        None,
        "--target-sha",
        help="MR 目标分支 Commit SHA。",
    ),
    max_context_chars: int = typer.Option(
        int(
            os.getenv(
                "AI_REVIEW_MAX_CONTEXT_CHARS",
                "80000",
            )
        ),
        "--max-context-chars",
        min=1000,
        help="发送给模型的源码上下文最大字符数。",
    ),
) -> None:
    """执行一次 AI 代码审查。"""

    try:
        if not diff.is_file():
            raise FileNotFoundError(
                f"Diff 文件不存在: {diff}"
            )

        if not repo_root.is_dir():
            raise NotADirectoryError(
                f"源码目录不存在: {repo_root}"
            )

        client = DeepSeekClient()

        result = run_review(
            diff_path=diff,
            repo_root=repo_root,
            skill_path=skill_path,
            source_sha=source_sha,
            target_sha=target_sha,
            max_context_chars=max_context_chars,
            client=client,
        )

        write_json(
            output,
            result.model_dump(),
        )

        typer.echo(
            f"审查完成，结果文件：{output.resolve()}"
        )

        typer.echo(
            f"审查状态：{result.review_status}"
        )

        typer.echo(
            f"发现数量：{len(result.findings)}"
        )

        typer.echo(
            "是否放行："
            + ("是" if result.allow_merge else "否")
        )

        # partial 不能被 CI 当作完整审查通过。
        if result.review_status != "completed":
            raise typer.Exit(code=2)

    except (
        OSError,
        ValueError,
        LLMError,
        ReviewValidationError,
        ValidationError,
    ) as exc:

        typer.echo(
            f"AI 审查执行失败：{exc}",
            err=True,
        )

        # 尽可能生成失败结果，避免 CI 将执行失败误判为无缺陷。
        try:
            write_json(
                output,
                {
                    "schema_version": "1.0",
                    "review_status": "failed",
                    "allow_merge": False,
                    "summary": str(exc),
                    "findings": [],
                    "limitations": [
                        "AI 审查未能产生有效的完整结果。"
                    ],
                },
            )

            typer.echo(
                f"失败结果已写入：{output.resolve()}",
                err=True,
            )

        except OSError as write_exc:
            typer.echo(
                f"无法写入失败结果：{write_exc}",
                err=True,
            )

        raise typer.Exit(code=2) from exc


if __name__ == "__main__":
    app()