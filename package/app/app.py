"""数字签名系统主模块"""
from typing import TYPE_CHECKING

from ._modules.app_utils import update_directory_info
from ._modules.initializer import Initializer, migrate_existing_files

if TYPE_CHECKING:
    from tkinter import Tk
    from .._core.keys.manager import SingleKeyManager


class APP:
    """数字签名系统主模块"""
    def __init__(self, root: Tk) -> None:
        # 创建初始化器
        self.__initializer: Initializer = Initializer(root)
        
        # 创建UI
        self.__initializer.ui.setup_main_window()
        self.__initializer.ui.setup_ui()
        
        # 数据处理
        migrate_existing_files()
        update_directory_info(self.__initializer.ui.dir_labels)
        self.__initializer.auto_load_current_key()


    @property
    def current_km(self) -> SingleKeyManager | None:
        return self.__initializer.current_km
