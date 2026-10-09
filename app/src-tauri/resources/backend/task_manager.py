"""任务管理器 — 内存任务注册表 + 后台执行线程。

每个任务：id、参数、状态（queued/running/done/failed/cancelled）、
进度（0-100）、阶段消息、结果路径。进度通过线程安全队列广播给 SSE。
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import uuid

log = logging.getLogger("task_manager")

STAGES = ["queued", "running", "done", "failed", "cancelled"]


class Task:
    def __init__(self, task_id: str, params: dict) -> None:
        self.id = task_id
        self.params = params
        self.status = "queued"
        self.progress = 0
        self.message = "排队中"
        self.result = None
        self.error = None
        self.created_at = time.time()
        self._events: queue.Queue = queue.Queue()

    def set(self, status: str, progress: int | None = None, message: str | None = None) -> None:
        self.status = status
        if progress is not None:
            self.progress = progress
        if message is not None:
            self.message = message
        self._events.put(
            {
                "type": "progress",
                "task_id": self.id,
                "status": self.status,
                "progress": self.progress,
                "message": self.message,
            }
        )

    def to_dict(self) -> dict:
        video = self.params.get("video_path", "")
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "video_name": video.split("/")[-1] if video else "",
            "kind": self.params.get("kind", "pipeline"),
        }


class TaskManager:
    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()

    def create(self, params: dict) -> Task:
        task = Task(uuid.uuid4().hex[:12], params)
        with self._lock:
            self._tasks[task.id] = task
        return task

    def get(self, task_id: str) -> Task | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self) -> list[Task]:
        """全部任务，按创建时间倒序。"""
        with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)

    def run(self, task: Task, runner: callable) -> None:
        def _run() -> None:
            try:
                task.set("running", progress=1, message="开始处理")
                result = runner(task)
                task.set("done", progress=100, message="完成")
                task.result = str(result) if result else None
            except BaseException as exc:
                log.exception("任务 %s 失败", task.id)
                task.set("failed", message=f"失败: {exc}")
                task.error = str(exc)
            finally:
                task._events.put(
                    {"type": "end", "task_id": task.id, "status": task.status}
                )

        threading.Thread(target=_run, daemon=True).start()


manager = TaskManager()
