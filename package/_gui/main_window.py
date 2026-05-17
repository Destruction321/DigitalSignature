# package/_gui/main_window.py
"""数字签名窗口UI创建模块"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import Callable, TYPE_CHECKING

from .helpers import reload_current_key
from ._key_management_tab import KeyManagementTab
from ._signing_tabs import FileSigningTab, TextSigningTab
from .._backups import BackUps
from .._cleanups import CleanUps
from .._utils.constants import BASE_DIR, DIRS
from .._utils.enums import DirType
from .._utils.tools import format_size
from .._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from .._core.keys.loader import KeyLoader
    from .._core.keys.managers import MultiKeyManager


class MainWindow:
    """数字签名窗口UI创建模块"""
    def __init__(self, root: tk.Tk, multi_km: MultiKeyManager, key_loader: KeyLoader) -> None:
        self.__root: tk.Tk = root  # 主窗口
        self.__multi_km: MultiKeyManager = multi_km
        self.__key_loader: KeyLoader = key_loader
        self.__backup_buttons: dict[str, ttk.Button] = {}
        self.__ui_state_mgr = get_ui_state_manager()
        self.__cleanups: CleanUps | None = None
        self.__backups: BackUps | None = None
        self.__status_label: ttk.Label | None = None
        self.__dir_labels: dict[DirType, ttk.Label] = {}
        self.__key_tab: KeyManagementTab | None = None
        self.__text_tab: TextSigningTab | None = None
        self.__file_tab: FileSigningTab | None = None
        
    
    """getters"""
    @property
    def dir_labels(self) -> dict[DirType, ttk.Label]:
        return self.__dir_labels
    
    @property
    def key_tab(self) -> KeyManagementTab | None:
        return self.__key_tab
    
    @property
    def text_tab(self) -> TextSigningTab | None:
        return self.__text_tab
    
    @property
    def file_tab(self) -> FileSigningTab | None:
        return self.__file_tab
    
        
    """public UI creator"""
    def setup_main_window(self) -> None:
        """设置主窗口"""
        self.__root.title("数字签名系统 - 哈尔滨工程大学")
        self.__root.geometry("1000x700")
        self.__root.minsize(900, 600)
        self.__root.columnconfigure(0, weight=1)
        self.__root.rowconfigure(0, weight=1)
        
    def setup_ui(self) -> None:
        """设置用户界面"""
        main_frame: ttk.Frame = ttk.Frame(self.__root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)

        self.__create_directory_info(main_frame)
        self.__create_tabs(main_frame)
        self.__create_tools_area(main_frame)
        self.__create_backup_area(main_frame)
        self.__create_status_bar(main_frame)

        self.__ui_state_mgr.register_status_handler(self.__handle_status_update)
        self.__ui_state_mgr.register_result_handler(self.__handle_result_show)
        self.__ui_state_mgr.register_dir_labels_handler(self.__update_dir_labels)


    """private UI creator"""
    def __create_directory_info(self, parent: tk.Widget) -> None:
        """创建目录信息区域"""
        dir_info_frame: ttk.LabelFrame = ttk.LabelFrame(parent, text="数据目录信息", padding="5")
        dir_info_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 10))
        dir_info_frame.columnconfigure(0, weight=1)

        dir_grid: ttk.Frame = ttk.Frame(dir_info_frame)
        dir_grid.pack(fill=tk.X)

        base_info: str = f"数据目录: {Path(BASE_DIR).resolve().as_posix()}"
        base_label: ttk.Label = ttk.Label(dir_grid, text=base_info, font=("微软雅黑", 9, "bold"))
        base_label.grid(row=0, column=0, columnspan=6, sticky=tk.W, pady=(0, 5))

        categories: list[DirType] = [DirType.KEYS, DirType.TEXTS, DirType.SIGNATURES, DirType.TEMP]
        labels: list[str] = ["密钥:", "文本:", "签名:", "临时:"]

        for i, (category, label) in enumerate(zip(categories, labels)):
            ttk.Label(dir_grid, text=label, font=("微软雅黑", 9)).grid(row=1, column=i * 2, sticky=tk.W, padx=(10, 2))
            self.__dir_labels[category] = ttk.Label(dir_grid, text="加载中...", font=("微软雅黑", 9))
            self.__dir_labels[category].grid(row=1, column=i * 2 + 1, sticky=tk.W, padx=(0, 15))

    def __create_tabs(self, parent: tk.Widget) -> None:
        """创建标签页"""
        notebook: ttk.Notebook = ttk.Notebook(parent)
        notebook.grid(row=1, column=0, sticky=tk.NSEW, padx=5, pady=5)

        key_tab: ttk.Frame = ttk.Frame(notebook, padding="10")
        text_tab: ttk.Frame = ttk.Frame(notebook, padding="10")
        file_tab: ttk.Frame = ttk.Frame(notebook, padding="10")

        notebook.add(key_tab, text="密钥管理")
        notebook.add(text_tab, text="文本签名")
        notebook.add(file_tab, text="文件签名")

        # 创建标签页实例
        self.__key_tab = KeyManagementTab(key_tab, self.__multi_km, self.__key_loader)
        self.__text_tab = TextSigningTab(text_tab)
        self.__file_tab = FileSigningTab(file_tab)
        
        self.__cleanups = CleanUps(self.__root)
        self.__backups = BackUps(
            root=self.__root,
            backup_buttons=self.__backup_buttons,
            refresh_callback=self.__key_tab.refresh_key_list,
            multi_km=self.__multi_km,
            key_loader=self.__key_loader
        )

    def __create_tools_area(self, parent: tk.Widget) -> None:
        """创建系统工具区域"""
        assert self.__cleanups is not None, "cleanups 模块未初始化"

        tools_frame: ttk.LabelFrame = ttk.LabelFrame(parent, text="系统工具", padding="5")
        tools_frame.grid(row=2, column=0, sticky=tk.EW, pady=5)
        tools_frame.columnconfigure(0, weight=1)

        tools_container: ttk.Frame = ttk.Frame(tools_frame)
        tools_container.pack(fill=tk.X, expand=True)

        button_row1: ttk.Frame = ttk.Frame(tools_container)
        button_row1.pack(fill=tk.X, expand=True, pady=2)

        buttons_row1: list[tuple[str, Callable[[], None]]] = [(
            "重新加载密钥",
            lambda: reload_current_key(
                multi_km=self.__multi_km,
                key_loader=self.__key_loader,
                click_reload_btn=True
            )),
            ("刷新目录信息", self.__ui_state_mgr.update_dir_labels)
        ]

        for text, command in buttons_row1:
            ttk.Button(button_row1, text=text, command=command).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        button_row2: ttk.Frame = ttk.Frame(tools_container)
        button_row2.pack(fill=tk.X, expand=True, pady=2)

        buttons_row2: list[tuple[str, Callable[[], None]]] = [
            ("完整清理", self.__cleanups.cleanup_all_files),
            ("清理孤立密钥", self.__cleanups.cleanup_orphaned_keys),
            ("清理旧文件", self.__cleanups.cleanup_old_files),
            ("清理临时文件", self.__cleanups.cleanup_temp_files)
        ]

        for text, command in buttons_row2:
            ttk.Button(button_row2, text=text, command=command).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def __create_backup_area(self, parent: tk.Widget) -> None:
        """创建备份工具区域"""
        assert self.__backups is not None, "backups 模块未初始化"   
        
        backup_frame: ttk.LabelFrame = ttk.LabelFrame(parent, text="备份工具", padding="5")
        backup_frame.grid(row=3, column=0, sticky=tk.EW, pady=5)
        backup_frame.columnconfigure(0, weight=1)

        backup_button_row: ttk.Frame = ttk.Frame(backup_frame)
        backup_button_row.pack(fill=tk.X, expand=True)

        backup_buttons: list[tuple[str, Callable[[], None]]] = [
            ("创建备份", self.__backups.show_backup_options),
            ("恢复备份", self.__backups.restore_backup_dialog),
            ("管理备份", self.__backups.backup_manager_dialog)
        ]

        # 保存按钮引用
        for text, command in backup_buttons:
            button = ttk.Button(backup_button_row, text=text, command=command)
            button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
            self.__backup_buttons[text] = button

    def __create_status_bar(self, parent: tk.Widget) -> None:
        """创建状态栏"""
        status_frame: ttk.Frame = ttk.Frame(parent)
        status_frame.grid(row=4, column=0, sticky=tk.EW)

        self.__status_label = ttk.Label(status_frame, text="就绪", relief=tk.SUNKEN, anchor=tk.W)
        self.__status_label.pack(fill=tk.X, padx=5, pady=2)

    def __handle_status_update(self, message: str) -> None:
        """处理状态更新"""
        assert self.__status_label is not None, "状态标签未初始化"
        self.__status_label.config(text=message)

    def __handle_result_show(self, text: str, tab_type: str) -> None:
        """处理结果显示"""
        assert self.__file_tab is not None, "文件标签页未初始化"
        assert self.__text_tab is not None, "文本标签页未初始化"
        assert self.__file_tab.result_text is not None, "文件结果文本框未初始化"
        assert self.__text_tab.result_text is not None, "文本结果文本框未初始化"
        
        if tab_type == "file":
            self.__file_tab.result_text.delete("1.0", tk.END)
            self.__file_tab.result_text.insert("1.0", text)
            
        elif tab_type == "text":
            self.__text_tab.result_text.delete("1.0", tk.END)
            self.__text_tab.result_text.insert("1.0", text)
            
    def __update_directory_info(self) -> None:
        """更新所有目录信息显示"""
        for category, label in self.__dir_labels.items():
            dir_path = DIRS.get(category)
            if dir_path is None:
                label.config(text=f"未知目录类别: {category}")
                continue

            dir_path = Path(dir_path)

            if not dir_path.exists():
                label.config(text="目录不存在")
                continue

            try:
                files = [f for f in dir_path.iterdir() if f.is_file()]
                file_count = len(files)
                total_size = sum(f.stat().st_size for f in files)
                size_str = format_size(total_size)
                label.config(text=f"{file_count}文件/{size_str}")
            except (PermissionError, OSError) as e:
                label.config(text=f"访问错误: {e}")

    def __update_dir_labels(self) -> None:
        """封装目录更新函数以供注册调用"""
        self.__update_directory_info()
