# package/_gui/_signing_tabs/_file_signing_tab.py
"""文件签名标签页"""
import tkinter as tk
from hashlib import sha256
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

from ._base_signing_tab import BaseSigningTab
from ..._core import signature
from ..._utils.enums import DirType, FileType
from ..._utils.result import Status, Result
from ..._utils.tools import get_path

if TYPE_CHECKING:
    from ..._core.keys.managers import SingleKeyManager


class FileSigningTab(BaseSigningTab):
    """文件签名标签页"""
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
                file_types=[("所有文件", "*.*"), ("文本文件", f"*{FileType.TEXT.value}"), ("文档", "*.docx *.pdf")],
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
                file_types=[("签名文件", f"*{FileType.SIGNATURE.value}"), ("所有文件", "*.*")],
                callback=self.__on_signature_selected
            )
        ).grid(row=1, column=2, padx=5, pady=5)

    def _get_content(self) -> str:
        assert self.__file_path_entry is not None, "文件选择区未初始化"
        return self.__file_path_entry.get().strip()

    def _sign_content(self, km: SingleKeyManager, content: str) -> None:
        if not self.__validate_file_exists(content):
            return
        
        try:
            signature_file = signature.sign_file(km, Path(content))
            file_hash = sha256(Path(content).read_bytes()).hexdigest()
            self.__update_signature_path(signature_file.data)
            self._handle_sign_success(signature_file.data, content, file_hash)

        except Exception as e:
            self._handle_operation_error("签名", str(e))

    def _verify_content(self, km: SingleKeyManager, content: str) -> None:
        assert self.__signature_path_entry is not None, "签名路径输入框未初始化"
        
        if not self.__validate_file_exists(content):
            return
        
        signature_path = self.__signature_path_entry.get().strip()
        if not self.__validate_file_exists(signature_path, "签名"):
            return

        try:
            is_valid = signature.verify_signature(km, content, Path(signature_path))
            file_hash = sha256(Path(content).read_bytes()).hexdigest()
            self._handle_verify_success(is_valid.is_success, signature_path, content, file_hash)

        except Exception as e:
            self._handle_operation_error("验证", str(e))

    
    """private methods"""
    def __show_hash(self) -> None:
        assert self.__file_path_entry is not None, "文件路径输入框未初始化"
        
        file_path = self.__file_path_entry.get().strip()
        if not self.__validate_file_exists(file_path):
            return

        try:
            file_hash_info = self.__get_file_hash_info(Path(file_path))
            if not file_hash_info.is_success:
                self._handle_operation_error("获取文件哈希", file_hash_info.msg)
                return
            
            file_hash_info = file_hash_info.data
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
            self._handle_operation_error("获取文件哈希", str(e))

    def __update_signature_path(self, signature_path: str) -> None:
        assert self.__signature_path_entry is not None, "签名路径输入框未初始化"
        
        self.__signature_path_entry.delete(0, tk.END)
        self.__signature_path_entry.insert(0, signature_path)

    def __on_file_selected(self, file_path: str) -> None:
        """选择文件"""
        assert self.__file_path_entry is not None, "文件路径输入框未初始化"

        self.__file_path_entry.delete(0, tk.END)
        self.__file_path_entry.insert(0, file_path)

    def __on_signature_selected(self, file_path: str) -> None:
        """选择签名文件"""
        assert self.__signature_path_entry is not None, "签名路径输入框未初始化"

        self.__signature_path_entry.delete(0, tk.END)
        self.__signature_path_entry.insert(0, file_path)

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
    
    def __get_file_hash_info(self, file_path: Path) -> Result:
        """获取文件哈希信息"""
        if not file_path.exists():
            return Result(status=Status.FILE_NOT_FOUND)

        file_size = file_path.stat().st_size
        try:
            sha256_hash = sha256(file_path.read_bytes()).hexdigest()
            result = {
                "path": file_path.as_posix(),
                "size": file_size,
                "sha256": sha256_hash,
                "size_formatted": f"{file_size} 字节"
            }
            return Result(status=Status.SUCCESS, data=result)
        
        except Exception as e:
            return Result(status=Status.FAILED, msg=f"哈希过程出现未知错误：{e}")
