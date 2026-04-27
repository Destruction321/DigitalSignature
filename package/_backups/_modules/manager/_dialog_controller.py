# package/_backups/_modules/manager/_dialog_controller.py
"""备份管理对话框控制器"""
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from typing import Any, Callable, TYPE_CHECKING

from .._verifier import Verifier
from ... import _backup_utils
from ...._utils import format_size

if TYPE_CHECKING:
    from ._dialog_protocol import DialogProtocol


class Controller:
    """备份管理对话框控制器。"""
    def __init__(self, dialog_protocol: DialogProtocol, parent: tk.Widget) -> None:
        self.__dialog_protocol: DialogProtocol = dialog_protocol
        self.__verifier: Verifier = Verifier(parent)
        self.__backup_items: list[dict] = []


    """public methods"""
    def refresh_list(self, click_btn: bool = False) -> None:
        """刷新备份列表并更新所有统计信息"""
        result = _backup_utils.list_backups_with_integrity()
        if not result.is_success():
            messagebox.showerror("刷新备份", result.msg)
            return

        backups: list[dict] = result.data
        self.__backup_items = backups

        self.__dialog_protocol.populate_list(backups)
        self.__dialog_protocol.set_info_text(self.__build_info_text(backups))

        if backups:
            status_text, color = self.__build_integrity_status(backups)
            self.__dialog_protocol.set_integrity_status(status_text, color)

        self.__dialog_protocol.select_tab(0)

        if click_btn:
            messagebox.showinfo("成功", "刷新成功")

    def delete_selected_backup(self, update_status_callback: Callable[[str], None]) -> None:
        """删除选中的备份"""
        index = self.__dialog_protocol.get_selected_index()
        if index is None:
            messagebox.showwarning("选择备份", "请先选择一个要删除的备份")
            return

        selected_backup: dict = self.__backup_items[index]
        confirm_msg = (
            f"确定要删除备份吗？\n\n"
            f"备份名称: {selected_backup['name']}\n"
            f"创建时间: {selected_backup['created_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"备份大小: {format_size(selected_backup['size'])}\n\n"
            f"此操作不可逆，删除后无法恢复！"
        )
        if not messagebox.askyesno("确认删除", confirm_msg):
            return

        try:
            delete_result = _backup_utils.delete_backup(selected_backup["name"])
            if delete_result.is_success():
                update_status_callback(f"备份删除成功: {selected_backup['name']}")
                messagebox.showinfo("删除成功", f"备份删除成功！\n\n{delete_result.msg}")
                self.refresh_list()
            else:
                messagebox.showerror("删除失败", f"备份删除失败：\n{delete_result.msg}")
        except Exception as e:
            messagebox.showerror("删除失败", f"删除备份过程中出现错误：\n{str(e)}")

    def show_selected_details(self) -> None:
        """显示选中备份的详情"""
        index = self.__dialog_protocol.get_selected_index()
        if index is None:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return

        selected_backup: dict = self.__backup_items[index]
        details = self.__build_details_text(selected_backup)
        self.__dialog_protocol.show_details(details)
        self.__dialog_protocol.select_tab(1)

    def verify_selected_backup(self) -> None:
        """验证选中的备份"""
        index = self.__dialog_protocol.get_selected_index()
        if index is None:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return

        selected_backup: dict = self.__backup_items[index]
        self.__verifier.verify_single_backup(selected_backup, self.__on_single_verify_done)

    def verify_all_backups(self) -> None:
        """验证所有备份"""
        if not self.__backup_items:
            messagebox.showinfo("验证备份", "没有找到备份文件")
            return

        self.__verifier.verify_all_backups(self.__backup_items, self.__on_all_verify_done)


    """private methods"""
    def __on_single_verify_done(self, backup: dict[str, Any]) -> None:
        """单个备份验证完成后的回调：刷新列表，并同步更新详情区"""
        self.refresh_list()

        index = self.__dialog_protocol.get_selected_index()
        if index is None:
            return

        current = self.__backup_items[index]
        if current.get("path") == backup.get("path"):
            details = self.__build_details_text(current)
            self.__dialog_protocol.show_details(details)

    def __on_all_verify_done(self, backup_items: list[dict[str, Any]]) -> None:
        """批量验证完成后的回调：用新数据更新列表"""
        self.__backup_items = backup_items
        self.refresh_list()


    @staticmethod
    def __build_info_text(backups: list[dict]) -> str:
        valid_backups = [b for b in backups if b.get("integrity_valid", False)]
        total_size = format_size(sum(b["size"] for b in backups))
        return (
            f"共找到 {len(backups)} 个备份文件，"
            f"{len(valid_backups)} 个已验证完整，"
            f"总大小: {total_size}"
        )

    @staticmethod
    def __build_integrity_status(backups: list[dict]) -> tuple[str, str]:
        """返回 (状态文字, 颜色字符串)"""
        valid = [b for b in backups if b.get("integrity_valid", False)]
        ratio = len(valid) / len(backups) * 100
        if ratio == 100:
            return "所有备份均完整", "green"
        elif ratio >= 50:
            return f"部分备份完整 ({len(valid)}/{len(backups)})", "orange"
        else:
            return f"多数备份不完整 ({len(valid)}/{len(backups)})", "red"

    @staticmethod
    def __build_details_text(backup: dict) -> str:
        """构建备份详情的纯文本内容"""
        back_up_path = Path(backup["path"])
        details = (
            f"备份名称: {backup['name']}\n"
            f"完整路径: {backup['path']}\n"
            f"创建时间: {backup['created_time'].strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"备份大小: {format_size(backup['size'])}\n"
            f"目录存在: {'是' if back_up_path.exists() else '否'}\n"
        )

        if "integrity_valid" in backup:
            if backup["integrity_valid"]:
                details += "完整性状态: ✓ 已验证通过\n"
            else:
                details += "完整性状态: ⚠ 验证失败\n"
            if "integrity_message" in backup:
                details += f"验证消息: {backup['integrity_message']}\n"

        if backup.get("checksum_data"):
            checksum = backup["checksum_data"]
            details += (
                f"\n校验和信息:\n"
                f"  备份类型: {checksum.get('backup_type', '未知')}\n"
                f"  文件数量: {checksum.get('file_count', 0)}\n"
                f"  总大小: {format_size(checksum.get('total_size', 0))}\n"
                f"  创建时间: {checksum.get('created_time', '未知')}\n"
                f"  校验和: {checksum.get('checksum', '无')[:16]}...\n"
            )

        details += "\n目录结构:\n--------\n"
        if back_up_path.exists():
            try:
                details += _get_directory_structure(back_up_path, max_depth=2)
            except Exception as e:
                details += f"无法读取目录结构: {str(e)}\n"
        else:
            details += "目录不存在\n"

        return details
    

def _get_directory_structure(path: Path, max_depth: int = 2, current_depth: int = 0) -> str:
    """获取目录结构，仅在包含子目录的目录后添加斜杠"""
    if current_depth >= max_depth:
        return ""

    structure: str = ""
    try:
        items: list[str] = [item.name for item in path.iterdir()]
        items.sort()

        for i, item in enumerate(items):
            item_path: Path = path / item
            prefix: str = "    " * current_depth

            # 检查是否为目录
            if not item_path.is_dir():
                # 文件项
                structure += f"{prefix}{item}\n"
                continue

            # 尝试读取子目录内容，检查是否有子项
            try:
                sub_items: list[str] = [item.name for item in item_path.iterdir()]
                has_subitems = len(sub_items) > 0
            except (PermissionError, Exception):
                has_subitems = False

            # 显示当前目录
            structure += f"{prefix}{item}/"  # 目录后加斜杠

            # 如果有子项且未达到最大深度，递归处理
            if has_subitems and current_depth + 1 < max_depth:
                structure += "\n"
                structure += _get_directory_structure(
                    item_path, max_depth, current_depth + 1
                )
            else:
                structure += "\n"

    except PermissionError:
        prefix = "    " * current_depth
        structure += f"{prefix}【权限不足】\n"
    except Exception as e:
        prefix = "    " * current_depth
        structure += f"{prefix}【错误：{e}】\n"

    return structure
 