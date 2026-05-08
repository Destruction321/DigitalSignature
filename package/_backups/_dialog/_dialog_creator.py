# package/_backups/_dialog/_dialog_creator.py
"""备份管理对话框创建"""
import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
from typing import Any, Callable

from ._dialog_controller import Controller
from ..._utils.tools import format_size


def center_dialog(parent: tk.Widget, dialog: tk.Toplevel) -> None:
    """
    居中显示对话框
    
    Args:
        parent (tk.Widget): 父窗口
        dialog (tk.Toplevel): 对话框对象
    """
    dialog.update_idletasks()
    x = (parent.winfo_screenwidth() - dialog.winfo_width()) // 2
    y = (parent.winfo_screenheight() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")

def create_ui(parent: tk.Widget, backups: list[dict[str, Any]], dialog: tk.Toplevel) -> None:
    """
    创建UI界面
    
    Args:
        parent (tk.Widget): 父窗口
        backups (list[dict[str, Any]]): 备份列表
        dialog (tk.Toplevel): 对话框对象
        update_status_callback (Callable[[str], None]): 状态更新回调函数
    """
    main_frame: ttk.Frame = ttk.Frame(dialog, padding="15")
    main_frame.pack(fill=tk.BOTH, expand=True)

    initializer = Initializer(parent)

    initializer.create_header(main_frame, backups)
    initializer.create_notebook(main_frame)
    initializer.create_button_area(main_frame, dialog)


class Initializer:
    """对话框创建器"""
    def __init__(self, parent: tk.Widget) -> None:
        self.__listbox: tk.Listbox | None = None
        self.__info_label: ttk.Label | None = None
        self.__details_text: ScrolledText | None = None
        self.__notebook: ttk.Notebook | None = None
        self.__integrity_label: ttk.Label | None = None
        
        # 创建控制器
        self.__controller: Controller = Controller(self, parent)


    """DialogProtocol协议实现"""
    def set_info_text(self, text: str) -> None:
        assert self.__info_label is not None, "信息标签未初始化"
        self.__info_label.config(text=text)

    def set_integrity_status(self, text: str, color: str) -> None:
        assert self.__integrity_label is not None, "完整性标签未初始化"
        self.__integrity_label.config(text=f"完整性状态：{text}", foreground=color)

    def populate_list(self, items: list[dict]) -> None:
        assert self.__listbox is not None, "列表框未初始化"

        self.__listbox.delete(0, tk.END)

        if not items:
            self.__listbox.insert(tk.END, "没有找到备份文件")
            return

        for backup in items:
            time_str = backup["created_time"].strftime("%Y-%m-%d %H:%M")
            size_str = format_size(backup["size"])
            display_name = backup.get("display_name", backup["name"])
            display_text = f"{display_name:40} | {time_str} | {size_str:>12}"

            self.__listbox.insert(tk.END, display_text)

            index = self.__listbox.size() - 1
            color = "green" if backup.get("integrity_valid", False) else "orange"
            self.__listbox.itemconfig(index, {"fg": color})

    def get_selected_index(self) -> int | None:
        assert self.__listbox is not None, "列表框未初始化"
        
        selection = self.__listbox.curselection()
        return int(selection[0]) if selection else None

    def show_details(self, text: str) -> None:
        assert self.__details_text is not None, "详情文本框未初始化"
        
        self.__details_text.config(state=tk.NORMAL)
        self.__details_text.delete("1.0", tk.END)
        self.__details_text.insert("1.0", text)
        self.__details_text.config(state=tk.DISABLED)

    def select_tab(self, index: int) -> None:
        assert self.__notebook is not None, "笔记本控件未初始化"
        self.__notebook.select(index)


    """public methods"""
    def create_header(self, parent: ttk.Frame, backups: list[dict]) -> None:
        """
        创建头部信息
        
        Args:
            parent (tk.Widget): 父窗口
            backups (list[dict[str, Any]]): 备份列表
        """
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


    def create_notebook(self, parent: ttk.Frame) -> None:
        """
        创建笔记本控件
        
        Args:
            parent (tk.Widget): 父窗口
        """
        self.__notebook = ttk.Notebook(parent)
        self.__notebook.pack(fill=tk.BOTH, expand=True, pady=10)

        # 创建各个标签页
        self.__create_list_tab()
        self.__create_details_tab()
        self.__create_verify_tab()

    def create_button_area(self, parent: ttk.Frame, dialog: tk.Toplevel) -> None:
        """
        创建按钮区域
        
        Args:
            parent (tk.Widget): 父窗口
            dialog (tk.Toplevel): 对话框对象
            update_status_callback (Callable[[str], None]): 状态更新回调函数
        """
        button_frame: ttk.Frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=10)

        left_frame: ttk.Frame = ttk.Frame(button_frame)
        left_frame.pack(side=tk.LEFT)

        ttk.Button(
            left_frame,
            text="刷新列表",
            command=lambda: self.__controller.refresh_list(click_btn=True)
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            left_frame,
            text="删除选中备份",
            command=self.__controller.delete_selected_backup
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            left_frame,
            text="查看详情",
            command=self.__controller.show_selected_details
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            left_frame,
            text="验证完整性",
            command=self.__controller.verify_selected_backup
        ).pack(side=tk.LEFT, padx=5)

        right_frame: ttk.Frame = ttk.Frame(button_frame)
        right_frame.pack(side=tk.RIGHT)

        ttk.Button(right_frame, text="关闭", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

    
    """private methods"""
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

    def __create_list_tab(self) -> None:
        """创建列表标签页"""
        assert self.__notebook is not None, "笔记本控件未创建"
        
        list_tab = ttk.Frame(self.__notebook, padding="10")
        self.__notebook.add(list_tab, text="备份列表")

        list_frame: ttk.LabelFrame = ttk.LabelFrame(list_tab, text="备份文件列表", padding="10")
        list_frame.pack(fill=tk.BOTH, expand=True)

        list_container: ttk.Frame = ttk.Frame(list_frame)
        list_container.pack(fill=tk.BOTH, expand=True)

        self.__listbox = tk.Listbox(list_container, height=15, font=("Consolas", 9), selectmode=tk.SINGLE)
        scrollbar: ttk.Scrollbar = ttk.Scrollbar(list_container, orient=tk.VERTICAL, command=self.__listbox.yview)
        self.__listbox.configure(yscrollcommand=scrollbar.set)

        self.__listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.__controller.refresh_list()

    def __create_details_tab(self) -> None:
        """创建详细信息标签页"""
        assert self.__notebook is not None, "笔记本控件未创建"
        
        details_tab = ttk.Frame(self.__notebook, padding="10")
        self.__notebook.add(details_tab, text="备份详情")

        details_frame: ttk.LabelFrame = ttk.LabelFrame(details_tab, text="备份详细信息", padding="10")
        details_frame.pack(fill=tk.BOTH, expand=True)

        self.__details_text = ScrolledText(
            details_frame, wrap=tk.WORD, font=("Consolas", 10), height=15, state=tk.DISABLED
        )
        self.__details_text.pack(fill=tk.BOTH, expand=True)

    def __create_verify_tab(self) -> None:
        """创建验证标签页"""
        assert self.__notebook is not None, "笔记本控件未创建"
        
        verify_tab = ttk.Frame(self.__notebook, padding="10")
        self.__notebook.add(verify_tab, text="完整性验证")

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
            command=self.__controller.verify_all_backups
        ).pack(side=tk.LEFT, padx=5)

        ttk.Button(
            verify_btn_frame,
            text="手动验证选中备份",
            command=self.__controller.verify_selected_backup
        ).pack(side=tk.LEFT, padx=5)
