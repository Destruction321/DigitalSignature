# package/_gui/key_management_tab/ui_creator.py
"""密钥管理标签页UI创建器"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import cast, TYPE_CHECKING

from .controller import Controller
from ..._core.keys import creator
from ..._utils import DirType, get_path
from ..._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from ..._core.keys.loader import KeyLoader
    from ..._core.keys.managers import MultiKeyManager
    from ..._utils.ui_state_manager import UIStateManager
    

class UICreator:
    """UI创建器"""
    def __init__(self, parent: tk.Widget, multi_key_manager: MultiKeyManager, key_loader: KeyLoader) -> None:
        self.__key_id_entry: tk.Entry | None = None
        self.__encryption_var: tk.BooleanVar | None = None
        self.__key_size_combo: ttk.Combobox | None = None
        self.__password_entry: tk.Entry | None = None
        self.__ui_state_mgr: UIStateManager = get_ui_state_manager()
        
        self.__parent: tk.Widget = parent
        self.__key_listbox: tk.Listbox | None = None
        self.__key_status_label: ttk.Label | None = None
        self.__security_status_label: ttk.Label | None = None
        self.__multi_km: MultiKeyManager = multi_key_manager
        
        self.__controller: Controller = Controller(self, key_loader)


    @property
    def parent(self) -> tk.Widget:
        return self.__parent
    
    @property
    def key_listbox(self) -> tk.Listbox | None:
        return self.__key_listbox
    
    @key_listbox.setter
    def key_listbox(self, key_listbox: tk.Listbox) -> None:
        self.__key_listbox = key_listbox
    
    @property
    def key_status_label(self) -> ttk.Label | None:
        return self.__key_status_label
    
    @property
    def security_status_label(self) -> ttk.Label | None:
        return self.__security_status_label
    
    @property
    def multi_km(self) -> MultiKeyManager:
        return self.__multi_km
    
    @property
    def controller(self) -> Controller:
        return self.__controller
    
    
    """public methods -- setter"""
    def setup_ui(self) -> None:
        """设置用户界面"""
        self.__setup_parent_layout()
        self.__create_directory_info()
        self.__create_key_creation_area()
        self.__create_key_management_area()
        self.__parent.winfo_toplevel().minsize(800, 800)

    
    """private methods"""
    def __setup_parent_layout(self) -> None:
        """配置父框架布局"""
        self.__parent.columnconfigure(0, weight=1)
        self.__parent.rowconfigure(0, weight=0)  # 目录信息
        self.__parent.rowconfigure(1, weight=0)  # 密钥创建
        self.__parent.rowconfigure(2, weight=1)  # 密钥管理

    def __create_directory_info(self) -> None:
        """创建目录信息区域"""
        dir_frame = ttk.Frame(self.__parent)
        dir_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 5))

        keys_dir = get_path(DirType.KEYS)
        dir_label = ttk.Label(
            dir_frame, text=f"密钥存储目录: {keys_dir}", font=("微软雅黑", 9), foreground="blue"
        )
        dir_label.pack(anchor=tk.W)

    def __create_key_creation_area(self) -> None:
        """创建密钥生成区域"""
        create_frame = ttk.LabelFrame(self.__parent, text="创建新密钥对", padding="10")
        create_frame.grid(row=1, column=0, sticky=tk.EW, pady=5)
        create_frame.columnconfigure(1, weight=1)

        self.__create_key_id_input(create_frame)
        self.__create_key_size_selection(create_frame)
        self.__create_encryption_options(create_frame)
        self.__create_key_generation_button(create_frame)

    def __create_key_id_input(self, parent: tk.Widget) -> None:
        """创建密钥ID输入区域"""
        ttk.Label(parent, text="密钥ID:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.__key_id_entry = ttk.Entry(parent, width=30)
        self.__key_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

    def __create_key_size_selection(self, parent: tk.Widget) -> None:
        """创建密钥长度选择"""
        ttk.Label(parent, text="密钥长度:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.__key_size_combo = ttk.Combobox(
            parent, values=["1024", "2048", "4096"], width=10, state="readonly"
        )
        self.__key_size_combo.set("2048")
        self.__key_size_combo.grid(row=0, column=3, padx=5, pady=5)

    def __create_encryption_options(self, parent: tk.Widget) -> None:
        """创建加密选项区域"""
        encryption_frame = ttk.Frame(parent)
        encryption_frame.grid(row=1, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=2)

        self.__encryption_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            encryption_frame,
            text="加密存储",
            variable=self.__encryption_var,
            command=self.__toggle_password_entry
        ).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(encryption_frame, text="密码:").pack(side=tk.LEFT, padx=(0, 5))
        self.__password_entry = ttk.Entry(encryption_frame, width=15, show="*")
        self.__password_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.__password_entry.config(state=tk.DISABLED)

    def __create_key_generation_button(self, parent: tk.Widget) -> None:
        """创建密钥生成按钮"""
        if not all([self.__key_id_entry, self.__key_size_combo, self.__encryption_var, self.__password_entry]):
            messagebox.showerror("错误", "UI组件未正确初始化")
            return

        key_setter = creator.KeySetter(
            key_id_entry=cast(tk.Entry, self.__key_id_entry),
            key_size_combo=cast(ttk.Combobox, self.__key_size_combo),
            encryption_var=cast(tk.BooleanVar, self.__encryption_var),
            password_entry=cast(tk.Entry, self.__password_entry),
        )

        callbacks = creator.CallBacks(
            update_status_callback=self.__ui_state_mgr.update_status,
            refresh_callback=self.__controller.refresh_key_list,
            update_key_status_callback=self.__controller.update_key_status,
            toggle_password_callback=self.__toggle_password_entry
        )

        ttk.Button(
            parent,
            text="创建密钥对",
            command=lambda: creator.create_key_pair(
                key_setter=key_setter,
                multi_km=self.__multi_km,
                callbacks=callbacks
            )
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
        """设置管理区域布局"""
        parent.columnconfigure(0, weight=1)
        for i in range(5):
            parent.rowconfigure(i, weight=0)
        parent.rowconfigure(1, weight=1) # 密钥列表区域可扩展

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

        # 创建列表和滚动条
        self.__key_listbox = tk.Listbox(listbox_container, height=4)
        scrollbar = ttk.Scrollbar(listbox_container, orient=tk.VERTICAL, command=self.__key_listbox.yview)
        self.__key_listbox.configure(yscrollcommand=scrollbar.set)

        self.__key_listbox.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.__controller.ksy_listbox = self.__key_listbox
        self.__controller.refresh_key_list()

    def __create_operation_buttons(self, parent: tk.Widget) -> None:
        """创建操作按钮"""
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=2, column=0, sticky=tk.EW, pady=10)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        buttons = [
            ("加载选中密钥", self.__controller.load_selected_key),
            ("删除选中密钥", self.__controller.delete_selected_key),
            ("刷新列表", lambda: self.__controller.refresh_key_list(click_refresh_btn=True))
        ]

        for i, (text, command) in enumerate(buttons):
            ttk.Button(btn_frame, text=text, command=command).grid(
                row=0, column=i, padx=5, sticky=tk.EW
            )

    def __create_advanced_operations(self, parent: tk.Widget) -> None:
        """创建高级操作按钮"""
        advanced_btn_frame = ttk.Frame(parent)
        advanced_btn_frame.grid(row=3, column=0, sticky=tk.EW, pady=5)
        advanced_btn_frame.columnconfigure(0, weight=1)
        advanced_btn_frame.columnconfigure(1, weight=1)
        advanced_btn_frame.columnconfigure(2, weight=1)

        advanced_buttons = [
            ("查看加密状态", self.__controller.show_encryption_status),
            ("更改加密密码", self.__controller.change_key_password),
            ("恢复配置", self.__controller.recover_config)
        ]

        for i, (text, command) in enumerate(advanced_buttons):
            ttk.Button(advanced_btn_frame, text=text, command=command).grid(
                row=0, column=i, padx=5, sticky=tk.EW
            )

    def __create_status_display(self, parent: tk.Widget) -> None:
        """创建状态显示"""
        status_frame = ttk.Frame(parent)
        status_frame.grid(row=4, column=0, sticky=tk.EW, pady=(10, 0))

        # 密钥状态
        self.__key_status_label = ttk.Label(
            status_frame, text="未加载密钥对", foreground="red", font=("微软雅黑", 10, "bold")
        )
        self.__key_status_label.pack()

        # 配置安全状态
        self.__security_status_label = ttk.Label(
            status_frame, text="配置完整性: 未知", foreground="gray", font=("微软雅黑", 8)
        )
        self.__security_status_label.pack()

    def __toggle_password_entry(self) -> None:
        """切换密码输入框状态"""
        if self.__password_entry is None:
            return

        if self.__encryption_var and self.__encryption_var.get():
            self.__password_entry.config(state=tk.NORMAL)
        else:
            self.__password_entry.config(state=tk.DISABLED)
            self.__password_entry.delete(0, tk.END)
            