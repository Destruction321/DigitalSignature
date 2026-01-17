# package/_gui/tabs/_base_signing_tab.py
"""签名标签页基类"""
import tkinter as tk
from pathlib import Path
from abc import ABC, abstractmethod
from tkinter import ttk, messagebox
from tkinter.filedialog import askopenfilename
from tkinter.scrolledtext import ScrolledText
from typing import Callable, TYPE_CHECKING

from cryptography.hazmat.primitives.hashes import Hash, SHA256

from ...._utils.ui_state_manager import get_ui_state_manager
from ...._utils import BASE_DIR, Status, Result

if TYPE_CHECKING:
    from ...._core.keys.manager import SingleKeyManager


class BaseSigningTab(ABC):
    """签名标签页基类"""
    def __init__(self, parent: tk.Widget, tab_type: str) -> None:
        self.__km: SingleKeyManager | None = None
        self.__tab_type: str = tab_type
        self.__result_text: tk.Text | None = None

        self._ui_state_mgr = get_ui_state_manager()
        self._parent: tk.Widget = parent


    @property
    def result_text(self) -> tk.Text | None:
        return self.__result_text

    @property
    def km(self) -> SingleKeyManager | None:
        return self.__km

    @km.setter
    def km(self, km: SingleKeyManager) -> None:
        self.__km = km


    """核心接口"""
    @abstractmethod
    def _create_editor(self) -> None:
        """创建核心编辑区域"""
        pass
    
    @abstractmethod
    def _get_content(self) -> str :
        """获取文本内容"""
        pass

    @abstractmethod
    def _sign_content(self, km: SingleKeyManager, content: str) -> None:
        """
        签名文本或文件
        
        Args:
            km (SingleKeyManager): 密钥管理器
            content (str): 待签名内容或文件路径
        """
        pass

    @abstractmethod
    def _verify_content(self, km: SingleKeyManager, content: str) -> None:
        """
        验证文本或文件签名
        
        Args:
            km (SingleKeyManager): 密钥管理器
            content (str): 待验证内容或文件路径
        """
        pass


    """可选接口"""
    def _update_signature_path(self, _signature_path: str) -> None:
        """更新签名路径显示 - 文件签名专用"""
        pass

    def _show_hash(self) -> None:
        """显示哈希值 - 文件签名专用"""
        pass

    def _clear_content(self) -> None:
        """清空内容 - 文本签名专用"""
        pass

    def _save_content(self) -> None:
        """保存内容 - 文本签名专用"""
        pass


    """protected methods -- used by subclasses"""
    def _setup_ui(self) -> None:
        """设置用户界面"""
        title = "文件" if self.__tab_type == "file" else "文本"
        self._parent.columnconfigure(0, weight=1)
        self.__dynamically_adjust_layout()
        self._create_editor()
        self.__create_operation_panel(1, title)
        self.__create_result_area(2)

    def _sign_or_verify(self, mode: str) -> None:
        """
        签名或验证内容
        
        Args:
            mode (str): 操作模式 ("sign"=签名, "verify"=验证)
        """
        validation_result = self._validate_km_and_content()
        if validation_result is None:
            return

        km: SingleKeyManager
        km, content = validation_result
        
        if mode == "sign":
            self._sign_content(km, content)
        else:
            self._verify_content(km, content)

    def _handle_sign_success(self, signature_file: str, content_path: str, content_hash: str) -> None:
        """
        处理签名成功
        
        Args:
            signature_file (str): 生成的签名文件路径
            content_path (str): 被签名内容的路径
            content_hash (str): 被签名内容的哈希值
        """
        self._ui_state_mgr.update_status(f"{self.__tab_type.capitalize()}签名成功")
        self._update_signature_path(signature_file)

        result_text = (
            f"{self.__tab_type.capitalize()}签名成功！\n\n"
            f"{"文件" if self.__tab_type == "file" else "内容"}路径: {content_path}\n"
            f"签名文件: {signature_file}\n"
            f"{"文件" if self.__tab_type == "file" else "文本"}哈希: {content_hash}"
        )
        self._show_result(result_text)
        self.__show_info(f"{self.__tab_type.capitalize()}签名成功！")

    def _handle_verify_success(self, is_valid: bool, signature_path: str, content_path: str, content_hash: str) -> None:
        """
        处理验证结果
        
        Args:
            is_valid (bool): 签名是否有效（True=有效，False=无效）
            signature_path (str): 签名文件路径
            content_path (str): 被验证内容的路径
            content_hash (str): 被验证内容的哈希值
        """
        self.__show_result_text(is_valid, content_path, signature_path, content_hash)

        if is_valid:
            self.__show_info("签名验证成功！")
        else:
            self._show_warning("签名验证失败！")

    def _validate_km_and_content(self) -> tuple[SingleKeyManager, str] | None:
        """
        验证密钥管理器和内容
        
        Returns:
            (key_manager, content) (tuple[SingleKeyManager, str] | None):
            返回验证通过的密钥管理器和内容，否则返回None
        """
        if self.__km is None:
            self._show_warning(
                '请先加载密钥对！\n\n请在"密钥管理"标签页中选择并加载一个密钥对，然后再进行操作。'
            )
            return None

        if not hasattr(self.__km, "private_key") or not hasattr(self.__km, "public_key"):
            self._show_warning(
                "密钥管理器不完整！\n\n请确保密钥对正确加载，并且包含必要的公钥和私钥。"
            )
            return None

        # 验证内容
        content = self._get_content()

        valid, message = (
            (False, f"{self.__tab_type.capitalize()}内容为空")
            if not content or not content.strip()
            else (True, "")
        )

        if not valid:
            self._show_warning(str(message))
            return None

        return self.__km, content

    def _show_result(self, text: str) -> None:
        """
        显示结果
        
        Args:
            text (str): 结果文本
        """
        if self.__result_text:
            self.__result_text.delete("1.0", tk.END)
            self.__result_text.insert("1.0", text)

        self._ui_state_mgr.show_result(text, self.__tab_type)

    def _show_warning(self, message: str) -> None:
        """显示警告信息 - 统一状态管理"""
        messagebox.showwarning("警告", message)
        self._ui_state_mgr.update_status(f"警告: {message}")

    @staticmethod
    def _validate_file_exists(file_path: str, file_description: str = "") -> Result:
        """
        验证文件是否存在
        
        Args:
            file_path (str): 文件路径
            file_description (str): 文件描述（用于错误消息）

        Returns:
            (status, error) (tuple[bool, str]): 返回验证结果和错误消息
        """
        if not file_path or not file_path.strip():
            message = f"请选择有效的{file_description}文件"
            return Result(status=Status.FILE_NOT_FOUND, msg=message)

        if not Path(file_path).exists():
            message = f"{file_description}文件不存在: {file_path}"
            return Result(status=Status.FILE_NOT_FOUND, msg=message)

        if not Path(file_path).is_file():
            message = f"{file_description}文件不是有效的文件: {file_path}"
            return Result(status=Status.FILE_NOT_FOUND, msg=message)

        return Result(status=Status.SUCCESS)

    def _handle_operation_error(self, operation_name: str, error: Exception) -> None:
        """
        统一处理操作错误
        
        Args:
            operation_name (str): 操作名称（如“签名”或“验证”）
            error (Exception): 异常对象
        """
        error_message = f"{operation_name}失败: {error}"
        messagebox.showerror("错误", error_message)
        self._ui_state_mgr.update_status(f"{operation_name}失败")

    @staticmethod
    def _browse_file(title: str = "选择文件", initial_dir: str | None = None, 
                     file_types: list[tuple[str, str]] | None = None, 
                     callback: Callable[[str], None] | None = None) -> str:
        """
        通用文件浏览方法
        
        Args:
            title (str): 对话框标题
            initial_dir (str | None): 初始目录
            file_types (list[tuple[str, str]] | None): 可选的文件类型过滤器
            callback (Callable[[str], None] | None): 选择文件后的回调函数

        Returns:
            file_path (str | None): 选择的文件路径或None
        """
        # 设置默认初始目录
        if initial_dir is None:
            initial_dir = BASE_DIR
        
        # 设置默认文件类型
        if file_types is None:
            file_types = [("所有文件", "*.*")]
        
        # 显示文件选择对话框
        file_path = askopenfilename(
            title=title,
            initialdir=initial_dir,
            filetypes=file_types
        )
        
        # 处理回调
        if file_path and callback:
            callback(file_path)
        
        return file_path

    @staticmethod
    def _get_file_hash(file_path: str) -> str:
        """
        获取文件的SHA-256哈希值
        
        Args:
            file_path (str): 文件路径
            
        Returns:
            file_hash (str): 文件的SHA-256哈希值（十六进制字符串）
        """
        with open(file_path, "rb") as f:
            g_data = f.read()

        digest = Hash(SHA256())
        digest.update(g_data)
        g_file_hash = digest.finalize()

        return g_file_hash.hex()

    @staticmethod
    def _create_scrolled_text(parent: tk.Widget, height: int = 8,
                              font: tuple[str, int] = ("Consolas", 9),
                              wrap: str = tk.WORD) -> ScrolledText:
        """
        创建滚动文本框
        
        Args:
            parent (tk.Widget): 父组件
            height (int): 高度（行数），默认为8
            font (tuple[str, int]): 字体
            wrap (str): 换行方式

        Returns:
            scrolledtext (ScrolledText): 滚动文本框组件
        """
        return ScrolledText(
            parent,
            height=height,
            font=font,
            wrap=wrap
        )


    """private methods"""
    def __show_info(self, message: str) -> None:
        """显示信息 - 统一状态管理"""
        messagebox.showinfo("信息", message)
        self._ui_state_mgr.update_status(message)

    def __dynamically_adjust_layout(self) -> None:
        """动态布局调整"""
        self._parent.rowconfigure(0, weight=0 if self.__tab_type == "file" else 1)
        self._parent.rowconfigure(1, weight=0)
        self._parent.rowconfigure(2, weight=1)

    def __create_operation_panel(self, row: int, title: str) -> None:
        """创建操作面板"""
        op_frame = ttk.LabelFrame(self._parent, text="操作面板", padding=5)
        op_frame.grid(row=row, column=0, sticky=tk.EW, pady=2)
        op_frame.columnconfigure(0, weight=1)

        buttons = self.__get_operation_buttons(title)
        self.__create_button_row(op_frame, buttons)

    @staticmethod
    def __create_button_row(parent: tk.Widget, buttons: list[dict[str, Callable[[], None]]]) -> ttk.Frame:
        """创建按钮行"""
        button_row: ttk.Frame = ttk.Frame(parent)
        button_row.pack(fill=tk.X, expand=True)

        for button_config in buttons:
            ttk.Button(
                button_row,
                text=str(button_config["text"]),
                command=button_config["command"]
            ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        return button_row

    def __create_result_area(self, row: int) -> None:
        """创建结果区域"""
        result_frame = ttk.LabelFrame(self._parent, text="操作结果", padding=5)
        result_frame.grid(row=row, column=0, sticky=tk.NSEW, pady=2)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.__result_text = self._create_scrolled_text(result_frame)
        self.__result_text.grid(row=0, column=0, sticky=tk.NSEW)

    def __show_result_text(self, is_valid: bool, content_path: str, signature_path: str, content_hash: str) -> None:
        """返回结果字符串"""
        msg: list[str] = ["成功", "完整且未被篡改"] if is_valid else ["失败", "可能已被篡改"]

        self._ui_state_mgr.update_status(f"{self.__tab_type.capitalize()}验证{msg[0]}")
        result_text = (
            f"签名验证{msg[0]}！\n\n"
            f"{"文件" if self.__tab_type == "file" else "内容"}路径: {content_path}\n"
            f"签名文件: {signature_path}\n"
            f"{"文件" if self.__tab_type == "file" else "文本"}哈希: {content_hash}\n\n"
            f"{"文件" if self.__tab_type == "file" else "内容"}{msg[1]}。\n也可能使用了错误的签名文件或公钥文件。"
        )

        self._show_result(result_text)

    def __get_operation_buttons(self, title: str) -> list:
        """获取操作按钮配置"""
        buttons = [
            {"text": f"签名{title}", "command": lambda: self._sign_or_verify(mode="sign")},
            {"text": f"验证{title}签名", "command": lambda: self._sign_or_verify(mode="verify")},
            {"text": "清空结果", "command": self.__clear_results}
        ]

        if self.__tab_type == "file":
            buttons.insert(2, {"text": "显示哈希", "command": self._show_hash})
        else:
            buttons.insert(2, {"text": "清空文本", "command": self._clear_content})
            buttons.insert(3, {"text": "保存文本", "command": self._save_content})

        return buttons

    def __clear_results(self) -> None:
        """清空结果显示区域"""
        if self.__result_text:
            self.__result_text.delete("1.0", tk.END)
        self._ui_state_mgr.update_status("结果已清空")
