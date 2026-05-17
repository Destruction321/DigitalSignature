# package/_gui/_key_management_tab/_recovery_dialog.py
"""弹出恢复选择对话框"""
import tkinter as tk
from tkinter import ttk


def ask_recovery_choice(key_id: str) -> tuple[bool, bool]:
    """
    弹出恢复选择对话框
    
    Args:
        key_id (str): 加密密钥ID
    
    Returns:
        choice, remember (tuple[bool, bool]): 用户选择和是否记住选择的元组
    """
    dialog = tk.Toplevel()
    dialog.title("加密密钥恢复")
    dialog.grab_set()
    dialog.update_idletasks()
    x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    dialog.resizable(False, False)

    choice = tk.BooleanVar(value=False)
    remember = tk.BooleanVar(value=False)
    confirmed = tk.BooleanVar(value=False)

    ttk.Label(
        dialog,
        text=f"发现加密密钥 '{key_id}'，您想要做什么？",
        font=("微软雅黑", 10, "bold")
    ).pack(padx=20, pady=(20, 10))

    ttk.Radiobutton(
        dialog, text="重置密码（需要输入旧密码）",
        variable=choice, value=True
    ).pack(anchor=tk.W, padx=30)

    ttk.Radiobutton(
        dialog, text="跳过，稍后手动处理",
        variable=choice, value=False
    ).pack(anchor=tk.W, padx=30, pady=(5, 10))

    ttk.Checkbutton(
        dialog, text="为后续加密密钥保留此选择",
        variable=remember
    ).pack(anchor=tk.W, padx=30, pady=(0, 15))

    ttk.Button(
        dialog, text="确定",
        command=lambda: _on_confirm(confirmed, dialog)
    ).pack(pady=(0, 20))

    dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
    dialog.wait_window()
    return confirmed.get() and choice.get(), confirmed.get() and remember.get()

def _on_confirm(confirmed: tk.BooleanVar, dialog: tk.Toplevel) -> None:
    confirmed.set(True)
    dialog.destroy()
