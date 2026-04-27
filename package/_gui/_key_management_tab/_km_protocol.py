# package/_gui/_key_management_tab/_km_protocol.py
"""密钥管理标签页协议"""
from typing import Protocol


class KeyManagerProtocol(Protocol):
    """密钥管理标签页协议"""
    def populate_key_list(self, items: list[tuple[str, str]]) -> None:
        """
        填充密钥列表
        
        Args:
            items (list[tuple[str, str]]): 要显示的密钥项列表，每项为 (key_id, display_text) 的元组
        """
        ...

    def get_selected_display_text(self) -> str | None:
        """
        返回当前选中项的显示文字

        Returns:
            str | None: 选中项的显示文字或 None
        """
        ...

    def set_key_status(self, text: str, color: str) -> None:
        """
        更新密钥状态标签

        Args:
            text (str): 要显示的密钥状态文本
            color (str): 要使用的颜色
        """
        ...

    def set_security_status(self, text: str, color: str) -> None:
        """
        更新配置安全状态标签

        Args:
            text (str): 要显示的安全状态文本
            color (str): 要使用的颜色
        """
        ...