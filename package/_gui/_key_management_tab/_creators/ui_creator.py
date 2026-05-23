# package/_gui/_key_management_tab/_creators/ui_creator.py
"""密钥管理标签页UI创建器"""
import tkinter as tk
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

from . import _key_creator
from .._controller import Controller
from ...._utils.constants import LOG_DIR
from ...._utils.enums import DirType
from ...._utils.tools import get_path

if TYPE_CHECKING:
    from ...._core.keys.loader import KeyLoader
    from ...._core.keys.managers import MultiKeyManager
    

class UICreator:
    """密钥管理标签页UI创建器"""
    def __init__(self,
                 parent: tk.Widget,
                 multi_key_manager: MultiKeyManager,
                 key_loader: KeyLoader) -> None:
        self.__parent: tk.Widget = parent
        self.__multi_km: MultiKeyManager = multi_key_manager
        
        # UI组件
        self.__key_id_entry: ttk.Entry | None = None
        self.__encryption_var: tk.BooleanVar | None = None
        self.__key_size_combo: ttk.Combobox | None = None
        self.__password_entry: ttk.Entry | None = None
        self.__key_listbox: tk.Listbox | None = None
        self.__key_status_label: ttk.Label | None = None
        self.__security_status_label: ttk.Label | None = None

        # 控制器
        self.__controller: Controller = Controller(
            km_tab=self,
            multi_km=multi_key_manager,
            key_loader=key_loader,
            parent=parent
        )

    
    @property
    def controller(self) -> Controller:
        return self.__controller


    """KeyManagerProtocol协议实现"""
    def populate_key_list(self, items: list[tuple[str, str]]) -> None:
        assert self.__key_listbox is not None, "密钥列表框未初始化"

        self.__key_listbox.delete(0, tk.END)
        for display_text, _ in items:
            self.__key_listbox.insert(tk.END, display_text)

    def get_selected_display_text(self) -> str | None:
        assert self.__key_listbox is not None, "密钥列表框未初始化"
        
        selection = self.__key_listbox.curselection()
        if not selection:
            return None
        
        return self.__key_listbox.get(selection[0])

    def set_key_status(self, text: str, color: str) -> None:
        assert self.__key_status_label is not None, "密钥状态标签未初始化"
        
        self.__key_status_label.config(text=text, foreground=color)

    def set_security_status(self, text: str, color: str) -> None:
        assert self.__security_status_label is not None, "安全状态标签未初始化"
        
        self.__security_status_label.config(text=text, foreground=color)


    """public methods"""
    def setup_ui(self) -> None:
        """设置用户界面"""
        self.__setup_parent_layout()
        self.__create_directory_info()
        self.__create_key_creation_area()
        self.__create_key_management_area()


    """private methods"""
    def __setup_parent_layout(self) -> None:
        """初始化整体框架"""
        self.__parent.columnconfigure(0, weight=1)
        self.__parent.rowconfigure(0, weight=0)
        self.__parent.rowconfigure(1, weight=0)
        self.__parent.rowconfigure(2, weight=1)

    def __create_directory_info(self) -> None:
        """创建目录信息区域"""
        dir_frame = ttk.Frame(self.__parent)
        dir_frame.grid(row=0, column=0, sticky=tk.EW, pady=5)
        keys_dir = Path(get_path(DirType.KEYS)).as_posix()
        ttk.Label(
            dir_frame,
            text=f"密钥存储目录: {keys_dir}",
            font=("微软雅黑", 9),
            foreground="blue",
        ).grid(row=0, column=0, sticky=tk.W)
        
        ttk.Label(
            dir_frame,
            text=f"日志存储目录: {LOG_DIR}",
            font=("微软雅黑", 9),
            foreground="red",
        ).grid(row=1, column=0, sticky=tk.W)

    def __create_key_creation_area(self) -> None:
        """创建密钥创建区域"""
        create_frame = ttk.LabelFrame(self.__parent, text="创建新密钥对", padding="10")
        create_frame.grid(row=1, column=0, sticky=tk.EW, pady=5)
        create_frame.columnconfigure(1, weight=1)

        self.__create_key_id_input(create_frame)
        self.__create_key_size_selection(create_frame)
        self.__create_encryption_options(create_frame)
        self.__create_key_generation_button(create_frame)

    def __create_key_id_input(self, parent: tk.Widget) -> None:
        """创建密钥ID输入框"""
        ttk.Label(parent, text="密钥ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.__key_id_entry = ttk.Entry(parent, width=30)
        self.__key_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

    def __create_key_size_selection(self, parent: tk.Widget) -> None:
        """创建密钥长度选择框"""
        ttk.Label(parent, text="密钥长度:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.__key_size_combo = ttk.Combobox(
            parent, values=["1024", "2048", "4096"], width=10, state="readonly"
        )
        self.__key_size_combo.set("2048")
        self.__key_size_combo.grid(row=0, column=3, padx=5, pady=5)

    def __create_encryption_options(self, parent: tk.Widget) -> None:
        """创建加密选项"""
        encryption_frame = ttk.Frame(parent)
        encryption_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=2)

        self.__encryption_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            encryption_frame,
            text="加密存储",
            variable=self.__encryption_var,
            command=self.__toggle_password_entry,
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(encryption_frame, text="密码:").pack(side=tk.LEFT, padx=(0, 5))
        self.__password_entry = ttk.Entry(encryption_frame, width=15, show="*")
        self.__password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.__password_entry.config(state=tk.DISABLED)

    def __create_key_generation_button(self, parent: tk.Widget) -> None:
        """创建生成密钥对按钮"""
        assert self.__key_id_entry is not None, "密钥ID输入框未初始化"
        assert self.__key_size_combo is not None, "密钥长度下拉框未初始化"
        assert self.__encryption_var is not None, "加密选项变量未初始化"
        assert self.__password_entry is not None, "密码输入框未初始化"

        key_setter = _key_creator.KeySetter(
            key_id_entry=self.__key_id_entry,
            key_size_combo=self.__key_size_combo,
            encryption_var=self.__encryption_var,
            password_entry=self.__password_entry,
        )

        callbacks = _key_creator.CallBacks(
            refresh_callback=self.__controller.refresh_key_list,
            update_key_status_callback=self.__controller.update_key_status,
            toggle_password_callback=self.__toggle_password_entry,
        )

        ttk.Button(
            parent,
            text="创建密钥对",
            command=lambda: _key_creator.create_key_pair(
                key_setter=key_setter,
                multi_km=self.__multi_km,
                callbacks=callbacks,
                parent=self.__parent,
            ),
        ).grid(row=0, column=4, padx=5, pady=5)

    def __create_key_management_area(self) -> None:
        """创建密钥管理区域"""
        manage_frame = ttk.LabelFrame(self.__parent, text="密钥对管理", padding="10")
        manage_frame.grid(row=2, column=0, sticky=tk.NSEW, pady=5)

        self.__setup_management_layout(manage_frame)
        self.__create_key_list_label(manage_frame)
        self.__create_key_list_area(manage_frame)
        self.__create_operation_buttons(manage_frame)
        self.__create_advanced_operations(manage_frame)
        self.__create_status_display(manage_frame)

    @staticmethod
    def __setup_management_layout(parent: tk.Widget) -> None:
        """设置密钥管理区域布局"""
        parent.columnconfigure(0, weight=1)
        for i in range(5):
            parent.rowconfigure(i, weight=0)
        parent.rowconfigure(1, weight=1)

    @staticmethod
    def __create_key_list_label(parent: tk.Widget) -> None:
        """创建密钥列表标签"""
        list_label_frame = ttk.Frame(parent)
        list_label_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 5))
        list_label_frame.columnconfigure(0, weight=1)
        ttk.Label(list_label_frame, text="可用密钥对:").grid(row=0, column=0, sticky=tk.W, padx=5)

    def __create_key_list_area(self, parent: tk.Widget) -> None:
        """创建密钥列表区域"""
        list_container = ttk.Frame(parent)
        list_container.grid(row=1, column=0, sticky=tk.NSEW, pady=(0, 10))
        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        listbox_container = ttk.Frame(list_container)
        listbox_container.grid(row=0, column=0, sticky=tk.NSEW, padx=5)
        listbox_container.columnconfigure(0, weight=1)
        listbox_container.rowconfigure(0, weight=1)
        listbox_container.grid_propagate(False)
        listbox_container.configure(height=80)

        self.__key_listbox = tk.Listbox(listbox_container, height=4)
        scrollbar = ttk.Scrollbar(
            listbox_container, orient=tk.VERTICAL, command=self.__key_listbox.yview
        )
        self.__key_listbox.configure(yscrollcommand=scrollbar.set)

        self.__key_listbox.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        # 列表创建完成后触发首次刷新
        self.__controller.refresh_key_list()

    def __create_operation_buttons(self, parent: tk.Widget) -> None:
        """创建操作按钮"""
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=2, column=0, sticky=tk.EW, pady=10)
        for i in range(3):
            btn_frame.columnconfigure(i, weight=1)

        buttons = [
            ("加载选中密钥", self.__controller.load_selected_key),
            ("删除选中密钥", self.__controller.delete_selected_key),
            ("刷新列表", lambda: self.__controller.refresh_key_list(click_refresh_btn=True)),
        ]
        for i, (text, command) in enumerate(buttons):
            ttk.Button(btn_frame, text=text, command=command).grid(row=0, column=i, padx=5, sticky=tk.EW)

    def __create_advanced_operations(self, parent: tk.Widget) -> None:
        """创建高级操作按钮"""
        advanced_btn_frame = ttk.Frame(parent)
        advanced_btn_frame.grid(row=3, column=0, sticky=tk.EW, pady=5)
        for i in range(3):
            advanced_btn_frame.columnconfigure(i, weight=1)

        advanced_buttons = [
            ("查看加密状态", self.__controller.show_encryption_status),
            ("更改加密密码", self.__controller.change_key_password),
            ("恢复配置", self.__controller.recover_config),
        ]
        for i, (text, command) in enumerate(advanced_buttons):
            ttk.Button(advanced_btn_frame, text=text, command=command).grid(row=0, column=i, padx=5, sticky=tk.EW)

    def __create_status_display(self, parent: tk.Widget) -> None:
        """创建状态显示区域"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=4, column=0, sticky=tk.EW, pady=(10, 0))

        self.__key_status_label = ttk.Label(
            status_frame,
            text="未加载密钥对",
            foreground="red",
            font=("微软雅黑", 10, "bold"),
        )
        self.__key_status_label.pack()

        self.__security_status_label = ttk.Label(
            status_frame,
            text="配置完整性: 未知",
            foreground="gray",
            font=("微软雅黑", 8),
        )
        self.__security_status_label.pack()

    def __toggle_password_entry(self) -> None:
        """切换密码输入框启用状态"""
        assert self.__encryption_var is not None, "加密选项变量未初始化"
        assert self.__password_entry is not None, "密码输入框未初始化"

        if self.__encryption_var.get():
            self.__password_entry.config(state=tk.NORMAL)
        else:
            self.__password_entry.config(state=tk.DISABLED)
            self.__password_entry.delete(0, tk.END)
