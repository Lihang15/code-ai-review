"""命令行进度输出。"""

import math
import sys
import threading
import time

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)


console = Console(highlight=False)


def log(message: str) -> None:
    """立即打印一行状态，避免用户长时间看不到输出。"""

    console.print(message, highlight=False)
    sys.stdout.flush()


def run_with_progress(title: str, action):
    """打印标题并在下方显示进度，直到 action 结束。"""

    log(title)

    done = threading.Event()
    box: dict = {}

    def worker() -> None:
        try:
            box["result"] = action()
        except Exception as exc:
            box["error"] = exc
        finally:
            done.set()

    thread = threading.Thread(
        target=worker,
        daemon=True,
    )
    thread.start()

    try:
        if console.is_terminal:
            _animate(done, box)
        else:
            while not done.wait(5):
                log("AI分析进行中...")
    except KeyboardInterrupt:
        log("审查已取消")
        raise
    finally:
        if done.is_set():
            thread.join()

    if "error" in box:
        raise box["error"]

    return box["result"]


def _animate(
    done: threading.Event,
    box: dict,
) -> None:
    """在终端里用一条逐渐前进的进度条表示等待。"""

    with Progress(
        SpinnerColumn(),
        TextColumn("{task.description}"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
        refresh_per_second=8,
    ) as progress:
        task = progress.add_task(
            "分析中",
            total=100,
        )
        started = time.monotonic()

        while not done.is_set():
            elapsed = time.monotonic() - started
            percent = 95 * (
                1 - math.exp(-elapsed / 25)
            )
            progress.update(
                task,
                completed=percent,
            )
            done.wait(0.25)

        if "error" in box:
            progress.update(
                task,
                description="分析失败",
            )
            return

        progress.update(
            task,
            completed=100,
            description="分析完成",
        )
