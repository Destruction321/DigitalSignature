# package/_backups/_modules/manager/_dialog_controller.py
"""备份管理对话框控制器"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Any, cast, Callable, TYPE_CHECKING

from .._verifier import BackupVerifier
from ... import _backup_utils
from ...._utils import format_size

if TYPE_CHECKING:
    from ._dialog_creator import Initializer


class Controller:
    """对话框控制器"""
    def __init__(self, initializer: Initializer, parent: tk.Widget) -> None:
        self.__initializer = initializer  # 访问对话框UI控件
        self.__verifier = BackupVerifier(parent)
        self.__backup_items: list[dict] = []
        
    
    """public methods -- bind to buttons"""
    def refresh_list(self, click_btn: bool = False) -> None:
        """刷新备份列表"""
        backups = _backup_utils.list_backups_with_integrity()
        self.__populate_list(backups)

        # 更新统计信息
        valid_backups = [b for b in backups if b.get("integrity_valid", False)]
        total_size = format_size(sum(backup["size"] for backup in backups))

        cast(tk.Label, self.__initializer.info_label).config(
            text=f"共找到 {len(backups)} 个备份文件，{len(valid_backups)} 个已验证完整，总大小: {total_size}"
        )

        # 更新完整性状态标签
        if backups and self.__initializer.integrity_label:
            integrity_ratio = len(valid_backups) / len(backups) * 100
            if integrity_ratio == 100:
                color = "green"
                status_text = "所有备份均完整"
            elif integrity_ratio >= 50:
                color = "orange"
                status_text = f"部分备份完整 ({len(valid_backups)}/{len(backups)})"
            else:
                color = "red"
                status_text = f"多数备份不完整 ({len(valid_backups)}/{len(backups)})"

            cast(tk.Label, self.__initializer.integrity_label).config(text=f"完整性状态：{status_text}", foreground=color)

        cast(ttk.Notebook, self.__initializer.notebook).select(0)
        
        if click_btn:
            messagebox.showinfo("成功", "刷新成功")

    def delete_selected_backup(self, update_status_callback: Callable[[str], None]) -> None:
        """
        删除选中的备份
        
        Args:
            update_status_callback (Callable[[str], None]): 状态更新回调函数
        """
        selection = cast(tk.Listbox, self.__initializer.listbox).curselection()
        if not selection:
            messagebox.showwarning("选择备份", "请先选择一个要删除的备份")
            return
        
        selected_backup: dict = self.__backup_items[int(selection[0])]
        confirm_msg = (
            f"确定要删除备份吗？\n\n"
            f"备份名称: {selected_backup["name"]}\n"
            f"创建时间: {selected_backup["created_time"].strftime("%Y-%m-%d %H:%M:%S")}\n"
            f"备份大小: {format_size(selected_backup["size"])}\n\n"
            f"此操作不可逆，删除后无法恢复！"
        )
        if not messagebox.askyesno("确认删除", confirm_msg):
            return
        
        try:
            delete_result = _backup_utils.delete_backup(selected_backup["name"])
            if delete_result.is_success():
                update_status_callback(f"备份删除成功: {selected_backup["name"]}")
                messagebox.showinfo("删除成功", f"备份删除成功！\n\n{delete_result.msg}")
                self.refresh_list()
            else:
                messagebox.showerror("删除失败", f"备份删除失败：\n{delete_result.msg}")
                
        except Exception as e:
            messagebox.showerror("删除失败", f"删除备份过程中出现错误：\n{str(e)}")

    def show_selected_details(self) -> None:
        """显示选中备份的详情"""
        selection: tuple[int] = cast(tk.Listbox, self.__initializer.listbox).curselection()
        if not selection:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return

        selected_index: int = selection[0]
        selected_backup: dict = self.__backup_items[selected_index]
        self.__show_backup_details(selected_backup)

    def verify_selected_backup(self) -> None:
        """验证选中的备份"""
        selection: tuple[int] = cast(tk.Listbox, self.__initializer.listbox).curselection()
        if not selection:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return

        selected_index: int = selection[0]
        selected_backup: dict = self.__backup_items[selected_index]

        # 使用验证器进行验证
        self.__verifier.verify_single_backup(selected_backup, self.__update_backup_info)

    def verify_all_backups(self) -> None:
        """验证所有备份"""
        if self.__backup_items is None:
            messagebox.showinfo("验证备份", "没有找到备份文件")
            return

        # 使用验证器进行批量验证
        self.__verifier.verify_all_backups(self.__backup_items, self.__update_backup_list)


    """private methods"""
    def __update_backup_info(self, backup: dict[str, Any]) -> None:
        """更新单个备份信息后的回调"""
        # 刷新列表显示更新后的信息
        self.refresh_list()

        # 如果当前选中了这个备份，更新详情显示
        selection = cast(tk.Listbox, self.__initializer.listbox).curselection()
        if not selection:
            return

        selected_index = selection[0]
        selected_backup = self.__backup_items[selected_index]
        if selected_backup.get("path") == backup.get("path"):
            self.__show_backup_details(selected_backup)

    def __populate_list(self, backups: list[dict]) -> None:
        """填充备份列表"""
        listbox = cast(tk.Listbox, self.__initializer.listbox)
        listbox.delete(0, tk.END)
        self.__backup_items = []

        if not backups:
            listbox.insert(tk.END, "没有找到备份文件")
            self.__initializer.listbox = listbox
            return

        for backup in backups:
            time_str: str = backup["created_time"].strftime("%Y-%m-%d %H:%M")
            size_str: str = format_size(backup["size"])

            # 使用显示名称（已包含完整性标记）
            display_name = backup.get("display_name", backup["name"])
            display_text: str = f"{display_name:40} | {time_str} | {size_str:>12}"

            listbox.insert(tk.END, display_text)
            self.__backup_items.append(backup)

            # 根据完整性状态设置颜色
            index = listbox.size() - 1
            if backup.get("integrity_valid", False):
                listbox.itemconfig(index, {"fg": "green"})
            else:
                listbox.itemconfig(index, {"fg": "orange"})
                
        self.__initializer.listbox = listbox

    def __show_backup_details(self, backup: dict) -> None:
        """显示备份详细信息"""
        if self.__initializer.details_text is None:
            return

        self.__initializer.details_text.config(state=tk.NORMAL)
        self.__initializer.details_text.delete("1.0", tk.END)

        # 基本信息
        back_up_path = Path(backup["path"])
        details: str = (
            f"备份名称: {backup["name"]}\n"
            f"完整路径: {backup["path"]}\n"
            f"创建时间: {backup["created_time"].strftime("%Y-%m-%d %H:%M:%S")}\n"
            f"备份大小: {format_size(backup["size"])}\n"
            f"目录存在: {"是" if back_up_path.exists() else "否"}\n"
        )

        # 显示完整性验证信息（如果存在）
        if "integrity_valid" in backup:
            if backup["integrity_valid"]:
                details += f"完整性状态: ✓ 已验证通过\n"
            else:
                details += f"完整性状态: ⚠ 验证失败\n"

            if "integrity_message" in backup:
                details += f"验证消息: {backup["integrity_message"]}\n"

        # 显示校验和数据（如果存在）
        if "checksum_data" in backup and backup["checksum_data"]:
            checksum = backup["checksum_data"]
            details += f"\n校验和信息:\n"
            details += f"  备份类型: {checksum.get("backup_type", "未知")}\n"
            details += f"  文件数量: {checksum.get("file_count", 0)}\n"
            details += f"  总大小: {format_size(checksum.get("total_size", 0))}\n"
            details += f"  创建时间: {checksum.get("created_time", "未知")}\n"
            details += f"  校验和: {checksum.get("checksum", "无")[:16]}...\n"

        details += "\n目录结构:\n"
        details += "--------\n"

        if back_up_path.exists():
            try:
                dir_structure: str = _get_directory_structure(back_up_path, max_depth=2)
                details += dir_structure
            except Exception as e:
                details += f"无法读取目录结构: {str(e)}\n"
        else:
            details += "目录不存在\n"

        self.__initializer.details_text.insert("1.0", details)
        self.__initializer.details_text.config(state=tk.DISABLED)
        cast(ttk.Notebook, self.__initializer.notebook).select(1)

    def __update_backup_list(self, backup_items: list[dict[str, Any]]) -> None:
        """更新备份列表后的回调"""
        # 更新备份列表并刷新显示
        self.__backup_items = backup_items
        self.refresh_list()


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
