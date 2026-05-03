# package/_backups/_backups.py
"""数字签名窗口备份方法模块"""
from tkinter import Menu, messagebox, Widget
from tkinter.ttk import Button, Label
from typing import cast, Callable, TYPE_CHECKING

from .dialog import dialog_show
from ._backup_ops.ops import create_backup, list_backups_with_integrity
from ._restore import Restore
from .._utils.enums import DirType
from .._utils.tools import reload_current_key, update_directory_info
from .._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from tkinter import Tk
    from .._core.keys.loader import KeyLoader
    from .._core.keys.managers import MultiKeyManager
    from .._utils.ui_state_manager import UIStateManager
        

class BackUps:
    """数字签名窗口备份方法模块"""
    def __init__(self,
                 root: Tk,
                 backup_buttons: dict[str, Button],
                 dir_labels: dict[DirType, Label],
                 refresh_callback: Callable[[], None],
                 multi_km: MultiKeyManager,
                 key_loader: KeyLoader) -> None:
        self.__root: Tk = root
        self.__backup_buttons: dict[str, Button] = backup_buttons
        self.__dir_labels: dict[DirType, Label] = dir_labels
        self.__refresh_callback: Callable[[], None] = refresh_callback
        self.__multi_km: MultiKeyManager = multi_km
        self.__key_loader: KeyLoader = key_loader
        self.__ui_state_mgr: UIStateManager = get_ui_state_manager()
    
    
    """public methods -- bind to buttons"""
    def show_backup_options(self) -> None:
        """显示备份选项菜单"""
        menu = Menu(self.__root, tearoff=0)
        menu.add_command(label="完整备份", command=lambda: self.__backup_data(DirType.FULL, "完整"))
        menu.add_command(label="仅备份密钥", command=lambda: self.__backup_data(DirType.KEYS, "密钥"))
        menu.add_command(label="仅备份文本", command=lambda: self.__backup_data(DirType.TEXTS, "文本"))
        menu.add_command(label="仅备份签名", command=lambda: self.__backup_data(DirType.SIGNATURES, "签名"))

        try:
            backup_button = self.__root.nametowidget(str(self.__backup_buttons.get("创建备份")))
            x: int = backup_button.winfo_rootx()
            y: int = backup_button.winfo_rooty() + backup_button.winfo_height()
            menu.post(x, y)
        except AttributeError:
            menu.post(self.__root.winfo_pointerx(), self.__root.winfo_pointery())

    def restore_backup_dialog(self) -> None:
        """恢复备份对话框"""
        backups = list_backups_with_integrity()
        if not backups:
            messagebox.showinfo("恢复备份", "没有找到可用的备份文件")
            return

        dialog = Restore(
            parent=self.__root,
            update_status_callback=self.__ui_state_mgr.update_status,
            update_dir_callback=lambda: update_directory_info(self.__dir_labels),
            refresh_key_callback=self.__refresh_callback,
            reload_key_callback=lambda: reload_current_key(self.__multi_km, self.__key_loader)
        )
        dialog.show()

    def backup_manager_dialog(self) -> None:
        """统一备份管理对话框"""
        parent_window = cast(Widget, self.__root.winfo_toplevel())
        dialog_show(parent_window, self.__ui_state_mgr.update_status)


    """private methods"""
    def __backup_data(self, dir_type: DirType, data_type: str) -> None:
        """备份数据"""
        backup_result = create_backup(dir_type)
        self.__handle_backup_result(backup_result.is_success, backup_result.msg, f"{data_type}备份")

    def __handle_backup_result(self, success: bool, result: str, operation: str) -> None:
        """处理备份结果"""
        if success:
            self.__ui_state_mgr.update_status(f"{operation}完成")
            messagebox.showinfo("备份成功", f"{operation}完成:\n\n{result}")
        else:
            messagebox.showerror("备份失败", f"{operation}失败:\n\n{result}")
