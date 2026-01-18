# package/_gui/key_management_tab/__init__.py
"""密钥管理标签页"""
import tkinter as tk
from typing import TYPE_CHECKING

from .ui_creator import UICreator

if TYPE_CHECKING:
    from ..._core.keys.loader import KeyLoader
    from ..._core.keys.managers import MultiKeyManager


class KeyManagementTab:
    """密钥管理标签页"""
    def __init__(self, parent: tk.Widget, multi_key_manager: MultiKeyManager, key_loader: KeyLoader) -> None:
        self.__ui: UICreator = UICreator(parent, multi_key_manager, key_loader)
        
        self.__ui.setup_ui()
        
        self.__ui.controller.update_security_status(self.__ui.multi_km.config_secure)
        
        
    @property
    def loaded_key_id(self) -> str | None:
        return self.__ui.controller.loaded_key_id

    @loaded_key_id.setter
    def loaded_key_id(self, key_id: str | None) -> None:
        self.__ui.controller.loaded_key_id = key_id
    
    
    def refresh_key_list(self) -> None:
        """刷新密钥列表"""
        self.__ui.controller.refresh_key_list()
        
    def update_key_status(self) -> None:
        """更新密钥状态显示"""
        self.__ui.controller.update_key_status()
