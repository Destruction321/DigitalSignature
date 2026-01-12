# package/_utils/backup/backup_manager.py
"""备份管理器"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable, cast

from . import backup_utils
from ._backup_verifier import BackupVerifier
from ...utils import format_size


class BackupManager:
    """备份管理器"""
    def __init__(self, parent: tk.Widget,
                 update_status_callback: Callable[[str], None]) -> None:
        self.__parent: tk.Widget = parent
        self.__update_status: Callable[[str], None] = update_status_callback

        # 创建验证器实例
        self.__verifier = BackupVerifier(parent)

        # UI控件
        self.__dialog: tk.Toplevel | None = None
        self.__listbox: tk.Listbox | None = None
        self.__backup_items: list[dict] = []
        self.__info_label: ttk.Label | None = None
        self.__details_text: ScrolledText | None = None
        self.__notebook: ttk.Notebook | None = None
        self.__integrity_label: ttk.Label | None = None


    """public methods"""
    def show(self) -> None:
        """显示统一备份管理对话框"""
        backups = backup_utils.list_backups_with_integrity()

        self.__dialog = tk.Toplevel(self.__parent)
        self.__dialog.title("备份管理")
        self.__dialog.geometry("850x650")

        try:
            parent_top_level = self.__parent.winfo_toplevel()
            self.__dialog.transient(parent_top_level)
        except tk.TclError:
            self.__dialog.transient()

        self.__dialog.grab_set()
        self.__center_dialog(self.__dialog)
        self.__create_ui(backups)
        #self.__bind_events()


    """private methods"""
    def __center_dialog(self, dialog: tk.Toplevel) -> None:
        """居中显示对话框"""
        dialog.update_idletasks()
        x = (self.__parent.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (self.__parent.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

    def __create_ui(self, backups: list[dict]) -> None:
        """创建UI界面"""
        main_frame: ttk.Frame = ttk.Frame(self.__dialog, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建头部信息
        self.__create_header(main_frame, backups)

        # 创建笔记本控件
        self.__create_notebook(main_frame)

        # 创建按钮区域
        self.__create_button_area(main_frame)

    def __create_header(self, parent: ttk.Frame, backups: list[dict]) -> None:
        """创建头部信息"""
        header_frame: ttk.Frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 10))

        title_label: ttk.Label = ttk.Label(header_frame, text="备份文件管理", font=("微软雅黑", 12, "bold"))
        title_label.pack(anchor=tk.W)

        # 计算完整备份数量
        valid_backups = [b for b in backups if b.get("integrity_valid", False)]
        total_size = format_size(sum(backup["size"] for backup in backups))

        self.__info_label = ttk.Label(
            header_frame,
            text=f"共找到 {len(backups)} 个备份文件，{len(valid_backups)} 个已验证完整，总大小: {total_size}",
            font=("微软雅黑", 9)
        )
        self.__info_label.pack(anchor=tk.W, pady=(5, 0))

        # 完整性状态标签
        if backups:
            integrity_ratio = len(valid_backups) / len(backups) * 100
            self.__create_integrity_label(header_frame, integrity_ratio, len(valid_backups), len(backups))

    def __create_integrity_label(self, parent: ttk.Frame, ratio: float, valid_count: int, total_count: int) -> None:
        """创建完整性状态标签"""
        if ratio == 100:
            color = "green"
            status_text = "所有备份均完整"
        elif ratio >= 50:
            color = "orange"
            status_text = f"部分备份完整 ({valid_count}/{total_count})"
        else:
            color = "red"
            status_text = f"多数备份不完整 ({valid_count}/{total_count})"

        self.__integrity_label = ttk.Label(
            parent,
            text=f"完整性状态：{status_text}",
            font=("微软雅黑", 9, "bold"),
            foreground=color
        )
        self.__integrity_label.pack(anchor=tk.W, pady=(2, 0))

    def __create_notebook(self, parent: ttk.Frame) -> None:
        """创建笔记本控件"""
        self.__notebook = ttk.Notebook(parent)
        self.__notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # 创建各个标签页
        self.__create_list_tab()
        self.__create_details_tab()
        self.__create_verify_tab()

    def __create_list_tab(self) -> None:
        """创建列表标签页"""
        list_tab = ttk.Frame(self.__notebook, padding="10")
        cast(ttk.Notebook, self.__notebook).add(list_tab, text="备份列表")

        list_frame: ttk.LabelFrame = ttk.LabelFrame(list_tab, text="备份文件列表", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)

        list_container: ttk.Frame = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.__listbox = tk.Listbox(list_container, height=15, font=("Consolas", 9), selectmode=tk.SINGLE)
        scrollbar: ttk.Scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.__listbox.yview)
        self.__listbox.configure(yscrollcommand=scrollbar.set)

        self.__listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.__refresh_list()

    def __create_details_tab(self) -> None:
        """创建详细信息标签页"""
        details_tab = ttk.Frame(self.__notebook, padding="10")
        cast(ttk.Notebook, self.__notebook).add(details_tab, text="备份详情")

        details_frame: ttk.LabelFrame = ttk.LabelFrame(details_tab, text="备份详细信息", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True)

        self.__details_text = ScrolledText(
            details_frame, wrap=tk.WORD, font=("Consolas", 10), height=15, state=tk.DISABLED
        )
        self.__details_text.pack(fill=tk.BOTH, expand=True)

    def __create_verify_tab(self) -> None:
        """创建验证标签页"""
        verify_tab = ttk.Frame(self.__notebook, padding="10")
        cast(ttk.Notebook, self.__notebook).add(verify_tab, text="完整性验证")

        verify_frame: ttk.LabelFrame = ttk.LabelFrame(verify_tab, text="备份完整性验证", padding="10")
        verify_frame.pack(fill=tk.BOTH, expand=True)

        # 验证说明
        explanation = ttk.Label(
            verify_frame,
            text="完整性验证说明：",
            font=("微软雅黑", 10, "bold")
        )
        explanation.pack(anchor=tk.W, pady=(0, 10))

        explanation_text = (
            "系统使用SHA-256哈希算法验证备份的完整性。验证包括：\n\n"
            "1. 文件完整性：计算所有文件的哈希值，确保文件未被篡改\n"
            "2. 文件数量：验证备份中的文件数量是否与创建时一致\n"
            "3. 文件大小：验证每个文件的大小是否与创建时一致\n\n"
            "验证结果：\n"
            "• ✓ 表示备份完整且有效\n"
            "• ⚠ 表示备份可能损坏或缺少验证信息\n"
            "• 无标记表示旧格式备份（无验证信息）"
        )

        explanation_label = ttk.Label(
            verify_frame,
            text=explanation_text,
            font=("微软雅黑", 9),
            justify=tk.LEFT,
            wraplength=700
        )
        explanation_label.pack(anchor=tk.W, pady=(0, 20))

        # 验证按钮区域
        verify_btn_frame = ttk.Frame(verify_frame)
        verify_btn_frame.pack(fill=tk.X, pady=10)

        ttk.Button(
            verify_btn_frame,
            text="验证所有备份",
            command=self.__verify_all_backups
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            verify_btn_frame,
            text="手动验证选中备份",
            command=self.__verify_selected_backup
        ).pack(side=tk.LEFT, padx=5)

    def __create_button_area(self, parent: ttk.Frame) -> None:
        """创建按钮区域"""
        button_frame: ttk.Frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)

        left_frame: ttk.Frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)

        ttk.Button(left_frame, text="刷新列表", command=self.__refresh_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_frame, text="删除选中备份", command=self.__delete_selected_backup).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_frame, text="查看详情", command=self.__show_selected_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(left_frame, text="验证完整性", command=self.__verify_selected_backup).pack(side=tk.LEFT, padx=5)

        right_frame: ttk.Frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)

        ttk.Button(right_frame, text="关闭", command=cast(tk.Toplevel, self.__dialog).destroy).pack(side=tk.RIGHT, padx=5)

    def __bind_events(self) -> None:
        """绑定事件"""
        self.__listbox = cast(tk.Listbox, self.__listbox)
        self.__listbox.bind("<<ListboxSelect>>", self.__on_backup_selected)
        self.__listbox.bind("<Double-Button-1>", lambda event: self.__delete_selected_backup())

    def __populate_list(self, backups: list[dict]) -> None:
        """填充备份列表"""
        self.__listbox = cast(tk.Listbox, self.__listbox)
        self.__listbox.delete(0, tk.END)
        self.__backup_items = []

        if not backups:
            self.__listbox.insert(tk.END, "没有找到备份文件")
            return

        for backup in backups:
            time_str: str = backup["created_time"].strftime("%Y-%m-%d %H:%M")
            size_str: str = format_size(backup["size"])

            # 使用显示名称（已包含完整性标记）
            display_name = backup.get("display_name", backup["name"])
            display_text: str = f"{display_name:40} | {time_str} | {size_str:>12}"

            self.__listbox.insert(tk.END, display_text)
            self.__backup_items.append(backup)

            # 根据完整性状态设置颜色
            index = self.__listbox.size() - 1
            if backup.get("integrity_valid", False):
                self.__listbox.itemconfig(index, {"fg": "green"})
            else:
                self.__listbox.itemconfig(index, {"fg": "orange"})

    def __on_backup_selected(self, _event: tk.Event | None = None) -> None:
        """当备份被选中时显示详情"""
        selection: tuple[int] = cast(tk.Listbox, self.__listbox).curselection()
        if selection:
            selected_index: int = selection[0]
            selected_backup: dict = self.__backup_items[selected_index]
            self.__show_backup_details(selected_backup)

    def __show_backup_details(self, backup: dict) -> None:
        """显示备份详细信息"""
        if self.__details_text is None:
            return

        self.__details_text.config(state=tk.NORMAL)
        self.__details_text.delete("1.0", tk.END)

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
                dir_structure: str = self.__get_directory_structure(back_up_path, max_depth=2)
                details += dir_structure
            except Exception as e:
                details += f"无法读取目录结构: {str(e)}\n"
        else:
            details += "目录不存在\n"

        self.__details_text.insert("1.0", details)
        self.__details_text.config(state=tk.DISABLED)
        cast(ttk.Notebook, self.__notebook).select(1)

    def __refresh_list(self) -> None:
        """刷新备份列表"""
        backups = backup_utils.list_backups_with_integrity()
        self.__populate_list(backups)

        # 更新统计信息
        valid_backups = [b for b in backups if b.get("integrity_valid", False)]
        total_size = format_size(sum(backup["size"] for backup in backups))

        cast(tk.Label, self.__info_label).config(
            text=f"共找到 {len(backups)} 个备份文件，{len(valid_backups)} 个已验证完整，总大小: {total_size}"
        )

        # 更新完整性状态标签
        if backups and self.__integrity_label:
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

            cast(tk.Label, self.__integrity_label).config(text=f"完整性状态：{status_text}", foreground=color)

        cast(ttk.Notebook, self.__notebook).select(0)

    def __delete_selected_backup(self) -> None:
        """删除选中的备份"""
        selection = cast(tk.Listbox, self.__listbox).curselection()
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
            delete_result = backup_utils.delete_backup(selected_backup["name"])
            if delete_result.is_success():
                self.__update_status(f"备份删除成功: {selected_backup["name"]}")
                messagebox.showinfo("删除成功", f"备份删除成功！\n\n{delete_result.msg}")
                self.__refresh_list()
            else:
                messagebox.showerror("删除失败", f"备份删除失败：\n{delete_result.msg}")
                
        except Exception as e:
            messagebox.showerror("删除失败", f"删除备份过程中出现错误：\n{str(e)}")

    def __show_selected_details(self) -> None:
        """显示选中备份的详情"""
        selection: tuple[int] = cast(tk.Listbox, self.__listbox).curselection()
        if not selection:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return

        selected_index: int = selection[0]
        selected_backup: dict = self.__backup_items[selected_index]
        self.__show_backup_details(selected_backup)

    def __verify_selected_backup(self) -> None:
        """验证选中的备份"""
        selection: tuple[int] = cast(tk.Listbox, self.__listbox).curselection()
        if not selection:
            messagebox.showwarning("选择备份", "请先选择一个备份")
            return

        selected_index: int = selection[0]
        selected_backup: dict = self.__backup_items[selected_index]

        # 使用验证器进行验证
        self.__verifier.verify_single_backup(selected_backup, self.__update_backup_info)

    def __verify_all_backups(self) -> None:
        """验证所有备份"""
        if self.__backup_items is None:
            messagebox.showinfo("验证备份", "没有找到备份文件")
            return

        # 使用验证器进行批量验证
        self.__verifier.verify_all_backups(self.__backup_items, self.__update_backup_list)

    def __update_backup_info(self, backup: dict[str, Any]) -> None:
        """更新单个备份信息后的回调"""
        # 刷新列表显示更新后的信息
        self.__refresh_list()

        # 如果当前选中了这个备份，更新详情显示
        selection = cast(tk.Listbox, self.__listbox).curselection()
        if not selection:
            return

        selected_index = selection[0]
        selected_backup = self.__backup_items[selected_index]
        if selected_backup.get("path") == backup.get("path"):
            self.__show_backup_details(selected_backup)

    def __update_backup_list(self, backup_items: list[dict[str, Any]]) -> None:
        """更新备份列表后的回调"""
        # 更新备份列表并刷新显示
        self.__backup_items = backup_items
        self.__refresh_list()

    @staticmethod
    def __get_directory_structure(path: Path, max_depth: int = 2, current_depth: int = 0) -> str:
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
                    structure += BackupManager.__get_directory_structure(
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
