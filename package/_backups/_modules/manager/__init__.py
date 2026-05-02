# package/_backups/_modules/manager/__init__.py
from tkinter import TclError, Toplevel
from tkinter.messagebox import showerror
from typing import Callable, TYPE_CHECKING

from . import _dialog_creator
from ..._backup_utils import list_backups_with_integrity

if TYPE_CHECKING:
    from tkinter import Widget


def show(parent: Widget, update_status_callback: Callable[[str], None]) -> None:
    """
    显示统一备份管理对话框
    
    Args:
        parent (tk.Widget): 父窗口
        update_status_callback (Callable[[str], None]): 状态更新回调函数
    """
    backups = list_backups_with_integrity()
    if not backups.is_success:
        showerror("备份管理", backups.msg)
        return

    dialog = Toplevel(parent)
    dialog.title("备份管理")
    dialog.geometry("850x650")

    try:
        parent_top_level = parent.winfo_toplevel()
        dialog.transient(parent_top_level)
    except TclError:
        dialog.transient()

    dialog.grab_set()
    _dialog_creator.center_dialog(parent, dialog)
    _dialog_creator.create_ui(parent, backups.data, dialog, update_status_callback)
