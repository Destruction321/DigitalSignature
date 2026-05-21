# package/_backups/_backups.py
"""数字签名窗口备份方法模块"""
from tkinter import Menu, messagebox
from tkinter.ttk import Button
from typing import Callable, TYPE_CHECKING

from ._dialog import dialog_show
from ._backup_ops.ops import create_backup, list_backups_with_integrity
from ._restore import Restore
from .._utils.enums import DirType
from .._utils.result import Status
from .._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from tkinter import Tk
    from .._core.keys.loader import KeyLoader
    from .._core.keys.managers import MultiKeyManager
        

class BackUps:
    """数字签名窗口备份方法模块"""
    def __init__(self,
                 root: Tk,
                 backup_buttons: dict[str, Button],
                 refresh_callback: Callable[[], None],
                 multi_km: MultiKeyManager,
                 key_loader: KeyLoader) -> None:
        self.__root: Tk = root
        self.__backup_buttons: dict[str, Button] = backup_buttons  # 引用传递
        
        # Restore所需参数
        self.__refresh_callback: Callable[[], None] = refresh_callback
        self.__multi_km: MultiKeyManager = multi_km
        self.__key_loader: KeyLoader = key_loader
    
    
    """public methods -- bind to buttons"""
    def show_backup_options(self) -> None:
        """显示备份选项菜单"""
        menu = Menu(self.__root, tearoff=0)
        menu.add_command(label="完整备份", command=lambda: self.__backup_data(DirType.FULL, "完整"))
        menu.add_command(label="仅备份密钥", command=lambda: self.__backup_data(DirType.KEYS, "密钥"))
        menu.add_command(label="仅备份文本", command=lambda: self.__backup_data(DirType.TEXTS, "文本"))
        menu.add_command(label="仅备份签名", command=lambda: self.__backup_data(DirType.SIGNATURES, "签名"))

        backup_button = self.__backup_buttons.get("创建备份")
        if backup_button is not None:
            x = backup_button.winfo_rootx()
            y = backup_button.winfo_rooty() + backup_button.winfo_height()
            menu.post(x, y)
        else:
            menu.post(self.__root.winfo_pointerx(), self.__root.winfo_pointery())

    def restore_backup_dialog(self) -> None:
        """恢复备份对话框"""
        backups = list_backups_with_integrity()
        if not backups.is_success:
            messagebox.showinfo("恢复备份", "没有找到可用的备份文件")
            return

        dialog = Restore(
            refresh_key_callback=self.__refresh_callback,
            reload_key_callback=self.reload_current_key
        )
        dialog.show(self.__root)

    def backup_manager_dialog(self) -> None:
        """统一备份管理对话框"""
        dialog_show(self.__root)

    def reload_current_key(self, click_reload_btn: bool = False) -> None:
        """
        重新加载当前密钥

        Args:
            multi_km (MultiKeyManager): 当前的多密钥对管理器
            key_loader (KeyLoader): 当前的密钥加载器
            click_reload_btn (bool): 是否由按钮触发，默认为False（非按钮触发）
        """
        if self.__multi_km.current_key_id is None:
            if click_reload_btn:
                messagebox.showwarning("警告", "没有加载的密钥对")
            return

        reload_result = self.__key_loader.load_key(self.__multi_km.current_key_id)

        if reload_result.is_success:
            messagebox.showinfo("成功", reload_result.msg)
            return

        if reload_result.status == Status.CANCEL_INPUT:
            messagebox.showinfo("取消加载", reload_result.msg)
            return

        messagebox.showerror("加载失败", f"重新加载密钥失败:\n\n{reload_result.msg}")


    """private methods"""
    def __backup_data(self, dir_type: DirType, data_type: str) -> None:
        """备份数据"""
        backup_result = create_backup(dir_type)
        self.__handle_backup_result(backup_result.is_success, backup_result.msg, f"{data_type}备份")

    def __handle_backup_result(self, success: bool, result: str, operation: str) -> None:
        """处理备份结果"""
        if success:
            get_ui_state_manager().update_status(f"{operation}完成")
            messagebox.showinfo("备份成功", f"{operation}完成:\n\n{result}")
        else:
            messagebox.showerror("备份失败", f"{operation}失败:\n\n{result}")
