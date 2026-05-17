# package/_app/_app.py
"""数字签名系统主模块"""
from typing import TYPE_CHECKING

from . import _initializer

if TYPE_CHECKING:
    from tkinter import Tk
    from .._core.keys.managers import SingleKeyManager


class APP:
    """数字签名系统主模块"""
    def __init__(self, root: Tk) -> None:
        # 创建初始化器
        self.__initializer: _initializer.Initializer = _initializer.Initializer(root)
        
        # 创建UI
        self.__initializer.ui_setter.setup_main_window()
        self.__initializer.ui_setter.setup_ui()
        
        # 数据处理
        _initializer.migrate_existing_files()
        self.__initializer.auto_load_current_key()


    @property
    def current_km(self) -> SingleKeyManager | None:
        return self.__initializer.current_km
