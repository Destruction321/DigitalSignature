# package/_backups/_dialog/_dialog_show.py
"""显示备份管理对话框"""
from tkinter import TclError, Toplevel
from tkinter.messagebox import showerror
from typing import TYPE_CHECKING

from . import _dialog_creator
from .._backup_ops.ops import list_backups

if TYPE_CHECKING:
    from tkinter import Misc


def show(parent: Misc) -> None:
    """
    显示备份管理对话框
    
    Args:
        parent (tk.Misc): 父窗口
    """
    backups = list_backups()
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
    _dialog_creator.create_ui(parent, backups.data, dialog)
