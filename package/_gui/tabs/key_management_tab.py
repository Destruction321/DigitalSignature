# package/_gui/tabs/key_management_tab.py
"""密钥管理标签页"""
import tkinter as tk
from tkinter import ttk, messagebox
from typing import cast, TYPE_CHECKING

from ..._core.keys import creator
from ..._core.keys.manager import SingleKeyManager
from ..._functions.password_validator import PasswordValidator
from ..._utils import DirType, ENCRYPTED, get_path, PassWord, Status
from ..._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from ..._core.keys.loader import KeyLoader
    from ..._core.keys.manager import MultiKeyManager
    from ..._utils.ui_state_manager import UIStateManager


class KeyManagementTab:
    """密钥管理标签页"""
    def __init__(self, parent: tk.Widget,
                 multi_key_manager: MultiKeyManager,
                 key_loader: KeyLoader) -> None:
        # UI组件引用
        self.__key_id_entry: tk.Entry | None = None
        self.__key_listbox: tk.Listbox | None = None
        self.__key_size_combo: ttk.Combobox | None = None
        self.__key_status_label: ttk.Label | None = None
        self.__security_status_label: ttk.Label | None = None
        self.__encryption_var: tk.BooleanVar | None = None
        self.__password_entry: tk.Entry | None = None
        self.__loaded_key_id: str | None = None
        self.__key_id_map: dict[str, str] = {}

        # 依赖注入
        self.__parent: tk.Widget = parent
        self.__multi_km: MultiKeyManager = multi_key_manager
        self.__ui_state_mgr: UIStateManager = get_ui_state_manager()

        # 设置恢复回调
        self.__multi_km.recovery_callback = self.__handle_key_recovery

        # 创建专门的处理器
        self.__key_loader = key_loader

        # 创建密码验证服务
        self.__password_validator = PasswordValidator(
            multi_key_manager,
            parent,
            update_status=self.__ui_state_mgr.update_status,
            refresh_list=self.refresh_key_list,
            update_security=self.__update_security_status
        )
        
        # 构建UI
        self.__setup_ui()

        # 初始化安全状态显示（启动时自动验证已完成）
        self.__update_security_status(self.__multi_km.config_secure)
    
        
    @property
    def loaded_key_id(self) -> str | None:
        return self.__loaded_key_id

    @loaded_key_id.setter
    def loaded_key_id(self, key_id: str | None) -> None:
        self.__loaded_key_id = key_id
        self.update_key_status()

    @property
    def key_loader(self) -> KeyLoader:
        return self.__key_loader
    
    @key_loader.setter
    def key_loader(self, loader: KeyLoader) -> None:
        self.__key_loader = loader


    """UI creator"""
    def __setup_ui(self) -> None:
        """设置用户界面"""
        self.__setup_parent_layout()
        self.__create_directory_info()
        self.__create_key_creation_area()
        self.__create_key_management_area()
        self.__parent.winfo_toplevel().minsize(800, 800)

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
            refresh_callback=self.refresh_key_list,
            update_key_status_callback=self.update_key_status,
            toggle_password_callback=self.__toggle_password_entry
        )

        ttk.Button(
            parent,
            text="创建密钥对",
            command=lambda: creator.create_key_pair(
                key_setter,
                self.__multi_km,
                callbacks
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

    def __toggle_password_entry(self) -> None:
        """切换密码输入框状态"""
        if self.__password_entry is None:
            return

        if self.__encryption_var and self.__encryption_var.get():
            self.__password_entry.config(state=tk.NORMAL)
        else:
            self.__password_entry.config(state=tk.DISABLED)
            self.__password_entry.delete(0, tk.END)

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

        self.refresh_key_list()

    def __create_operation_buttons(self, parent: tk.Widget) -> None:
        """创建操作按钮"""
        btn_frame = ttk.Frame(parent)
        btn_frame.grid(row=2, column=0, sticky=tk.EW, pady=10)
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)
        btn_frame.columnconfigure(2, weight=1)

        buttons = [
            ("加载选中密钥", self.__load_selected_key),
            ("删除选中密钥", self.__delete_selected_key),
            ("刷新列表", lambda: self.refresh_key_list(click_refresh_btn=True))
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
            ("查看加密状态", self.__show_encryption_status),
            ("更改加密密码", self.__change_key_password),
            ("恢复配置", self.__recover_config)
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


    """Other private methods"""
    def __handle_key_recovery(self, key_id: str, action: PassWord) -> None:
        """处理密钥恢复"""
        if action != PassWord.RECOVERY:
            return

        # 询问用户想要做什么
        choice = messagebox.askyesno(
            "加密密钥恢复",
            f"发现加密密钥 '{key_id}'，您想要做什么？\n\n"
            f"是(Y): 重置密码（需要输入旧密码，最多尝试3次）\n"
            f"否(N): 暂时跳过，稍后手动处理\n"
        )

        if choice: # 用户选择重置密码
            self.__handle_change_result(key_id, PassWord.RECOVERY)
        else:  # 用户选择跳过
            self.__ui_state_mgr.update_status(f"跳过加密密钥 '{key_id}' 的恢复")

    def __handle_change_result(self, key_id: str, mode: PassWord) -> None:
        change_result = self.__password_validator.validate_and_reset_password(
            key_id=key_id,
            mode=mode
        )
        if change_result.is_success():
            messagebox.showinfo("成功", f"密钥 '{key_id}' 密码修改成功：{change_result.msg}")
            return
        
        if change_result.status == Status.CANCEL_INPUT:
            messagebox.showinfo("取消", f"密钥 '{key_id}' 已{change_result.msg}")
            return
            
        messagebox.showerror("错误", f"密钥 '{key_id}' 修改密码失败：{change_result.msg}")

    def __recover_config(self) -> None:
        """恢复配置"""
        response = messagebox.askyesno(
            "恢复密钥配置",
            "确定要恢复密钥配置吗？\n\n"
            "这将：\n"
            "1. 扫描密钥目录重建配置\n"
            "2. 遇到加密密钥时提示重新设置密码\n"
            "3. 当前配置将被覆盖"
        )

        if not response:
            return

        result = self.__multi_km.recovery_mgr.try_rebuild_from_files()
        # 执行配置恢复
        if result.is_success():
            messagebox.showinfo("成功", "配置恢复成功")
            self.refresh_key_list()
            self.update_key_status()
            self.__ui_state_mgr.update_status("配置恢复完成")
            # 恢复配置后会保存配置，更新安全状态
            self.__update_security_status(True)
            # 配置恢复后，重置加载状态
            self.__loaded_key_id = None
        else:
            messagebox.showerror("错误", f"配置恢复失败: {result.msg}")

    def __change_key_password(self) -> None:
        """更改密钥的加密密码"""
        self.__key_listbox = cast(tk.Listbox, self.__key_listbox)
        selection = self.__key_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return
        
        display_text = self.__key_listbox.get(selection[0])
        key_id = self.__get_key_id_and_size(display_text)
        if not key_id:
            messagebox.showerror("错误", "无法解析密钥ID")
            return
        
        self.__handle_change_result(key_id, PassWord.CHANGE)
        
    def __load_selected_key(self) -> SingleKeyManager | None:
        """加载选中的密钥"""
        self.__key_listbox = cast(tk.Listbox, self.__key_listbox)
        selection = self.__key_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return None
        
        display_text = self.__key_listbox.get(selection[0])
        key_id = self.__get_key_id_and_size(display_text)
        if not key_id:
            messagebox.showerror("错误", "无法解析密钥ID")
            return None
        
        try:
            load_result = self.__key_loader.load_key(key_id)
            if load_result.is_success():
                self.update_key_status()
                return cast(SingleKeyManager, load_result.data)
            else:
                messagebox.showerror("加载失败", load_result.msg)
                self.__ui_state_mgr.update_status(f"加载失败: {load_result.msg}")
                return None
            
        except Exception as e:
            messagebox.showerror("系统错误", f"加载密钥时发生系统错误: {str(e)}")
            return None

    def __get_key_id_and_size(self, display_text: str) -> str:
        """从显示文本中提取密钥ID和长度"""
        if display_text in self.__key_id_map:
            return self.__key_id_map[display_text]

        # 密钥ID[加密状态，密钥长度位]
        if "[" in display_text:
            return display_text.split("[")[0].strip()
        else:
            return display_text

    def __delete_selected_key(self) -> None:
        """删除选中的密钥"""
        self.__key_listbox = cast(tk.Listbox, self.__key_listbox)
        selection = self.__key_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return
        
        display_text = self.__key_listbox.get(selection[0])
        key_id = self.__get_key_id_and_size(display_text)
        if not key_id:
            messagebox.showerror("错误", "无法解析密钥ID")
            return
        
        if not messagebox.askyesno("确认", f"确定要删除密钥对 '{key_id}' 吗？"):
            return
        
        delete_result = self.__multi_km.delete_key_pair(key_id)
        if not delete_result.is_success():
            messagebox.showerror("删除失败", delete_result.msg)
            return
        
        self.refresh_key_list()
        self.update_key_status()
        self.__ui_state_mgr.update_status(f"删除密钥对: {key_id}")
        
        if key_id == self.__loaded_key_id:
            self.__loaded_key_id = None
            
        self.__update_security_status(True)
        messagebox.showinfo("成功", delete_result.msg)

    def __show_encryption_status(self) -> None:
        """显示选中密钥的加密状态"""
        self.__key_listbox = cast(tk.Listbox, self.__key_listbox)
        selection = self.__key_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return
        
        display_text = self.__key_listbox.get(selection[0])
        key_id = self.__get_key_id_and_size(display_text)
        if not key_id:
            messagebox.showerror("错误", "无法解析密钥ID")
            return

        status_result = self.__multi_km.get_key_encryption_status(key_id)
        if status_result.is_success():
            messagebox.showinfo("加密状态", f"密钥 '{key_id}' 的状态:\n\n{status_result.msg}")
        else:
            messagebox.showerror("错误", status_result.msg)

    def __update_security_status(self, is_secure: bool) -> None:
        """更新安全状态显示"""
        if self.__security_status_label is None:
            return

        # 更新MultiKeyManager的安全状态
        self.__multi_km.config_secure = is_secure

        if is_secure:
            self.__security_status_label.config(text="配置完整性: 已验证", foreground="green")
        else:
            self.__security_status_label.config(text="配置完整性: 未验证/已损坏", foreground="orange")


    """public methods"""
    def refresh_key_list(self, click_refresh_btn: bool = False) -> None:
        """刷新密钥列表"""
        if self.__key_listbox is None:
            return
        
        self.__key_listbox.delete(0, tk.END)
        self.__key_id_map.clear()
        keys = list(self.__multi_km.key_pairs.keys())
        
        if not keys:
            self.__multi_km.recovery_mgr.try_rebuild_from_files()
            keys = list(self.__multi_km.key_pairs.keys())
            if not keys:
                if click_refresh_btn:
                    messagebox.showerror("警告", "没有可用的密钥对")
                return
            
        for key_id in keys:
            status_result = self.__multi_km.get_key_encryption_status(key_id)
            
            if status_result.is_success():
                key_info = self.__multi_km.key_pairs.get(key_id, {})
                key_size = key_info.get("key_size", "未知")
                display_text = f"{key_id}[{status_result.msg}，{key_size}位]"
            else:
                key_info = self.__multi_km.key_pairs.get(key_id, {})
                key_size = key_info.get("key_size", "未知")
                display_text = f"{key_id}[状态未知，{key_size}位]"
                
            self.__key_id_map[display_text] = key_id
            self.__key_listbox.insert(tk.END, display_text)
    
    def update_key_status(self) -> None:
        """更新密钥状态显示"""
        if self.__key_status_label is None:
            return
        
        current_key_id = self.__multi_km.current_key_id
        if current_key_id is None:
            self.__key_status_label.config(text="未选择密钥", foreground="gray")
            return
        
        status_result = self.__multi_km.get_key_encryption_status(current_key_id)
        if not status_result.is_success():
            self.__key_status_label.config(text="未找到密钥对", foreground="red")
            return
        
        status = status_result.msg
        
        if current_key_id == self.__loaded_key_id:
            status_text = f"当前密钥: {current_key_id} (已加载, {status})"
            color = "green"
        else:
            if ENCRYPTED in status:
                status_text = f"当前密钥: {current_key_id} (未解密, {status})"
            else:
                status_text = f"当前密钥: {current_key_id} (未加载, {status})"   
            color = "orange"
            
        self.__key_status_label.config(text=status_text, foreground=color)
