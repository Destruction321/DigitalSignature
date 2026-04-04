# package/_gui/tabs/signing_tabs/_file_signing_tab.py
"""文件签名标签页，实现核心接口和哈希显示接口"""
import tkinter as tk
from hashlib import sha256
from pathlib import Path
from tkinter import ttk
from typing import cast, TYPE_CHECKING

from ._base_signing_tab import BaseSigningTab
from ..._core import signature
from ..._utils import DirType, get_path

if TYPE_CHECKING:
    from ..._core.keys.managers import SingleKeyManager


class FileSigningTab(BaseSigningTab):
    """文件签名标签页，实现核心接口和哈希显示接口"""
    def __init__(self, parent: tk.Widget) -> None:
        super().__init__(parent, "file")
        
        self.__file_path_entry: tk.Entry | None = None
        self.__signature_path_entry: tk.Entry | None = None

        self._setup_ui()


    @property
    def _content_label(self) -> tuple[str, str]:
        return "文件", "文件"
    
    @property
    def _editor_row_weight(self) -> int:
        return 0

    @property
    def _get_extra_buttons(self) -> list[dict]:
        return [{"text": "显示哈希", "command": self.__show_hash}]


    def _create_editor(self) -> None:
        """创建文件选择区域"""
        file_frame = ttk.LabelFrame(self._parent, text="文件操作", padding=5)
        file_frame.grid(row=0, column=0, sticky=tk.EW, pady=2)
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="文件路径:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.__file_path_entry = ttk.Entry(file_frame)
        self.__file_path_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(
            file_frame,
            text="浏览文件",
            command=lambda: self._browse_file(
                title="选择文件",
                file_types=[("所有文件", "*.*"), ("文本文件", "*.txt"), ("文档", "*.docx *.pdf")],
                callback=self.__on_file_selected
            )
        ).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(file_frame, text="签名文件:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.__signature_path_entry = ttk.Entry(file_frame)
        self.__signature_path_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(
            file_frame,
            text="浏览签名文件",
            command=lambda: self._browse_file(
                title="选择签名文件",
                initial_dir=get_path(DirType.SIGNATURES),
                file_types=[("签名文件", "*.sig"), ("所有文件", "*.*")],
                callback=self.__on_signature_selected
            )
        ).grid(row=1, column=2, padx=5, pady=5)

    def _get_content(self) -> str:
        if self.__file_path_entry:
            return self.__file_path_entry.get().strip()
        
        return ""

    def _sign_content(self, km: SingleKeyManager, content: str) -> None:
        if not self.__validate_file_exists(content):
            return
        
        try:
            signature_file = signature.sign_file(km, Path(content))
            file_hash = sha256(Path(content).read_bytes()).hexdigest()
            self.__update_signature_path(signature_file.data)
            self._handle_sign_success(signature_file.data, content, file_hash)

        except Exception as e:
            self._handle_operation_error("签名", e)

    def _verify_content(self, km: SingleKeyManager, content: str) -> None:
        if not self.__validate_file_exists(content):
            return
        
        signature_path = cast(tk.Entry, self.__signature_path_entry).get().strip()
        if not self.__validate_file_exists(signature_path, "签名"):
            return

        try:
            is_valid = signature.verify_signature(km, content, Path(signature_path))
            file_hash = sha256(Path(content).read_bytes()).hexdigest()
            self._handle_verify_success(is_valid.is_success(), signature_path, content, file_hash)

        except Exception as e:
            self._handle_operation_error("验证", e)

    
    """private methods"""
    def __show_hash(self) -> None:
        file_path = self._get_content()
        if not self.__validate_file_exists(file_path):
            return

        try:
            file_hash_info = self.__get_file_hash_info(Path(file_path))
            if isinstance(file_hash_info, Exception):
                self._handle_operation_error("获取文件哈希", file_hash_info)
                return
            
            if not file_hash_info.get("sha256"):
                self._show_warning("无法计算文件哈希")
                return

            result_text = (
                f"文件信息:\n\n"
                f"路径: {file_hash_info["path"]}\n"
                f"大小: {file_hash_info["size_formatted"]}\n"
                f"SHA-256哈希: {file_hash_info["sha256"]}"
            )
            self._show_result(result_text)
            self._ui_state_mgr.update_status("文件哈希已显示")

        except Exception as e:
            self._handle_operation_error("获取文件哈希", e)

    def __update_signature_path(self, signature_path: str) -> None:
        if self.__signature_path_entry:
            self.__signature_path_entry.delete(0, tk.END)
            self.__signature_path_entry.insert(0, signature_path)

    def __on_file_selected(self, file_path: str) -> None:
        """选择文件"""
        file_path_entry = cast(tk.Entry, self.__file_path_entry)
        file_path_entry.delete(0, tk.END)
        file_path_entry.insert(0, file_path)

    def __on_signature_selected(self, file_path: str) -> None:
        """选择签名文件"""
        signature_path_entry = cast(tk.Entry, self.__signature_path_entry)
        signature_path_entry.delete(0, tk.END)
        signature_path_entry.insert(0, file_path)

    def __validate_file_exists(self, file_path: str, file_type = "") -> bool:
        """验证文件是否存在"""
        if not file_path or not file_path.strip():
            self._show_warning(f"请选择有效的{file_type}文件")
            return False

        if not Path(file_path).exists():
            self._show_warning(f"{file_type}文件不存在: {file_path}")
            return False

        if not Path(file_path).is_file():
            self._show_warning(f"{file_type}文件不是有效的文件: {file_path}")
            return False
            
        return True
    
    def __get_file_hash_info(self, file_path: Path) -> dict | Exception:
        """获取文件哈希信息"""
        if not file_path.exists():
            return {}

        file_size = file_path.stat().st_size
        sha256_hash = sha256(file_path.read_bytes()).hexdigest()
        if isinstance(sha256_hash, Exception):
            return sha256_hash

        return {
            "path": file_path,
            "size": file_size,
            "sha256": sha256_hash,
            "size_formatted": f"{file_size} 字节"
        }
