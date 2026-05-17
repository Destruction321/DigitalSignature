# package/_gui/helpers.py
"""GUI辅助函数"""
from tkinter import messagebox
from typing import TYPE_CHECKING

from .._utils.result import Status

if TYPE_CHECKING:
    from .._core.keys.loader import KeyLoader
    from .._core.keys.managers import MultiKeyManager


def reload_current_key(multi_km: MultiKeyManager, key_loader: KeyLoader, click_reload_btn: bool = False) -> None:
    """
    重新加载当前密钥

    Args:
        multi_km (MultiKeyManager): 当前的多密钥对管理器
        key_loader (KeyLoader): 当前的密钥加载器
        click_reload_btn (bool): 是否由按钮触发，默认为False（非按钮触发）
    """
    if multi_km.current_key_id is None:
        if click_reload_btn:
            messagebox.showwarning("警告", "没有加载的密钥对")
        return

    reload_result = key_loader.load_key(multi_km.current_key_id)

    if reload_result.is_success:
        messagebox.showinfo("成功", reload_result.msg)
        return

    if reload_result.status == Status.CANCEL_INPUT:
        messagebox.showinfo("取消加载", reload_result.msg)
        return

    messagebox.showerror("加载失败", f"重新加载密钥失败:\n\n{reload_result.msg}")
