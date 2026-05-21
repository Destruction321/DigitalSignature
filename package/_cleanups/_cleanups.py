# package/_cleanups/_cleanups.py
"""数字签名窗口清理模块"""
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable, TYPE_CHECKING

from . import _cleanup_ops
from .._utils.enums import DirType, Level
from .._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from .._utils.ui_state_manager import UIStateManager


class CleanUps:
    """数字签名窗口清理模块"""
    def __init__(self, root: tk.Tk, refresh_key_list: Callable[[], None]) -> None:
        self.__cleanup_days_threshold: int = 30
        self.__root: tk.Tk = root
        self.__ui_state_mgr: UIStateManager = get_ui_state_manager()
        self.__refresh_key_list: Callable[[], None] = refresh_key_list

    
    """public methods -- bind to buttons"""
    def cleanup_all_files(self) -> None:
        """执行完整清理所有文件"""
        # 弹出对话框让用户选择阈值天数
        selected_days = self.__show_days_selection_dialog()

        # 如果用户选择了天数（点击了确定），则执行完整清理
        if selected_days is not None:
            self.__cleanup_days_threshold = selected_days
            cleanup_result = _cleanup_ops.cleanup_all_files(selected_days)
            self.__refresh_key_list()
            self.__handle_cleanup_result(cleanup_result)

    def cleanup_temp_files(self) -> None:
        """清理临时文件"""
        cleanup_result = _cleanup_ops.cleanup_temp_files()
        self.__handle_cleanup_result(cleanup_result)

    def cleanup_orphaned_keys(self) -> None:
        """清理孤立的密钥文件"""
        cleanup_result = _cleanup_ops.cleanup_orphaned_keys()
        self.__refresh_key_list()
        self.__handle_cleanup_result(cleanup_result)

    def cleanup_old_files(self) -> None:
        """清理旧文件，不包括密钥文件"""
        # 弹出对话框让用户选择阈值天数
        selected_days = self.__show_days_selection_dialog()

        # 如果用户选择了天数（点击了确定），则执行清理
        if selected_days is not None:
            self.__cleanup_days_threshold = selected_days
            cleanup_result = _cleanup_ops.cleanup_old_files(
                self.__cleanup_days_threshold,
                [DirType.TEXTS, DirType.SIGNATURES, DirType.TEMP]
            )
            self.__handle_cleanup_result(cleanup_result)


    """private methods"""
    def __handle_cleanup_result(self, cleanup_result) -> None:
        """处理清理结果"""
        message = cleanup_result.msg
        level = Level.INFO if cleanup_result.is_success else Level.WARNING
        log = False if cleanup_result.is_success else True
        
        self.__ui_state_mgr.update_status(message, level, log=log)
        self.__ui_state_mgr.update_dir_labels()
        
        if cleanup_result.is_success:
            messagebox.showinfo("清理完成", message)
        else:
            messagebox.showerror("清理失败", message)

    def __show_days_selection_dialog(self) -> int | None:
        """显示天数选择对话框，返回用户选择的天数或None（用户取消）"""
        days_options = [1, 3, 7, 15, 30, 60]

        # 创建自定义对话框
        dialog = tk.Toplevel(self.__root)
        dialog.title("选择清理阈值")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self.__root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = self.__root.winfo_x() + (self.__root.winfo_width() - dialog.winfo_width()) // 2
        y = self.__root.winfo_y() + (self.__root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # 添加标签
        label = ttk.Label(dialog, text="请选择清理旧文件的阈值天数:", font=("微软雅黑", 10))
        label.pack(pady=15)

        # 创建变量来存储选择的天数，默认为当前阈值
        selected_days = tk.IntVar(value=self.__cleanup_days_threshold)

        # 创建选项框架
        options_frame = ttk.Frame(dialog)
        options_frame.pack(pady=10)

        # 创建单选按钮
        for i, days in enumerate(days_options):
            rb = ttk.Radiobutton(options_frame, text=f"{days}天", variable=selected_days, value=days)
            rb.grid(row=0, column=i, padx=5)

        # 创建按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        result: dict[str, bool | int] = {"confirmed": False, "days": 0}

        ttk.Button(
            button_frame,
            text="确定",
            command=lambda: self.__on_dialog_confirm(dialog, selected_days, result)
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            button_frame,
            text="取消",
            command=lambda: self.__on_dialog_cancel(dialog, result)
        ).pack(side=tk.LEFT, padx=10)

        # 等待对话框关闭
        self.__root.wait_window(dialog)

        # 返回用户选择的天数，如果取消则返回None
        return result.get("days") if result.get("confirmed") else None

    @staticmethod
    def __on_dialog_confirm(dialog: tk.Toplevel, selected_days: tk.IntVar, result: dict[str, bool | int]) -> None:
        """处理对话框确认"""
        result["confirmed"] = True
        result["days"] = selected_days.get()
        dialog.destroy()

    @staticmethod
    def __on_dialog_cancel(dialog: tk.Toplevel, result: dict[str, bool | int]) -> None:
        """处理对话框取消"""
        result["confirmed"] = False
        dialog.destroy()
