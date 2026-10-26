"""源码上下文收集模块。"""

import re
from pathlib import Path

from .diff_parser import ChangedFile


CPP_EXTENSIONS = {
    ".c", ".cc", ".cpp", ".cxx",
    ".h", ".hh", ".hpp", ".hxx",
    ".ipp", ".inl", ".mm", ".m",
}

INCLUDE_RE = re.compile(
    r'^\s*#\s*include\s*"([^"]+)"',
    re.MULTILINE,
)

DEFAULT_MAX_CONTEXT_CHARS = 80_000
MAX_FILE_CHARS = 18_000
MAX_NEARBY_LINES = 100


def read_text(path: Path) -> str:
    """读取文本文件，兼容非 UTF-8 内容。"""

    try:
        return path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return ""


def _line_window(
    text: str,
    center_lines: set[int],
    radius: int = MAX_NEARBY_LINES,
) -> str:
    """提取目标行附近的代码，并保留原始行号。"""

    lines = text.splitlines()

    if not lines:
        return ""

    selected: set[int] = set()

    for line_no in center_lines:
        start = max(1, line_no - radius)
        end = min(len(lines), line_no + radius)
        selected.update(range(start, end + 1))

    if not selected:
        selected.update(
            range(1, min(len(lines), 80) + 1)
        )

    output: list[str] = []
    last_line = 0

    for line_no in sorted(selected):
        if line_no > last_line + 1:
            output.append("...")

        output.append(
            f"{line_no:>5}: {lines[line_no - 1]}"
        )

        last_line = line_no

    return "\n".join(output)


def collect_context(
    repo_root: Path,
    changed_files: dict[str, ChangedFile],
    max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
) -> str:
    """收集修改文件、附近代码和可访问的本地头文件。"""

    root = repo_root.resolve()
    chunks: list[str] = []
    included_paths: set[str] = set()

    def add_file(
        relative_path: str,
        focus_lines: set[int] | None,
        label: str,
    ) -> None:
        if relative_path in included_paths:
            return

        candidate = (root / relative_path).resolve()

        # 禁止通过符号链接或路径构造读取仓库之外的文件。
        try:
            candidate.relative_to(root)
        except ValueError:
            return

        if not candidate.is_file():
            return

        if candidate.suffix.lower() not in CPP_EXTENSIONS:
            return

        content = read_text(candidate)

        if not content:
            return

        included_paths.add(relative_path)

        if focus_lines:
            rendered = _line_window(
                content,
                focus_lines,
            )
        else:
            rendered = "\n".join(
                f"{n:>5}: {line}"
                for n, line in enumerate(
                    content.splitlines()[:250],
                    start=1,
                )
            )

        if len(rendered) > MAX_FILE_CHARS:
            rendered = (
                rendered[:MAX_FILE_CHARS]
                + "\n...[文件内容已截断]"
            )

        chunks.append(
            f"### {label}: {relative_path}\n{rendered}"
        )

    for relative_path, changed in changed_files.items():

        if changed.is_deleted:
            chunks.append(
                f"### 删除文件: {relative_path}\n"
                "[该文件已在本次 Diff 中删除]"
            )
            continue

        add_file(
            relative_path,
            changed.changed_lines or changed.added_lines,
            "修改文件",
        )

        if relative_path not in included_paths:
            continue

        source_path = (root / relative_path).resolve()
        content = read_text(source_path)

        parent = str(Path(relative_path).parent)

        for include in INCLUDE_RE.findall(content):
            include_path = (
                Path(parent) / include
            ).as_posix()

            include_candidate = (
                root / include_path
            ).resolve()

            try:
                include_candidate.relative_to(root)
            except ValueError:
                continue

            if include_candidate.is_file():
                add_file(
                    include_path,
                    None,
                    "相关头文件",
                )

    result = "\n\n".join(chunks)

    if len(result) > max_context_chars:
        result = (
            result[:max_context_chars]
            + "\n\n...[上下文总长度已截断]"
        )

    return result