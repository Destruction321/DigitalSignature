# package/_backups/_verifier.py
"""备份验证器，负责处理备份完整性验证"""
import tkinter as tk
from threading import Thread
from pathlib import Path
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable

from ._backup_ops.ops import verify_backup_integrity
from .._utils.result import Status, Result
from .._utils.tools import format_size


class Verifier:
    """备份验证器，负责处理备份完整性验证"""
    def __init__(self, parent: tk.Widget) -> None:
        self.__parent: tk.Widget = parent
        
        # 验证对话框相关属性
        self.__verify_dialog: tk.Toplevel | None = None
        self.__progress_dialog: tk.Toplevel | None = None

        # 单个验证对话框控件
        self.__progress_label: ttk.Label | None = None
        self.__result_label: ttk.Label | None = None
        self.__close_button: ttk.Button | None = None

        # 批量验证对话框控件
        self.__progress_var: tk.IntVar | None = None
        self.__progress_bar: ttk.Progressbar | None = None
        self.__status_label: ttk.Label | None = None
        self.__result_text: ScrolledText | None = None
        self.__batch_close_button: ttk.Button | None = None


    """public methods in module 'backup'"""
    def verify_single_backup(self,
                             backup: dict[str, Any],
                             callback: Callable[[dict[str, Any]], None]) -> None:
        """
        验证单个备份
        
        Args:
            backup (dict[str, Any]): 备份信息字典
            callback (Callable[[dict[str, Any]], None]): 验证完成后的回调函数，参数为更新后的备份信息字典
        """
        backup_path = backup.get("path", "")
        if not backup_path or not Path(backup_path).exists():
            messagebox.showerror("验证失败", "备份路径不存在")
            return
        
        self.__create_single_verify_dialog(backup)
        
        thread = Thread(
            target=self.__single_verification_thread,
            args=(Path(backup_path), backup, callback),
            daemon=True
        )
        thread.start()

    def verify_all_backups(self,
                           backup_items: list[dict[str, Any]],
                           callback: Callable[[list[dict[str, Any]]], None]) -> None:
        """
        验证所有备份
        
        Args:
            backup_items (list[dict[str, Any]]): 备份信息列表
            callback (Callable[[list[dict[str, Any]]], None]): 验证完成后的回调函数，参数为更新后的备份信息列表    
        """
        if not backup_items:
            messagebox.showinfo("验证备份", "没有找到备份文件")
            return

        self.__create_batch_verify_dialog(len(backup_items))

        # 启动验证线程
        thread = Thread(
            target=self.__batch_verification_thread,
            args=(backup_items, callback),
            daemon=True
        )
        thread.start()
        
    
    """private methods"""
    def __single_verification_thread(self,
                                     backup_path: Path,
                                     backup: dict[str, Any],
                                     callback: Callable[[dict[str, Any]], None]) -> None:
        """单个备份验证线程函数"""
        try:
            if self.__verify_dialog is None:
                raise RuntimeError("单个验证对话框未创建")
            
            verify_result = verify_backup_integrity(backup_path)
            
        except Exception as e:
            verify_result = Result(status=Status.BACKUP_VERIFY_FAILED, msg=f"验证失败: {str(e)}")
            
        if self.__verify_dialog is None:
            return
        
        self.__verify_dialog.after(0, lambda: self.__update_single_result(verify_result, backup, callback))

    def __batch_verification_thread(self,
                                    backup_items: list[dict[str, Any]],
                                    callback: Callable[[list[dict[str, Any]]], None]) -> None:
        """批量验证线程函数"""
        valid_count = 0
        invalid_count = 0
        total_count = len(backup_items)

        for i, backup in enumerate(backup_items):
            # 处理当前备份
            if self.__progress_dialog is None:  # 中途关闭，停止验证
                return
            
            self.__process_single_backup_in_batch(i, backup, total_count)

            # 统计结果
            if backup.get("integrity_valid", False):
                valid_count += 1
            else:
                invalid_count += 1

        # 完成验证
        verification_result = [total_count, valid_count, invalid_count]
        
        if self.__progress_dialog is None:
            return
        
        self.__progress_dialog.after(
            0, lambda: self.__finish_batch_verification(verification_result, callback, backup_items)
        )

    def __process_single_backup_in_batch(self, index: int, backup: dict[str, Any], total_count: int) -> None:
        """在批量验证中处理单个备份"""
        if self.__progress_dialog is None:
            return

        # 更新进度
        backup_path = Path(backup.get("path", ""))
        self.__progress_dialog.after(
            0, lambda idx=index + 1,
            name=backup["name"]: self.__update_batch_progress(idx, total_count, f"正在验证: {name}")
        )

        try:
            if backup_path and backup_path.exists():
                verify_result = verify_backup_integrity(backup_path)
                
                is_valid = verify_result.is_success
                message = verify_result.msg

                # 更新备份信息
                backup["integrity_valid"] = is_valid
                backup["integrity_message"] = message
                backup["checksum_data"] = verify_result.data
                backup["display_name"] = f"✓ {backup["name"]}" if is_valid else f"⚠ {backup["name"]}"

                # 记录结果
                if is_valid:
                    result = f"✓ {backup["name"]}: 验证通过\n"
                else:
                    result = f"⚠ {backup["name"]}: {message}\n"

                self.__progress_dialog.after(0, lambda r=result: self.__add_batch_result(r))
            else:
                # 备份路径不存在
                backup["integrity_valid"] = False
                backup["integrity_message"] = "备份路径不存在"
                backup["display_name"] = f"{backup["name"]}"
                result = f"{backup["name"]}: 备份路径不存在\n"
                self.__progress_dialog.after(0, lambda r=result: self.__add_batch_result(r))

        except Exception as e:
            # 验证失败
            backup["integrity_valid"] = False
            backup["integrity_message"] = f"验证失败: {str(e)}"
            backup["display_name"] = f"{backup["name"]}"
            result = f"{backup["name"]}: 验证失败 - {str(e)}\n"
            self.__progress_dialog.after(0, lambda r=result: self.__add_batch_result(r))

    def __create_single_verify_dialog(self, backup: dict[str, Any]) -> None:
        """创建单个验证对话框"""
        self.__verify_dialog = tk.Toplevel(self.__parent)
        self.__verify_dialog.title("验证备份完整性")
        self.__verify_dialog.geometry("400x250")
        self.__verify_dialog.transient(self.__parent.winfo_toplevel())
        self.__verify_dialog.grab_set()
        self.__center_dialog(self.__verify_dialog)

        # 创建UI
        ttk.Label(
            self.__verify_dialog,
            text=f"正在验证备份：{backup["name"]}",
            font=("微软雅黑", 11, "bold")
        ).pack(pady=20)

        self.__progress_label = ttk.Label(self.__verify_dialog, text="正在计算校验和...", font=("微软雅黑", 10))
        self.__progress_label.pack(pady=10)

        self.__result_label = ttk.Label(self.__verify_dialog, text="", font=("微软雅黑", 10))
        self.__result_label.pack(pady=10)

        button_frame = ttk.Frame(self.__verify_dialog)
        button_frame.pack(pady=20)

        self.__close_button = (
            ttk.Button(button_frame, text="关闭", command=self.__close_single_dialog, state=tk.DISABLED)
        )
        self.__close_button.pack()

    def __update_single_result(self,
                               verify_result: Result,
                               backup: dict[str, Any],
                               callback: Callable[[dict[str, Any]], None]) -> None:
        """更新单个验证结果"""
        assert self.__progress_label is not None, "进度标签未创建"
        assert self.__result_label is not None, "结果标签未创建"
        assert self.__close_button is not None, "关闭按钮未创建"

        self.__progress_label.config(text="验证完成")
        if verify_result.is_success:
            self.__result_label.config(text=f"✓ {verify_result.msg}", foreground="green")
        else:
            self.__result_label.config(text=f"⚠ {verify_result.msg}", foreground="red")
            
        if verify_result.data:
            details = (
                f"备份类型: {verify_result.data.get("backup_type", "未知")}\n"
                f"文件数量: {verify_result.data.get("file_count", 0)} 个\n"
                f"总大小: {format_size(verify_result.data.get("total_size", 0))}\n"
                f"创建时间: {verify_result.data.get("created_time", "未知")}"
            )
            self.__result_label.config(text=self.__result_label.cget("text") + f"\n\n{details}")
            
        self.__close_button.config(state=tk.NORMAL)
        backup["integrity_valid"] = verify_result.is_success
        backup["integrity_message"] = verify_result.msg
        backup["checksum_data"] = verify_result.data
        backup["display_name"] = f"✓ {backup["name"]}" if verify_result.is_success else f"⚠ {backup["name"]}"
        
        callback(backup)

    def __close_single_dialog(self) -> None:
        """关闭单个验证对话框"""
        if self.__verify_dialog is not None:
            self.__verify_dialog.destroy()
            self.__verify_dialog = None
            self.__progress_label = None
            self.__result_label = None
            self.__close_button = None

    def __create_batch_verify_dialog(self, total_count: int) -> None:
        """创建批量验证对话框"""
        self.__progress_dialog = tk.Toplevel(self.__parent)
        self.__progress_dialog.title("验证所有备份")
        self.__progress_dialog.geometry("500x400")
        self.__progress_dialog.transient(self.__parent.winfo_toplevel())
        self.__progress_dialog.grab_set()
        self.__center_dialog(self.__progress_dialog)

        # 创建UI
        ttk.Label(
            self.__progress_dialog,
            text="正在验证所有备份完整性...",
            font=("微软雅黑", 11, "bold")
        ).pack(pady=20)

        self.__progress_var = tk.IntVar()
        self.__progress_bar = ttk.Progressbar(
            self.__progress_dialog,
            variable=self.__progress_var,
            maximum=total_count
        )
        self.__progress_bar.pack(fill=tk.X, padx=20, pady=10)

        self.__status_label = ttk.Label(self.__progress_dialog, text="准备开始...", font=("微软雅黑", 10))
        self.__status_label.pack(pady=10)

        self.__result_text = ScrolledText(
            self.__progress_dialog, height=10, font=("Consolas", 9), state=tk.DISABLED
        )
        self.__result_text.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        button_frame = ttk.Frame(self.__progress_dialog)
        button_frame.pack(pady=10)

        self.__batch_close_button = ttk.Button(
            button_frame, text="关闭", command=self.__close_batch_dialog, state=tk.DISABLED
        )
        self.__batch_close_button.pack()

    def __update_batch_progress(self, current: int, total: int, status: str) -> None:
        """更新批量验证进度"""
        assert self.__progress_var is not None, "进度变量未创建"
        assert self.__status_label is not None, "状态标签未创建"
        
        self.__progress_var.set(current)
        self.__status_label.config(text=f"{status} ({current}/{total})")

    def __add_batch_result(self, result: str) -> None:
        """添加批量验证结果到文本区域"""
        assert self.__result_text is not None, "结果文本区域未创建"
        
        self.__result_text.config(state=tk.NORMAL)
        self.__result_text.insert(tk.END, result)
        self.__result_text.see(tk.END)
        self.__result_text.config(state=tk.DISABLED)

    def __finish_batch_verification(self,
                                    verification_result: list[int],
                                    callback: Callable[[list[dict[str, Any]]], None],
                                    backup_items: list[dict[str, Any]]) -> None:
        """完成批量验证"""
        assert self.__status_label is not None, "状态标签未创建"
        assert self.__batch_close_button is not None, "关闭按钮未创建"
        assert self.__progress_var is not None, "进度变量未创建"
        
        total = verification_result[0]
        valid = verification_result[1]
        invalid = verification_result[2]
        
        self.__progress_var.set(total)
        self.__status_label.config(text="验证完成")

        summary = f"\n{"=" * 50}\n验证完成！\n"
        summary += f"总计: {total} 个备份\n"
        summary += f"有效: {valid} 个\n"
        summary += f"无效: {invalid} 个\n"

        self.__add_batch_result(summary)
        self.__batch_close_button.config(state=tk.NORMAL)

        # 调用回调函数
        callback(backup_items)

    def __close_batch_dialog(self) -> None:
        """关闭批量验证对话框"""
        if self.__progress_dialog is not None:
            self.__progress_dialog.destroy()
            self.__progress_dialog = None
            self.__progress_var = None
            self.__progress_bar = None
            self.__status_label = None
            self.__result_text = None
            self.__batch_close_button = None

    def __center_dialog(self, dialog: tk.Toplevel) -> None:
        """居中显示对话框"""
        dialog.update_idletasks()
        x = (self.__parent.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (self.__parent.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
