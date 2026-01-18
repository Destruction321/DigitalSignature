# package/_gui/tabs/signing_tabs/text_signing_tab.py
"""文本签名标签页，实现核心接口和内容编辑接口"""
import tkinter as tk
from pathlib import Path
from tkinter import messagebox
from tkinter.filedialog import asksaveasfilename
from tkinter.ttk import LabelFrame
from datetime import datetime
from typing import Callable, TYPE_CHECKING

from ._base_signing_tab import BaseSigningTab
from ..._core import signature
from ..._utils import DirType, get_path

if TYPE_CHECKING:
    from ..._core.keys.managers import SingleKeyManager


class TextSigningTab(BaseSigningTab):
    """文本签名标签页，实现核心接口和内容编辑接口"""
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, "text")
        self.__text_editor: tk.Text | None = None
        self._setup_ui()


    def _get_content(self) -> str:
        if self.__text_editor:
            return self.__text_editor.get("1.0", tk.END).strip()
        
        return ""

    def _sign_content(self, km: SingleKeyManager, content: str) -> None:
        try:
            temp_file = Path(self.__create_temp_file(content, "text"))
            signature_file = signature.sign_file(km, temp_file)
            text_hash = self._get_file_hash(str(temp_file))

            self._handle_sign_success(signature_file.data, "当前编辑文本", text_hash)
            temp_file.unlink()

        except Exception as e:
            self._handle_operation_error("签名", e)

    def _verify_content(self, km: SingleKeyManager, content: str) -> None:
        signature_path = self._browse_file(
            title="选择签名文件",
            initial_dir=get_path(DirType.SIGNATURES),
            file_types=[("签名文件", "*.sig"), ("所有文件", "*.*")],
        )
        if signature_path is None:
            return

        try:
            temp_file = self.__create_temp_file(content, "verify")
            is_valid = signature.verify_signature(km, temp_file, Path(signature_path))
            text_hash = self._get_file_hash(temp_file)

            self._handle_verify_success(is_valid.is_success(), signature_path, "当前编辑文本", text_hash)
            Path(temp_file).unlink()

        except Exception as e:
            self._handle_operation_error("验证", e)

    def _clear_content(self) -> None:
        if self.__text_editor:
            self.__text_editor.delete("1.0", tk.END)
            self._ui_state_mgr.update_status("文本已清空")

    def _save_content(self) -> None:
        content = self._get_content()
        valid, message = (False, "文本内容为空") if not content or not content.strip() else (True, "")
        if not valid:
            self._show_warning(message)
            return

        file_name = f"document_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt"

        self.__save_text_file(
            content=content,
            file_name=file_name,
            callback=self.__on_save_success
        )


    """private methods"""
    def __on_save_success(self, file_path: str) -> None:
        """保存文本成功回调"""
        self._ui_state_mgr.update_status(f"文本已保存: {file_path}")
            
    def _create_editor(self) -> None:
        """创建文本编辑区域"""
        editor_frame = LabelFrame(self._parent, text="文本编辑", padding=5)
        editor_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=2)
        editor_frame.columnconfigure(0, weight=1)
        editor_frame.rowconfigure(0, weight=1)

        self.__text_editor = self._create_scrolled_text(
            editor_frame,
            height=10,
            font=("Consolas", 10)
        )
        self.__text_editor.grid(row=0, column=0, sticky=tk.NSEW)

        default_text = """哈尔滨工程大学 - 数据安全课程设计
数字签名系统

学号：[请输入你的学号]
姓名：[请输入你的姓名]
专业：计算机科学与技术
日期：2025年秋季学期

您可以在此编辑任意文本内容，然后进行数字签名操作。"""
        self.__text_editor.insert("1.0", default_text)

    def __create_temp_file(self, content: str, prefix: str | None = None) -> str:
        """临时文件创建"""
        temp = DirType.TEMP.value
        timestamp = datetime.now().strftime("%H%M%S_%f")
        file_name = f"{temp}_{prefix}_{timestamp}.txt" if prefix else f"{temp}_{timestamp}.txt"

        file_path = get_path(DirType.TEMP, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        return file_path

    @staticmethod
    def __save_text_file(content: str, file_name: str = "document.txt",
                         callback: Callable[[str], None] | None = None) -> str | None:
        """保存文本文件"""
        if not content:
            messagebox.showwarning("警告", "文本内容为空")
            return None

        file_path = asksaveasfilename(
            title="保存文本文件",
            defaultextension=".txt",
            initialfile=file_name,
            initialdir=get_path(DirType.TEXTS),
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )

        if not file_path:
            return None

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            if callback:
                callback(file_path)
            
            return file_path
        except Exception as e:
            messagebox.showerror("错误", f"保存失败: {e}")
            return None
