"""数字签名窗口备份方法模块"""
import tkinter as tk
from tkinter import messagebox, ttk
from typing import cast, TYPE_CHECKING

from . import utils
from .._gui.key_management_tab import KeyManagementTab
from .._services.backup import backup_services
from .._services.backup.backup_manager import BackupManager
from .._services.backup.backup_restore import BackupRestore
from .._utils import DirType
from .._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from .._core.keys.key_loader import KeyLoader
    from .._core.keys.key_manager import MultiKeyManager
        

class BackUps:
    """数字签名窗口备份方法模块"""
    def __init__(self, root: tk.Tk,
                 backup_buttons: dict[str, ttk.Button],
                 dir_labels: dict[DirType, ttk.Label],
                 key_tab: KeyManagementTab,
                 multi_km: MultiKeyManager,
                 key_loader: KeyLoader) -> None:
        self.__root: tk.Tk = root
        self.__backup_buttons: dict[str, ttk.Button] = backup_buttons
        self.__dir_labels: dict[DirType, ttk.Label] = dir_labels
        self.__key_tab: KeyManagementTab = key_tab
        self.__multi_km: MultiKeyManager = multi_km
        self.__key_loader: KeyLoader = key_loader
        self.__ui_state_mgr = get_ui_state_manager()
    
    
    """public methods -- bind to buttons"""
    def show_backup_options(self) -> None:
        """显示备份选项菜单"""
        menu: tk.Menu = tk.Menu(self.__root, tearoff=0)
        menu.add_command(label="完整备份", command=self.__backup_all_data)
        menu.add_command(label="仅备份密钥", command=self.__backup_keys_only)
        menu.add_command(label="仅备份文本", command=self.__backup_texts_only)
        menu.add_command(label="仅备份签名", command=self.__backup_signatures_only)

        try:
            backup_button = self.__root.nametowidget(str(self.__backup_buttons.get("创建备份")))
            x: int = backup_button.winfo_rootx()
            y: int = backup_button.winfo_rooty() + backup_button.winfo_height()
            menu.post(x, y)
        except AttributeError:
            menu.post(self.__root.winfo_pointerx(), self.__root.winfo_pointery())

    def restore_backup_dialog(self) -> None:
        """恢复备份对话框"""
        backups = backup_services.list_backups_with_integrity()
        if not backups:
            messagebox.showinfo("恢复备份", "没有找到可用的备份文件")
            return

        dialog = BackupRestore(
            self.__root,
            self.__ui_state_mgr.update_status,
            lambda: utils.update_directory_info(self.__dir_labels),
            self.__key_tab.refresh_key_list,
            lambda: utils.reload_current_key(self.__multi_km, self.__key_loader)
        )
        dialog.show()

    def backup_manager_dialog(self) -> None:
        """统一备份管理对话框"""
        parent_window = cast(tk.Widget, self.__root.winfo_toplevel())
        dialog = BackupManager(parent_window, self.__ui_state_mgr.update_status)
        dialog.show()


    """private methods"""
    def __backup_all_data(self) -> None:
        """备份所有数据"""
        backup_result = backup_services.create_backup(DirType.FULL)
        self.__handle_backup_result(backup_result.is_success(), backup_result.msg, "数据备份")

    def __backup_keys_only(self) -> None:
        """仅备份密钥"""
        backup_result = backup_services.create_backup(DirType.KEYS)
        self.__handle_backup_result(backup_result.is_success(), backup_result.msg, "密钥备份")

    def __backup_texts_only(self) -> None:
        """仅备份文本"""
        backup_result = backup_services.create_backup(DirType.TEXTS)
        self.__handle_backup_result(backup_result.is_success(), backup_result.msg, "文本备份")

    def __backup_signatures_only(self) -> None:
        """仅备份签名"""
        backup_result = backup_services.create_backup(DirType.SIGNATURES)
        self.__handle_backup_result(backup_result.is_success(), backup_result.msg, "签名备份")

    def __handle_backup_result(self, success: bool, result: str, operation: str) -> None:
        """处理备份结果"""
        if success:
            self.__ui_state_mgr.update_status(f"{operation}完成")
            messagebox.showinfo("备份成功", f"{operation}完成:\n\n{result}")
        else:
            messagebox.showerror("备份失败", f"{operation}失败:\n\n{result}")
