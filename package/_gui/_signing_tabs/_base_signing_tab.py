# package/_gui/_signing_tabs/_base_signing_tab.py
"""签名标签页基类"""
import tkinter as tk
from abc import ABC, abstractmethod
from pathlib import Path
from tkinter import ttk, messagebox
from tkinter.filedialog import askopenfilename
from tkinter.scrolledtext import ScrolledText
from typing import Callable, TypedDict, TYPE_CHECKING

from ..._utils.constants import BASE_DIR
from ..._utils.enums import Level
from ..._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from ..._core.keys.managers import SingleKeyManager
    from ..._utils.ui_state_manager import UIStateManager


class ButtonConfig(TypedDict):
    """
    操作按钮配置
    
    Attributes:
        text (str): 按钮显示文本
        command (Callable[[], None]): 按钮点击回调函数
    """
    text: str
    command: Callable[[], None]

class BaseSigningTab(ABC):
    """签名标签页基类"""
    def __init__(self, parent: tk.Widget, tab_type: str) -> None:
        self.__km: SingleKeyManager | None = None
        self.__tab_type: str = tab_type
        self.__result_text: tk.Text | None = None

        self._parent: tk.Widget = parent
        self._ui_state_mgr: UIStateManager = get_ui_state_manager()


    @property
    def result_text(self) -> tk.Text | None:
        return self.__result_text

    @property
    def km(self) -> SingleKeyManager | None:
        return self.__km

    @km.setter
    def km(self, km: SingleKeyManager) -> None:
        self.__km = km


    """Interfaces for subclasses to implement"""
    @property
    @abstractmethod
    def _content_label(self) -> tuple[str, str]:
        """内容类型的显示名称"""
        ...

    @property
    @abstractmethod
    def _editor_row_weight(self) -> int:
        """编辑区行权重，文件=0，文本=1"""
        ...

    @property
    @abstractmethod
    def _get_extra_buttons(self) -> list[ButtonConfig]:
        """子类注入自己的特有按钮"""
        ...
    
    
    """not property"""
    @abstractmethod
    def _create_editor(self) -> None:
        """创建核心编辑区域"""
        ...
    
    @abstractmethod
    def _get_content(self) -> str:
        """获取文本内容"""
        ...

    @abstractmethod
    def _sign_content(self, km: SingleKeyManager, content: str) -> None:
        """
        签名文本或文件
        
        Args:
            km (SingleKeyManager): 密钥管理器
            content (str): 待签名内容或文件路径
        """
        ...

    @abstractmethod
    def _verify_content(self, km: SingleKeyManager, content: str) -> None:
        """
        验证文本或文件签名
        
        Args:
            km (SingleKeyManager): 密钥管理器
            content (str): 待验证内容或文件路径
        """
        ...


    """protected methods -- used by subclasses"""
    def _setup_ui(self) -> None:
        """设置用户界面"""
        self._parent.columnconfigure(0, weight=1)
        self.__dynamically_adjust_layout()
        self._create_editor()
        self.__create_operation_panel(1, self._content_label[1])
        self.__create_result_area(2)

    def _handle_sign_success(self, signature_file: str, content_path: str, content_hash: str) -> None:
        """
        处理签名成功
        
        Args:
            signature_file (str): 生成的签名文件路径
            content_path (str): 被签名内容的路径
            content_hash (str): 被签名内容的哈希值
        """
        self._ui_state_mgr.update_status(f"{self.__tab_type.capitalize()}签名成功")

        result_text = (
            f"{self.__tab_type.capitalize()}签名成功！\n\n"
            f"{self._content_label[0]}路径: {content_path}\n"
            f"签名文件: {str(Path(signature_file).as_posix())}\n"
            f"{self._content_label[1]}哈希: {content_hash}"
        )
        self._show_result(result_text)
        self.__show_info(f"{self.__tab_type.capitalize()}签名成功！")

    def _handle_verify_success(self,
                               is_valid: bool,
                               signature_path: str,
                               content_path: str,
                               content_hash: str) -> None:
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
                "请先加载密钥对！\n\n请在\"密钥管理\"标签页中选择并加载一个密钥对，然后再进行操作。"
            )
            return None

        if self.__km.private_key is None or self.__km.public_key is None:
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

    def _show_result(self, text: str, level: Level = Level.INFO, log: bool = False) -> None:
        """
        显示结果
        
        Args:
            text (str): 结果文本
        """
        assert self.__result_text is not None, "结果显示区未初始化"
        
        self.__result_text.delete("1.0", tk.END)
        self.__result_text.insert("1.0", text)

        self._ui_state_mgr.show_result(text, self.__tab_type, level, log=log)

    def _show_warning(self, message: str) -> None:
        """
        显示警告信息
        
        Args:
            message (str): 警告消息文本
        """
        messagebox.showwarning("警告", message)
        self._ui_state_mgr.update_status(f"警告: {message}", Level.WARNING, log=True)

    def _handle_operation_error(self, operation_name: str, error: str) -> None:
        """
        统一处理操作错误
        
        Args:
            operation_name (str): 操作名称（如“签名”或“验证”）
            error (Exception): 异常对象
        """
        error_message = f"{operation_name}失败: {error}"
        messagebox.showerror("错误", error_message)
        self._ui_state_mgr.update_status(f"{operation_name}失败", Level.ERROR, log=True)

    @staticmethod
    def _browse_file(title: str = "选择文件",
                     initial_dir: str | None = None, 
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
        
        return Path(file_path).as_posix()


    """private methods"""
    def __show_info(self, message: str) -> None:
        """显示信息 - 统一状态管理"""
        messagebox.showinfo("信息", message)
        self._ui_state_mgr.update_status(message)

    def __dynamically_adjust_layout(self) -> None:
        """动态布局调整"""
        self._parent.rowconfigure(0, weight=self._editor_row_weight)
        self._parent.rowconfigure(1, weight=0)
        self._parent.rowconfigure(2, weight=1)

    def __create_operation_panel(self, row: int, title: str) -> None:
        """创建操作面板"""
        op_frame = ttk.LabelFrame(self._parent, text="操作面板", padding=5)
        op_frame.grid(row=row, column=0, sticky=tk.EW, pady=2)
        op_frame.columnconfigure(0, weight=1)

        button_row: ttk.Frame = ttk.Frame(op_frame)
        button_row.pack(fill=tk.X, expand=True)
        buttons = self.__get_operation_buttons(title)

        for button_config in buttons:
            ttk.Button(
                button_row,
                text=str(button_config["text"]),
                command=button_config["command"]
            ).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

    def __create_result_area(self, row: int) -> None:
        """创建结果区域"""
        result_frame = ttk.LabelFrame(self._parent, text="操作结果", padding=5)
        result_frame.grid(row=row, column=0, sticky=tk.NSEW, pady=2)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        self.__result_text = ScrolledText(result_frame, height=8, font=("Consolas", 9), wrap=tk.WORD)
        self.__result_text.grid(row=0, column=0, sticky=tk.NSEW)

    def __show_result_text(self, is_valid: bool, content_path: str, signature_path: str, content_hash: str) -> None:
        """返回结果字符串"""
        msg: list[str] = ["成功", "完整且未被篡改"] if is_valid else ["失败", "可能已被篡改"]
        error = f"{"" if is_valid else "\n也可能使用了错误的签名文件或公钥文件。"}"
        level = Level.INFO if is_valid else Level.WARNING
        log = False if is_valid else True

        self._ui_state_mgr.update_status(f"{self.__tab_type.capitalize()}验证{msg[0]}", level, log=log)
        result_text = (
            f"签名验证{msg[0]}！\n\n"
            f"{self._content_label[0]}路径: {content_path}\n"
            f"签名文件: {signature_path}\n"
            f"{self._content_label[1]}哈希: {content_hash}\n\n"
            f"{self._content_label[0]}{msg[1]}。{error}"
        )

        self._show_result(result_text, level, log=log)

    def __get_operation_buttons(self, title: str) -> list:
        """获取操作按钮配置"""
        return [
            {"text": f"签名{title}", "command": lambda: self.__sign_or_verify(mode="sign")},
            {"text": f"验证{title}签名", "command": lambda: self.__sign_or_verify(mode="verify")},
            *self._get_extra_buttons,
            {"text": "清空结果", "command": self.__clear_results}
        ]

    def __sign_or_verify(self, mode: str) -> None:
        """签名或验证内容"""
        validation_result = self._validate_km_and_content()
        if validation_result is None:
            return

        km: SingleKeyManager
        km, content = validation_result
        
        if mode == "sign":
            self._sign_content(km, content)
        else:
            self._verify_content(km, content)

    def __clear_results(self) -> None:
        """清空结果显示区域"""
        assert self.__result_text is not None, "结果显示区未初始化"
        
        self.__result_text.delete("1.0", tk.END)
        self._ui_state_mgr.update_status("结果已清空")
