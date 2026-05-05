# package/_app/_initializer.py
"""数字签名窗口初始化器"""
from collections import Counter
from glob import glob
from logging import warning
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING
from shutil import move

from .._core.keys.loader import KeyLoader
from .._core.keys.managers import SingleKeyManager, MultiKeyManager
from .._gui import MainWindow
from .._utils.constants import BASE_DIR, KEYS_CONFIG_FILE
from .._utils.enums import DirType, KeyType, FileType
from .._utils.result import Status
from .._utils.tools import get_path, update_directory_info
from .._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from tkinter import Tk
    from .._utils.ui_state_manager import UIStateManager


class Initializer:
    """数字签名窗口初始化器"""
    def __init__(self, root: Tk) -> None:
        self.__ui_state_mgr: UIStateManager = get_ui_state_manager()
        self.__multi_km: MultiKeyManager = MultiKeyManager()
        self.__key_loader: KeyLoader = KeyLoader(
            multi_key_manager=self.__multi_km,
            parent=root,
            key_loaded_callback=self.__on_key_loaded,
            update_status_callback=self.__ui_state_mgr.update_status,
        )
        
        self.__current_km: SingleKeyManager | None = None  # 当前密钥管理器
        self.__ui: MainWindow = MainWindow(root, self.__multi_km, self.__key_loader)
        
        
    @property
    def current_km(self) -> SingleKeyManager | None:
        return self.__current_km
    
    @property
    def ui(self) -> MainWindow:
        return self.__ui
    
    
    """public methods"""
    def auto_load_current_key(self) -> None:
        """程序启动时自动加载当前密钥"""
        if self.__multi_km.current_key_id is None:
            self.__ui_state_mgr.update_status("请先在密钥管理标签页加载密钥对")
            return

        if self.__ui.key_tab is None:
            messagebox.showerror("错误", "密钥管理页未初始化")
            return

        try:
            # 使用KeyLoader静默加载
            loading_result = self.__key_loader.load_key(self.__multi_km.current_key_id, silent=True)
            success = loading_result.is_success
            result = loading_result.data
            
            if success and isinstance(result, SingleKeyManager):
                # 设置密钥管理器
                self.__set_current_key_manager(result)
                update_directory_info(self.__ui.dir_labels)
                self.__ui.key_tab.loaded_key_id = self.__multi_km.current_key_id
                self.__ui_state_mgr.update_status(f"自动加载密钥成功: {self.__multi_km.current_key_id}")
            elif not success and loading_result.status == Status.NEED_PASSWORD:
                self.__ui_state_mgr.update_status(f"密钥 '{self.__multi_km.current_key_id}' 已加密，请手动加载")
            else:
                self.__ui_state_mgr.update_status("自动加载密钥失败，请手动加载")

        except Exception as e:
            self.__ui_state_mgr.update_status(f"自动加载密钥出错: {e}")

        # 更新密钥标签页显示
        self.__ui.key_tab.update_key_status()
    
    
    """private methods"""
    def __on_key_loaded(self, key_manager: SingleKeyManager | None) -> None:
        """密钥加载成功时的回调"""
        if key_manager is None or not hasattr(key_manager, "private_key"):
            self.__ui_state_mgr.update_status("密钥管理器无效，无法创建数字签名实例")
            self.__current_km = None
            self.__multi_km.current_key_id = None

            # 通知KeyManagementTab加载失败
            if self.__ui.key_tab:
                self.__ui.key_tab.loaded_key_id = None
            return

        try:
            key_id = getattr(key_manager, "key_id", None)
            if key_id is None:
                key_id = self.__multi_km.current_key_id

            if key_id:
                self.__multi_km.current_key_id = key_id
                save_result = self.__multi_km.save_keys_config()
                if not save_result.is_success:
                    messagebox.showerror("密钥配置保存失败", f"密钥加载成功但配置保存失败：{save_result.msg}")
                    
                # 通知KeyManagementTab密钥已真正加载
                if self.__ui.key_tab:
                    self.__ui.key_tab.loaded_key_id = key_id

            self.__current_km = key_manager
            self.__update_key_managers()

            self.__ui_state_mgr.update_status(f"密钥对 '{key_id}' 已加载并准备就绪")
            update_directory_info(self.__ui.dir_labels)

        except Exception as e:
            self.__ui_state_mgr.update_status(f"创建数字签名实例失败: {e}")
            self.__current_km = None
            self.__multi_km.current_key_id = None

            # 通知KeyManagementTab加载失败
            if self.__ui.key_tab:
                self.__ui.key_tab.loaded_key_id = None

    def __set_current_key_manager(self, key_manager: SingleKeyManager) -> None:
        """设置当前密钥管理器"""
        if not hasattr(key_manager, "private_key"):
            self.__current_km = None
            return

        try:
            # 创建数字签名实例
            self.__current_km = key_manager

            # 更新所有标签页
            self.__update_key_managers()

            # 更新状态
            key_id = getattr(key_manager, "key_id", "未知")
            self.__ui_state_mgr.update_status(f"密钥对 '{key_id}' 已加载并准备就绪")
            update_directory_info(self.__ui.dir_labels)

        except Exception as e:
            messagebox.showerror("数字签名实例设置失败", f"{e}")
            self.__current_km = None

    def __update_key_managers(self) -> None:
        """更新所有标签页的密钥管理器"""
        assert self.__current_km is not None
        
        if self.__ui.text_tab:
            self.__ui.text_tab.km = self.__current_km

        if self.__ui.file_tab:
            self.__ui.file_tab.km = self.__current_km
           

def migrate_existing_files() -> None:
    """迁移现有文件到新的目录结构"""
    PRIVATE_, PUBLIC_, _PEM, _TXT, _SIG = _get_constants()
    migration_map: dict[DirType, list[str]] = {
        DirType.KEYS: [
            f"{PRIVATE_}key_*{_PEM}",
            f"{PUBLIC_}key_*{_PEM}",
            KEYS_CONFIG_FILE
        ],
        DirType.TEXTS:      [_TXT],
        DirType.SIGNATURES: [_SIG]
    }

    exclude_files = {f"requirements{_TXT}", f"README{_TXT}"}
    migrated_categories: list[DirType] = []

    for category, patterns in migration_map.items():
        for pattern in patterns:
            for old_file in glob(pattern):
                old_path = Path(old_file)

                invalid = (
                    old_path.name in exclude_files
                    or not old_path.is_file()
                    or old_file.startswith(BASE_DIR)
                )
                
                if invalid:
                    continue

                new_path = Path(get_path(category, old_path.name))
                if new_path.exists():
                    continue

                try:
                    move(old_file, new_path)
                    migrated_categories.append(category)
                except Exception as e:
                    warning(f"迁移文件失败 {old_file}: {e}")

    if not migrated_categories:
        return

    category_counts = Counter(migrated_categories)
    migration_info = "已自动迁移文件到data目录:\n\n" + "".join(
        f"{category}: {count} 个文件\n"
        for category, count in category_counts.items()
    )
    
    messagebox.showinfo("文件迁移", migration_info)

def _get_constants() -> tuple[str, str, str, str, str]:
    """字符串导出"""
    return (
        f"{KeyType.PRIVATE.value}_",
        f"{KeyType.PUBLIC.value}_",
        FileType.KEY.value,
        FileType.TEXT.value,
        FileType.SIGNATURE.value
    )
