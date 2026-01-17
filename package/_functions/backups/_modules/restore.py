# package/_utils/backup/backup_restore.py
"""备份恢复器"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Any, Callable, cast

from . import backup_utils


class BackupRestore:
    """备份恢复器"""
    def __init__(self, parent: tk.Tk,
                 update_status_callback: Callable[[str], None],
                 update_dir_callback: Callable[[], None],
                 refresh_key_callback: Callable[[], None],
                 reload_key_callback: Callable[[], None]) -> None:
        self.__parent = parent
        self.__update_status = update_status_callback
        self.__update_dir = update_dir_callback
        self.__refresh_key = refresh_key_callback
        self.__reload_key = reload_key_callback

        self.__dialog: tk.Toplevel | None = None
        self.__listbox: tk.Listbox | None = None
        self.__overwrite_var: tk.BooleanVar | None = None
        self.__backup_items: list[dict[str, Any]] = []
        self.__skip_verify_var: tk.BooleanVar | None = None


    """public methods"""
    def show(self) -> None:
        """显示对话框"""
        backups = backup_utils.list_backups()

        if not backups:
            messagebox.showinfo("恢复备份", "没有找到可用的备份文件")
            return

        self.__dialog = tk.Toplevel(self.__parent)
        self.__dialog.title("恢复备份")
        self.__dialog.geometry("600x500")
        self.__dialog.transient(self.__parent)
        self.__dialog.grab_set()

        self.__dialog.update_idletasks()
        x = (self.__parent.winfo_screenwidth() - self.__dialog.winfo_width()) // 2
        y = (self.__parent.winfo_screenheight() - self.__dialog.winfo_height()) // 2
        self.__dialog.geometry(f"+{x}+{y}")

        self.__create_ui(backups)
        cast(tk.Listbox, self.__listbox).bind("<Double-Button-1>", lambda _event: self.__on_restore())


    """private methods"""
    def __create_ui(self, backups: list[dict[str, Any]]) -> None:
        """创建UI"""
        main_frame = ttk.Frame(self.__dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            main_frame,
            text="选择要恢复的备份:",
            font=("微软雅黑", 11, "bold")
        ).pack(anchor=tk.W, pady=(0, 15))

        list_frame = ttk.LabelFrame(main_frame, text="可用备份", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        list_container = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.__listbox = tk.Listbox(list_container, height=8, font=("Consolas", 9))
        scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.__listbox.yview)
        self.__listbox.configure(yscrollcommand=scrollbar.set)

        self.__listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.__populate_list(backups)

        options_frame = ttk.Frame(main_frame)
        options_frame.pack(fill=tk.X, pady=15)

        self.__overwrite_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame,
            text="覆盖现有数据（将删除当前所有数据）",
            variable=self.__overwrite_var
        ).pack(anchor=tk.W)

        # 跳过验证选项
        self.__skip_verify_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="跳过完整性验证（不推荐）",
            variable=self.__skip_verify_var
        ).pack(anchor=tk.W, pady=(5, 0))

        # 在警告信息中强调完整性验证的重要性
        ttk.Label(
            options_frame,
            text="注意：建议保持完整性验证开启，以确保备份数据完整可靠",
            foreground="orange",
            font=("微软雅黑", 9)
        ).pack(anchor=tk.W, pady=(5, 0))

        ttk.Label(
            options_frame,
            text="警告：恢复备份将替换当前数据，请谨慎操作！",
            foreground="red",
            font=("微软雅黑", 9, "bold")
        ).pack(anchor=tk.W, pady=(10, 0))

        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="恢复选中备份", command=self.__on_restore).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=cast(tk.Toplevel, self.__dialog).destroy).pack(side=tk.LEFT, padx=5)

    def __populate_list(self, backups: list[dict[str, Any]]) -> None:
        """填充备份列表"""
        self.__backup_items = []
        for backup in backups:
            time_str = backup["created_time"].strftime("%Y-%m-%d %H:%M:%S")
            size_str = f"{backup["size"]:,} 字节"
            display_text = f"{str(backup["name"]):30} | {time_str} | {size_str:>12}"
            cast(tk.Listbox, self.__listbox).insert(tk.END, display_text)
            self.__backup_items.append(backup)

    def __on_restore(self) -> None:
        """执行恢复（强制验证完整性）"""
        selection = cast(tk.Listbox, self.__listbox).curselection()
        if not selection:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return
        
        selected_backup = self.__backup_items[int(selection[0])]
        backup_path = Path(selected_backup["path"])
        
        if cast(tk.BooleanVar, self.__skip_verify_var).get():
            self.__restore(selected_backup)
            return
            
        if not hasattr(backup_utils, "verify_backup_integrity"):
            self.__restore(selected_backup)
            return
            
        verify_result = backup_utils.verify_backup_integrity(backup_path)
        if verify_result.is_success():
            self.__restore(selected_backup)
            return
            
        response = messagebox.askyesno(
            "备份完整性验证失败",
            f"备份完整性验证失败：\n\n{verify_result.msg}\n\n是否仍然继续恢复？（不推荐）"
        )
        if not response:
            return
        
        self.__restore(selected_backup)

    def __restore(self, selected_backup: dict[str, Any]) -> None:
        self.__overwrite_var = cast(tk.BooleanVar, self.__overwrite_var)
        operation = "覆盖" if self.__overwrite_var.get() else "合并"
        confirm_msg = (
            f"确定要{operation}恢复备份吗？\n\n"
            f"备份名称: {selected_backup["name"]}\n"
            f"创建时间: {selected_backup["created_time"].strftime("%Y-%m-%d %H:%M:%S")}\n"
            f"备份大小: {selected_backup["size"]:,} 字节\n\n"
            f"这将{"删除当前所有数据并" if self.__overwrite_var.get() else ""}从备份恢复数据。\n此操作不可逆！"
        )
        if not messagebox.askyesno("确认恢复", confirm_msg):
            return
        
        try:
            restore_result = backup_utils.restore_backup(
                Path(selected_backup["path"]), overwrite=self.__overwrite_var.get()
            )
            
            if restore_result.is_success():
                self.__update_status(f"备份恢复完成: {selected_backup["name"]}")
                messagebox.showinfo("恢复成功", f"备份恢复成功！\n\n{restore_result.msg}")
                cast(tk.Toplevel, self.__dialog).destroy()
                self.__update_dir()
                self.__refresh_key()
                self.__reload_key()
            else:
                messagebox.showerror("恢复失败", f"备份恢复失败：\n{restore_result.msg}")
        except Exception as e:
            messagebox.showerror("恢复失败", str(e))
