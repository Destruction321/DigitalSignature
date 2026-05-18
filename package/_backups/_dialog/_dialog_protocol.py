# package/_backups/_dialog/_dialog_protocol.py
"""备份对话框协议"""
from typing import Protocol, TYPE_CHECKING

if TYPE_CHECKING:
    from .._backup_list_type import BackupList


class DialogProtocol(Protocol):
    """备份对话框协议"""
    def set_info_text(self, text: str) -> None:
        """
        更新顶部统计信息文字
        
        Args:
            text (str): 要显示的统计信息文本
        """
        ...

    def set_integrity_status(self, text: str, color: str) -> None:
        """
        更新完整性状态标签

        Args:
            text (str): 要显示的完整性状态文本
            color (str): 要使用的颜色
        """
        ...

    def populate_list(self, items: BackupList) -> None:
        """填充备份列表"""
        ...

    def get_selected_index(self) -> int | None:
        """
        返回当前选中项的下标，无选中时返回 None

        Returns:
            int | None: 选中项的下标或 None
        """
        ...

    def show_details(self, text: str) -> None:
        """
        在详情区显示文字内容

        Args:
            text (str): 要显示的详情内容
        """
        ...

    def select_tab(self, index: int) -> None:
        """
        切换到指定 Notebook 标签页

        Args:
            index (int): 要切换到的标签页下标
        """
        ...
