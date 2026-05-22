# package/_gui/_signing_tabs/_file_signing_tab.py
"""文件签名标签页"""
import tkinter as tk
from hashlib import sha256
from pathlib import Path
from tkinter import ttk
from typing import TYPE_CHECKING

from ._base_signing_tab import BaseSigningTab, ButtonConfig
from ..._core import signature
from ..._gui.progress_dialog import ProgressDialog
from ..._utils.enums import DirType, FileType
from ..._utils.result import Status, Result
from ..._utils.tools import get_path
from ..._utils.worker import Worker

if TYPE_CHECKING:
    from ..._core.keys.managers import SingleKeyManager


_CHUNK_SIZE = 1024 * 1024  # 1 MB


def _compute_file_hash(file_path: Path) -> str:
    """分块计算文件 SHA-256，避免一次性读入大文件"""
    h = sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(_CHUNK_SIZE):
            h.update(chunk)
    return h.hexdigest()


class _FileSignWorker(Worker):
    """在后台线程对文件签名，分块读取时报告进度"""
    def __init__(self, km: SingleKeyManager, file_path: Path) -> None:
        super().__init__()
        self.__km = km
        self.__file_path = file_path

    def do_work(self) -> Result:
        result = signature.sign_file(
            key_manager=self.__km,
            file_path=self.__file_path,
            progress_callback=self._report_progress
        )
        if result.is_success and not self.is_cancelled:
            self._report_progress(0.95, "正在计算文件哈希...")
            file_hash = _compute_file_hash(self.__file_path)
            self._report_progress(1.0, "签名完成")
            return Result(
                status=result.status,
                data={"path": result.data, "hash": file_hash},
                msg=result.msg
            )
        return result


class _FileVerifyWorker(Worker):
    """在后台线程验证文件签名，分块读取时报告进度"""
    def __init__(self, km: SingleKeyManager, file_path: Path,
                 signature_path: Path) -> None:
        super().__init__()
        self.__km = km
        self.__file_path = file_path
        self.__signature_path = signature_path

    def do_work(self) -> Result:
        result = signature.verify_signature(
            key_manager=self.__km,
            file_path=self.__file_path,
            signature_path=self.__signature_path,
            progress_callback=self._report_progress
        )
        if result.is_success or result.status == Status.VERIFY_FAILED and not self.is_cancelled:
            self._report_progress(0.95, "正在计算文件哈希...")
            file_hash = _compute_file_hash(self.__file_path)
            self._report_progress(1.0, "验证完成")
            return Result(
                status=result.status,
                data={"hash": file_hash},
                msg=result.msg
            )
            
        return result


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
    def _get_extra_buttons(self) -> list[ButtonConfig]:
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
                file_types=[
                    ("所有文件", "*.*"),
                    ("文本文件", f"*{FileType.TEXT.value}"),
                    ("文档", "*.doc *.docx *.pdf")
                ],
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
        return Path(self.__file_path_entry.get().strip()).as_posix()

    def _sign_content(self, km: SingleKeyManager, content: str) -> None:
        if not self.__validate_file_exists(content):
            return

        file_path = Path(content)
        dialog = ProgressDialog(
            parent=self._parent,
            title="文件签名",
            message="正在对文件进行数字签名...",
        )
        worker = _FileSignWorker(km, file_path)
        result = dialog.run(worker)

        if result.is_success:
            data = result.data
            signature_path = Path(data["path"]).as_posix()
            self.__update_signature_path(signature_path)
            self._handle_sign_success(signature_path, content, data["hash"])
            return

        if result.status != Status.CANCEL_INPUT:
            self._handle_operation_error("签名", result.msg)

    def _verify_content(self, km: SingleKeyManager, content: str) -> None:
        assert self.__signature_path_entry is not None, "签名路径输入框未初始化"

        if not self.__validate_file_exists(content):
            return

        signature_path = Path(self.__signature_path_entry.get().strip()).as_posix()
        if not self.__validate_file_exists(signature_path, "签名"):
            return

        file_path = Path(content)
        dialog = ProgressDialog(
            parent=self._parent,
            title="签名验证",
            message="正在验证文件签名...",
        )
        worker = _FileVerifyWorker(km, file_path, Path(signature_path))
        result = dialog.run(worker)

        if result.is_success:
            self._handle_verify_success(True, signature_path, content, result.data["hash"])
            return

        if result.status == Status.VERIFY_FAILED:
            self._handle_verify_success(False, signature_path, content, result.data["hash"])
            return

        if result.status != Status.CANCEL_INPUT:
            self._handle_operation_error("验证", result.msg)

    
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
        self.__signature_path_entry.insert(0, str(Path(file_path).as_posix()))

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
