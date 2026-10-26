"""Git Diff 解析模块。"""

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath


HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
)


@dataclass
class ChangedFile:
    """记录单个修改文件的信息。"""

    path: str
    added_lines: set[int] = field(default_factory=set)
    changed_lines: set[int] = field(default_factory=set)
    diff_text: list[str] = field(default_factory=list)
    is_deleted: bool = False
    is_renamed: bool = False


def _safe_diff_path(raw: str) -> str | None:
    """清理 Diff 路径，拒绝绝对路径和路径穿越。"""

    raw = raw.strip()

    if raw == "/dev/null":
        return None

    if raw.startswith(("a/", "b/")):
        raw = raw[2:]

    path = PurePosixPath(raw)

    if path.is_absolute() or ".." in path.parts:
        return None

    return path.as_posix()


def parse_unified_diff(
    diff_text: str,
) -> dict[str, ChangedFile]:
    """解析统一格式的 Git Diff。"""

    files: dict[str, ChangedFile] = {}
    current: ChangedFile | None = None

    old_line = 0
    new_line = 0
    in_hunk = False

    for line in diff_text.splitlines():

        if line.startswith("diff --git "):
            current = None
            in_hunk = False
            continue

        if line.startswith("+++ "):
            path = _safe_diff_path(line[4:])

            if path is not None:
                current = files.setdefault(
                    path,
                    ChangedFile(path=path),
                )
            else:
                current = None

            in_hunk = False
            continue

        if current is not None:
            if line.startswith("deleted file mode "):
                current.is_deleted = True

            if line.startswith("rename from "):
                current.is_renamed = True

        if current is not None and line.startswith("@@ "):
            match = HUNK_RE.match(line)

            if match:
                old_line = int(match.group(1))
                new_line = int(match.group(3))
                in_hunk = True
                current.diff_text.append(line)

            continue

        if current is None or not in_hunk:
            continue

        current.diff_text.append(line)

        if line.startswith("\\ No newline"):
            continue

        if line.startswith("+") and not line.startswith("+++"):
            current.added_lines.add(new_line)
            current.changed_lines.add(new_line)
            new_line += 1

        elif line.startswith("-") and not line.startswith("---"):
            # 删除行没有目标文件行号。
            # 记录删除位置附近的目标行，供后续定位使用。
            current.changed_lines.add(max(1, new_line))
            old_line += 1

        elif line.startswith(" "):
            old_line += 1
            new_line += 1

        elif line.startswith("\\"):
            continue

        else:
            in_hunk = False

    return files