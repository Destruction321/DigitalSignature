# package/app.py
"""数字签名系统主模块"""
import tkinter as tk
from collections import Counter
from glob import glob
from pathlib import Path
from tkinter import ttk, messagebox
from typing import Callable, cast
from shutil import move

from . import _utils
from ._core.keys.key_loader import KeyLoader
from ._core.keys.key_manager import SingleKeyManager, MultiKeyManager
from ._gui.key_management_tab import KeyManagementTab
from ._gui.signing_tabs.file_signing_tab import FileSigningTab
from ._gui.signing_tabs.text_signing_tab import TextSigningTab
from ._services import cleanup_services
from ._services.backup import backup_services
from ._services.backup.backup_manager import BackupManager
from ._services.backup.backup_restore import BackupRestore
from ._utils import DirType, FileType, KeyType, Status
from ._utils.ui_state_manager import get_ui_state_manager


class APP:
    """数字签名系统主模块"""
    def __init__(self, root: tk.Tk) -> None:
        self.__current_km: SingleKeyManager | None = None  # 当前密钥管理器
        self.__dir_labels: dict[DirType, ttk.Label] = {}  # 目录标签
        self.__cleanup_days_threshold: int = 30 # 清理旧文件的阈值天数, 默认30天
        self.__backup_buttons: dict[str, ttk.Button] = {}
        self.__root: tk.Tk = root  # 主窗口
        self.__status_label: ttk.Label | None = None  # 状态标签
        self.__key_tab: KeyManagementTab | None = None  # 密钥管理标签页
        self.__text_tab: TextSigningTab | None = None  # 文本签名标签页
        self.__file_tab: FileSigningTab | None = None  # 文件签名标签页

        self.__setup_main_window()
        self.__initialize_managers()
        
        self.__setup_ui()
        self.__migrate_existing_files()
        self.__update_directory_info()
        
        self.__auto_load_current_key()


    @property
    def current_km(self) -> SingleKeyManager | None:
        return self.__current_km


    """initialization methods"""
    def __setup_main_window(self) -> None:
        """设置主窗口"""
        self.__root.title("数字签名系统 - 哈尔滨工程大学")
        self.__root.geometry("1000x700")
        self.__root.minsize(900, 600)
        self.__root.columnconfigure(0, weight=1)
        self.__root.rowconfigure(0, weight=1)

    def __initialize_managers(self) -> None:
        """初始化管理器"""
        self.__multi_km: MultiKeyManager = MultiKeyManager()
        self.__ui_state_mgr = get_ui_state_manager()
        
        self.__key_loader = KeyLoader(
            multi_key_manager=self.__multi_km,
            parent=self.__root,
            key_loaded_callback=self.__on_key_loaded,
            update_status_callback=self.__ui_state_mgr.update_status,
        )


    """UI creator"""
    def __setup_ui(self) -> None:
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

    def __create_directory_info(self, parent: tk.Widget) -> None:
        """创建目录信息区域"""
        dir_info_frame: ttk.LabelFrame = ttk.LabelFrame(parent, text="数据目录信息", padding="5")
        dir_info_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 10))
        dir_info_frame.columnconfigure(0, weight=1)

        dir_grid: ttk.Frame = ttk.Frame(dir_info_frame)
        dir_grid.pack(fill=tk.X)

        base_info: str = f"数据目录: {Path(_utils.BASE_DIR).resolve()}"
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

    def __create_tools_area(self, parent: tk.Widget) -> None:
        """创建系统工具区域"""
        tools_frame: ttk.LabelFrame = ttk.LabelFrame(parent, text="系统工具", padding="5")
        tools_frame.grid(row=2, column=0, sticky=tk.EW, pady=5)
        tools_frame.columnconfigure(0, weight=1)

        tools_container: ttk.Frame = ttk.Frame(tools_frame)
        tools_container.pack(fill=tk.X, expand=True)

        button_row1: ttk.Frame = ttk.Frame(tools_container)
        button_row1.pack(fill=tk.X, expand=True, pady=2)

        buttons_row1: list[tuple[str, Callable[[], None]]] = [
            ("清理临时文件", self.__cleanup_temp_files),
            ("重新加载密钥", lambda: self.__reload_current_key(click_reload_btn=True)),
            ("刷新目录信息", self.__update_directory_info),
            ("清理孤立密钥", self.__cleanup_orphaned_keys)
        ]

        for text, command in buttons_row1:
            ttk.Button(button_row1, text=text, command=command).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        button_row2: ttk.Frame = ttk.Frame(tools_container)
        button_row2.pack(fill=tk.X, expand=True, pady=2)

        buttons_row2: list[tuple[str, Callable[[], None]]] = [
            ("备份所有数据", self.__backup_all_data),
            ("清理旧文件", self.__cleanup_old_files),
            ("完整清理", self.__cleanup_all_files)
        ]

        for text, command in buttons_row2:
            ttk.Button(button_row2, text=text, command=command).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def __create_backup_area(self, parent: tk.Widget) -> None:
        """创建备份工具区域"""
        backup_frame: ttk.LabelFrame = ttk.LabelFrame(parent, text="备份工具", padding="5")
        backup_frame.grid(row=3, column=0, sticky=tk.EW, pady=5)
        backup_frame.columnconfigure(0, weight=1)

        backup_button_row: ttk.Frame = ttk.Frame(backup_frame)
        backup_button_row.pack(fill=tk.X, expand=True)

        backup_buttons: list[tuple[str, Callable[[], None]]] = [
            ("创建备份", self.__show_backup_options),
            ("恢复备份", self.__restore_backup_dialog),
            ("管理备份", self.__backup_manager_dialog)
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


    """core logic"""
    def __migrate_existing_files(self) -> None:
        """迁移现有文件到新的目录结构"""
        PRIVATE_, PUBLIC_, _PEM, _TXT, _SIG = self.__get_constants()
        migration_map: dict[DirType, list[str]] = {
            DirType.KEYS: [
                f"{PRIVATE_}key_*{_PEM}",
                f"{PUBLIC_}key_*{_PEM}",
                _utils.KEYS_CONFIG_FILE
            ],
            DirType.TEXTS: [_TXT],
            DirType.SIGNATURES: [_SIG]
        }

        exclude_files = [f"requirements{_TXT}", f"README{_TXT}"]
        migrated_files: list[tuple[DirType, str, str]] = []

        for category, patterns in migration_map.items():
            for pattern in patterns:
                for old_file in glob(pattern):
                    old_file_path = Path(old_file)
                    if old_file_path.name in exclude_files:
                        continue

                    if not old_file_path.is_file() or old_file.startswith(_utils.BASE_DIR):
                        continue

                    new_path = _utils.get_path(category, old_file_path.name)

                    if Path(new_path).exists():
                        continue

                    try:
                        move(old_file, new_path)
                        migrated_files.append((category, old_file, new_path))
                    except Exception as e:
                        print(f"迁移文件失败 {old_file}: {e}")

        if not migrated_files:
            return

        category_counts = Counter(category for category, _, _ in migrated_files)

        migration_info = "已自动迁移文件到data目录:\n\n"
        
        for category, count in category_counts.items():
            migration_info += f"{category}: {count} 个文件\n"

        messagebox.showinfo("文件迁移", migration_info)

    def __update_directory_info(self) -> None:
        """更新所有目录信息显示"""
        for category, label in self.__dir_labels.items():
            # 获取目录路径
            dir_path = _utils.DIRS.get(category)
            if not dir_path:
                print(f"未知目录类别: {category}")
                continue
            
            dir_path = Path(dir_path)
            
            if not dir_path.exists():
                # 目录不存在
                label.config(text="目录不存在")
                continue
            
            # 计算文件数和总大小
            try:
                files = [f for f in dir_path.iterdir() if f.is_file()]
                file_count = len(files)
                total_size = sum(f.stat().st_size for f in files)
                size_str = _utils.format_size(total_size)
                label.config(text=f"{file_count}文件/{size_str}")
                
            except (PermissionError, OSError) as e:
                label.config(text=f"访问错误: {e}")

    def __auto_load_current_key(self) -> None:
        """程序启动时自动加载当前密钥"""
        if self.__multi_km.current_key_id is None:
            self.__ui_state_mgr.update_status("请先在密钥管理标签页加载密钥对")
            return

        self.__key_tab = cast(KeyManagementTab, self.__key_tab)
        try:
            # 使用KeyLoader静默加载
            loading_result = self.__key_loader.load_key(self.__multi_km.current_key_id, silent=True)
            success = loading_result.is_success()
            result = loading_result.data
            
            if success and isinstance(result, SingleKeyManager):
                # 设置密钥管理器
                self.__set_current_key_manager(result)
                self.__update_directory_info()
                self.__key_tab.loaded_key_id = self.__multi_km.current_key_id
                self.__ui_state_mgr.update_status(f"自动加载密钥成功: {self.__multi_km.current_key_id}")
            elif not success and loading_result.status == Status.NEED_PASSWORD:
                self.__ui_state_mgr.update_status(f"密钥 '{self.__multi_km.current_key_id}' 已加密，请手动加载")
            else:
                self.__ui_state_mgr.update_status("自动加载密钥失败，请手动加载")

        except Exception as e:
            self.__ui_state_mgr.update_status(f"自动加载密钥出错: {e}")

        # 更新密钥标签页显示
        self.__key_tab.update_key_status()


    """Backups"""
    def __show_backup_options(self) -> None:
        """显示备份选项菜单"""
        menu: tk.Menu = tk.Menu(self.__root, tearoff=0)
        menu.add_command(label="完整备份", command=self.__backup_all_data)
        menu.add_command(label="仅备份密钥", command=self.__backup_keys_only)
        menu.add_command(label="仅备份文本", command=self.__backup_texts_only)
        menu.add_command(label="仅备份签名", command=self.__backup_signatures_only)

        try:
            backup_button = self.__root.nametowidget(str(self.__backup_buttons.get("创建备份")))
            x: int = backup_button.winfo_rootx()
            y: int = backup_button.winfo_rooty() + backup_button.winfo_height()
            menu.post(x, y)
        except AttributeError:
            menu.post(self.__root.winfo_pointerx(), self.__root.winfo_pointery())

    def __backup_all_data(self) -> None:
        """备份所有数据"""
        backup_result = backup_services.create_backup(DirType.FULL)
        self.__handle_backup_result(backup_result.is_success(), backup_result.msg, "数据备份")

    def __backup_keys_only(self) -> None:
        """仅备份密钥"""
        backup_result = backup_services.create_backup(DirType.KEYS)
        self.__handle_backup_result(backup_result.is_success(), backup_result.msg, "密钥备份")

    def __backup_texts_only(self) -> None:
        """仅备份文本"""
        backup_result = backup_services.create_backup(DirType.TEXTS)
        self.__handle_backup_result(backup_result.is_success(), backup_result.msg, "文本备份")

    def __backup_signatures_only(self) -> None:
        """仅备份签名"""
        backup_result = backup_services.create_backup(DirType.SIGNATURES)
        self.__handle_backup_result(backup_result.is_success(), backup_result.msg, "签名备份")

    def __handle_backup_result(self, success: bool, result: str, operation: str) -> None:
        """处理备份结果"""
        if success:
            self.__ui_state_mgr.update_status(f"{operation}完成")
            messagebox.showinfo("备份成功", f"{operation}完成:\n\n{result}")
        else:
            messagebox.showerror("备份失败", f"{operation}失败:\n\n{result}")

    def __restore_backup_dialog(self) -> None:
        """恢复备份对话框"""
        backups = backup_services.list_backups_with_integrity()
        if not backups:
            messagebox.showinfo("恢复备份", "没有找到可用的备份文件")
            return

        dialog = BackupRestore(
            self.__root,
            self.__ui_state_mgr.update_status,
            self.__update_directory_info,
            cast(KeyManagementTab, self.__key_tab).refresh_key_list,
            self.__reload_current_key
        )
        dialog.show()

    def __backup_manager_dialog(self) -> None:
        """统一备份管理对话框"""
        parent_window = cast(tk.Widget, cast(object, self.__root.winfo_toplevel()))
        dialog = BackupManager(parent_window, self.__ui_state_mgr.update_status)
        dialog.show()

    """Cleanups"""
    def __cleanup_all_files(self) -> None:
        """执行完整清理所有文件"""
        # 弹出对话框让用户选择阈值天数
        selected_days = self.__show_days_selection_dialog()

        # 如果用户选择了天数（点击了确定），则执行完整清理
        if selected_days is not None:
            self.__cleanup_days_threshold = selected_days
            cleanup_result = cleanup_services.cleanup_all_files(
                self.__ui_state_mgr.update_status,
                self.__update_directory_info, 
                selected_days
            )
            self.__handle_cleanup_result(cleanup_result)
        

    def __cleanup_temp_files(self) -> None:
        """清理临时文件"""
        cleanup_result = cleanup_services.cleanup_temp_files()
        self.__handle_cleanup_result(cleanup_result)

    def __cleanup_orphaned_keys(self) -> None:
        """清理孤立的密钥文件"""
        cleanup_result = cleanup_services.cleanup_orphaned_keys()
        self.__handle_cleanup_result(cleanup_result)

    def __cleanup_old_files(self) -> None:
        """清理旧文件"""
        # 弹出对话框让用户选择阈值天数
        selected_days = self.__show_days_selection_dialog()

        # 如果用户选择了天数（点击了确定），则执行清理
        if selected_days is not None:
            self.__cleanup_days_threshold = selected_days
            cleanup_result = cleanup_services.cleanup_old_files(
                self.__cleanup_days_threshold,
                [DirType.TEXTS, DirType.SIGNATURES, DirType.TEMP]
            )
            self.__handle_cleanup_result(cleanup_result)

    def __show_days_selection_dialog(self) -> int | None:
        """显示天数选择对话框，返回用户选择的天数或None（用户取消）"""
        days_options = [1, 3, 7, 15, 30, 60]

        # 创建自定义对话框
        dialog = tk.Toplevel(self.__root)
        dialog.title("选择清理阈值")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self.__root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        x = self.__root.winfo_x() + (self.__root.winfo_width() - dialog.winfo_width()) // 2
        y = self.__root.winfo_y() + (self.__root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # 添加标签
        label = ttk.Label(dialog, text="请选择清理旧文件的阈值天数:", font=("微软雅黑", 10))
        label.pack(pady=15)

        # 创建变量来存储选择的天数，默认为当前阈值
        selected_days = tk.IntVar(value=self.__cleanup_days_threshold)

        # 创建选项框架
        options_frame = ttk.Frame(dialog)
        options_frame.pack(pady=10)

        # 创建单选按钮
        for i, days in enumerate(days_options):
            rb = ttk.Radiobutton(options_frame, text=f"{days}天", variable=selected_days, value=days)
            rb.grid(row=0, column=i, padx=5)

        # 创建按钮框架
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=10)

        result: dict[str, bool | int] = {"confirmed": False, "days": 0}

        ttk.Button(
            button_frame,
            text="确定",
            command=lambda: self.__on_dialog_confirm(dialog, selected_days, result)
        ).pack(side=tk.LEFT, padx=10)

        ttk.Button(
            button_frame,
            text="取消",
            command=lambda: self.__on_dialog_cancel(dialog, result)
        ).pack(side=tk.LEFT, padx=10)

        # 等待对话框关闭
        self.__root.wait_window(dialog)

        # 返回用户选择的天数，如果取消则返回None
        return result.get("days") if result.get("confirmed") else None

    @staticmethod
    def __on_dialog_confirm(dialog: tk.Toplevel, selected_days: tk.IntVar, result: dict[str, bool | int]) -> None:
        """处理对话框确认"""
        result["confirmed"] = True
        result["days"] = selected_days.get()
        dialog.destroy()

    @staticmethod
    def __on_dialog_cancel(dialog: tk.Toplevel, result: dict[str, bool | int]) -> None:
        """处理对话框取消"""
        result["confirmed"] = False
        dialog.destroy()

    def __handle_cleanup_result(self, cleanup_result) -> None:
        """处理清理结果"""
        message = cleanup_result.msg
        self.__ui_state_mgr.update_status(message)
        if cleanup_result.is_success():
            messagebox.showinfo("清理完成", message)
        else:
            messagebox.showerror("清理失败", message)


    """Utils"""
    def __on_key_loaded(self, key_manager: SingleKeyManager | None) -> None:
        """密钥加载成功时的回调"""
        if key_manager is None or not hasattr(key_manager, "private_key"):
            self.__ui_state_mgr.update_status("密钥管理器无效，无法创建数字签名实例")
            self.__current_km = None
            self.__multi_km.current_key_id = None

            # 通知KeyManagementTab加载失败
            if self.__key_tab:
                self.__key_tab.loaded_key_id = None
            return

        try:
            key_id = getattr(key_manager, "key_id", None)
            if key_id is None:
                key_id = self.__multi_km.current_key_id

            if key_id:
                self.__multi_km.current_key_id = key_id
                save_result = self.__multi_km.save_keys_config()
                if not save_result.is_success():
                    messagebox.showerror("密钥配置保存失败", f"密钥加载成功但配置保存失败：{save_result.msg}")
                    
                # 通知KeyManagementTab密钥已真正加载
                if self.__key_tab:
                    self.__key_tab.loaded_key_id = key_id

            self.__current_km = key_manager
            self.__update_all_tabs_key_manager()

            self.__ui_state_mgr.update_status(f"密钥对 '{key_id}' 已加载并准备就绪")
            self.__update_directory_info()

        except Exception as e:
            self.__ui_state_mgr.update_status(f"创建数字签名实例失败: {e}")
            self.__current_km = None
            self.__multi_km.current_key_id = None

            # 通知KeyManagementTab加载失败
            if self.__key_tab:
                self.__key_tab.loaded_key_id = None

    def __update_all_tabs_key_manager(self) -> None:
        """更新所有标签页的密钥管理器"""
        self.__current_km = cast(SingleKeyManager, self.__current_km)
        if self.__text_tab:
            self.__text_tab.km = self.__current_km

        if self.__file_tab:
            self.__file_tab.km = self.__current_km

    def __reload_current_key(self, click_reload_btn: bool = False) -> None:
        """重新加载当前密钥"""
        if self.__multi_km.current_key_id is None:
            if click_reload_btn:
                messagebox.showwarning("警告", "没有加载的密钥对")
            return

        # 使用统一的KeyLoader加载密钥
        reload_result = self.__key_loader.load_key(self.__multi_km.current_key_id)
        
        if reload_result.is_success():
            return
        
        if reload_result.status == Status.CANCEL_INPUT:
            messagebox.showinfo("取消加载", reload_result.msg)
            return
        
        messagebox.showerror("加载失败", f"重新加载密钥失败:\n\n{reload_result.msg}")

    def __handle_status_update(self, message: str) -> None:
        """处理状态更新"""
        if self.__status_label:
            self.__status_label.config(text=message)

    def __handle_result_show(self, text: str, tab_type: str) -> None:
        """处理结果显示"""
        if tab_type == "file" and hasattr(self.__file_tab, "result_text"):
            cast(tk.Text, cast(FileSigningTab, self.__file_tab).result_text).delete("1.0", tk.END)
            cast(tk.Text, cast(FileSigningTab, self.__file_tab).result_text).insert("1.0", text)
        elif tab_type == "text" and hasattr(self.__text_tab, "result_text"):
            cast(tk.Text, cast(TextSigningTab, self.__text_tab).result_text).delete("1.0", tk.END)
            cast(tk.Text, cast(TextSigningTab, self.__text_tab).result_text).insert("1.0", text)

    def __set_current_key_manager(self, key_manager: SingleKeyManager) -> None:
        """设置当前密钥管理器"""
        if not hasattr(key_manager, "private_key"):
            self.__current_km = None
            return

        try:
            # 创建数字签名实例
            self.__current_km = key_manager

            # 更新所有标签页
            self.__update_all_tabs_key_manager()

            # 更新状态
            key_id = getattr(key_manager, "key_id", "未知")
            self.__ui_state_mgr.update_status(f"密钥对 '{key_id}' 已加载并准备就绪")
            self.__update_directory_info()

        except Exception as e:
            messagebox.showerror("数字签名实例设置失败", f"{e}")
            self.__current_km = None

    @staticmethod
    def __get_constants():
        return (
            f"{KeyType.PRIVATE.value}_",
            f"{KeyType.PUBLIC.value}_",
            FileType.KEY.value,
            FileType.TEXT.value,
            FileType.SIGNATURE.value
        )
        