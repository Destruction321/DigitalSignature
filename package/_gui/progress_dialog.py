# package/_gui/progress_dialog.py
"""进度对话框基类"""
import tkinter as tk
from tkinter import ttk

from .._utils.result import Result, Status
from .._utils.worker import Worker


class ProgressDialog:
    """绑定 Worker，在后台任务执行期间显示进度条和取消按钮"""
    def __init__(self,
                 parent: tk.Misc,
                 title: str = "请稍候",
                 message: str = "正在处理...",
                 indeterminate: bool = False) -> None:
        self.__parent = parent
        self.__worker: Worker | None = None
        self.__result: Result | None = None

        self.__dialog = tk.Toplevel(parent.winfo_toplevel())
        self.__dialog.title(title)
        self.__dialog.transient(parent.winfo_toplevel())
        self.__dialog.grab_set()
        self.__dialog.resizable(False, False)
        self.__dialog.protocol("WM_DELETE_WINDOW", self.__on_cancel)

        main = ttk.Frame(self.__dialog, padding="20")
        main.pack(fill=tk.BOTH, expand=True)

        self.__label = ttk.Label(
            main, text=message, font=("微软雅黑", 10), anchor=tk.CENTER, width=42, wraplength=350
        )
        self.__label.pack(pady=(0, 15))

        mode = "indeterminate" if indeterminate else "determinate"
        self.__progress = ttk.Progressbar(main, length=350, mode=mode)
        self.__progress.pack(fill=tk.X, pady=(0, 15))
        if indeterminate:
            self.__progress.start(15)

        self.__cancel_btn = ttk.Button(main, text="取消", command=self.__on_cancel)
        self.__cancel_btn.pack()

        self.__center_on_parent()

    
    """public methods"""
    def run(self, worker: Worker) -> Result:
        """
        启动 Worker 并阻塞直到完成
        
        Args:
            worker (Worker): 要运行的后台任务
            
        Returns:
            result (Result): Worker 完成后的返回结果
        """
        self.__worker = worker
        worker.on_progress = self.__on_progress
        worker.start(on_finished=self.__on_finished)
        self.__dialog.wait_window()
        return self.__result or Result(status=Status.CANCEL_INPUT, msg="操作已取消")
    
    
    """private methods"""
    def __center_on_parent(self) -> None:
        """居中显示对话框"""
        self.__dialog.update_idletasks()
        pw = self.__parent.winfo_toplevel()
        w = self.__dialog.winfo_width()
        h = self.__dialog.winfo_height()
        x = pw.winfo_rootx() + (pw.winfo_width() - w) // 2
        y = pw.winfo_rooty() + (pw.winfo_height() - h) // 2
        self.__dialog.geometry(f"+{x}+{y}")

    def __on_progress(self, fraction: float, message: str) -> None:
        """进度条运行中回调，更新进度和消息"""
        self.__dialog.after(0, lambda: self.__progress.configure(value=fraction * 100))
        if message:
            self.__dialog.after(0, lambda: self.__label.configure(text=message))

    def __on_finished(self, result: Result) -> None:
        """工作完成回调"""
        self.__result = result
        self.__dialog.after(0, self.__dialog.destroy)

    def __on_cancel(self) -> None:
        """取消操作回调"""
        if self.__worker:
            self.__worker.cancel()
        
        self.__result = Result(status=Status.CANCEL_INPUT, msg="操作已取消")
        self.__dialog.destroy()
