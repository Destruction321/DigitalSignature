# package/_utils/worker.py
"""后台任务 Worker 基类"""
from abc import ABC, abstractmethod
from threading import Event, Thread
from typing import Callable

from .result import Result, Status

type ProgressCallback = Callable[[float, str], None]

class Worker(ABC):
    """在后台线程执行耗时操作，通过回调报告进度和结果"""
    def __init__(self) -> None:
        self.__cancel_event = Event()
        self.__on_progress: ProgressCallback | None = None

    
    """Interfaces for subclasses to implement"""
    @abstractmethod
    def do_work(self) -> Result:
        ...

    
    """getters and setters"""
    @property
    def is_cancelled(self) -> bool:
        return self.__cancel_event.is_set()
    
    @property
    def on_progress(self) -> ProgressCallback | None:
        return self.__on_progress

    @on_progress.setter
    def on_progress(self, callback: ProgressCallback) -> None:
        self.__on_progress = callback

    
    """protected methods -- used by subclasses"""
    def _report_progress(self, fraction: float, message: str = "") -> None:
        if self.__on_progress:
            self.__on_progress(max(0.0, min(1.0, fraction)), message)
    
    
    """public methods"""
    def start(self, on_finished: Callable[[Result], None]) -> None:
        """启动后台任务"""
        self.__on_finished = on_finished
        Thread(target=self.__run, daemon=True).start()
        
    def cancel(self) -> None:
        """取消操作"""
        self.__cancel_event.set()

    
    """private methods"""
    def __run(self) -> None:
        try:
            result = self.do_work()
        except Exception as e:
            result = Result(status=Status.SYSTEM_ERROR, msg=str(e))
        self.__on_finished(result)
