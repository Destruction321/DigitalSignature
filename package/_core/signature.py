# package/_core/signature.py
"""数字签名核心算法"""
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256

from .._utils.enums import DirType
from .._utils.result import Status, Result
from .._utils.tools import format_size, get_path

if TYPE_CHECKING:
    from .keys.managers import SingleKeyManager

_CHUNK_SIZE = 1024 * 1024  # 1 MB

"""public methods"""
def sign_file(key_manager: SingleKeyManager,
              file_path: Path,
              signature_path: str | None = None,
              progress_callback: Callable[[float, str], None] | None = None) -> Result:
    """
    对文件进行数字签名

    Args:
        key_manager (SingleKeyManager): 密钥管理器
        file_path (Path): 待签名文件路径
        signature_path (str): 签名文件保存路径（None=默认路径）
        progress_callback: 可选进度回调 (fraction, message)

    Returns:
        signature_result (Result): 签名结果，成功时返回签名路径
    """
    if not file_path.exists() or not file_path.is_file():
        return Result(status=Status.FILE_NOT_FOUND, msg=f"待签名文件不存在: {file_path.as_posix()}")

    if key_manager is None or key_manager.private_key is None:
        return Result(status=Status.KEY_FILE_CORRUPT, msg="密钥管理器未初始化或缺少私钥")

    if signature_path is None:
        if file_path.parent == Path(get_path(DirType.TEMP)):
            signature_path = get_path(DirType.TEMP, f"{file_path.name}.sig")
        else:
            signature_path = get_path(DirType.SIGNATURES, f"{file_path.name}.sig")

    try:
        s_data = _read_with_progress(file_path, progress_callback, 0.0, 0.8)

        if progress_callback:
            progress_callback(0.85, "正在签名...")

        signature = key_manager.private_key.sign(
            s_data,
            padding.PSS(mgf=padding.MGF1(SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            SHA256()
        )

        if progress_callback:
            progress_callback(0.95, "正在保存签名...")

        with open(signature_path, "wb") as f:
            f.write(signature)

        if progress_callback:
            progress_callback(1.0, "签名完成")

        message = f"文件签名成功：{signature_path}"
        return Result(status=Status.SIGN_SUCCESS, data=signature_path, msg=message)

    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"签名失败：权限不足: {e}")

    except Exception as e:
        return Result(status=Status.SIGN_FAILED, msg=f"签名失败: {str(e)}")


def verify_signature(key_manager: SingleKeyManager,
                     file_path: Path,
                     signature_path: Path,
                     progress_callback: Callable[[float, str], None] | None = None) -> Result:
    """
    验证文件签名

    Args:
        key_manager (SingleKeyManager): 密钥管理器
        file_path (Path): 待验证文件路径
        signature_path (Path): 签名文件路径
        progress_callback: 可选进度回调 (fraction, message)

    Returns:
        verify_result (Result): 验证结果
    """
    if not file_path.exists() or not file_path.is_file():
        return Result(status=Status.FILE_NOT_FOUND, msg=f"待验证文件不存在: {file_path}")

    if not signature_path.exists() or not signature_path.is_file():
        found_path = Path(get_path(DirType.SIGNATURES), f"{file_path.name}.sig")
        if not found_path.exists():
            message = f"签名文件不存在: {signature_path}（自动查找也失败）"
            return Result(status=Status.SIGNATURE_FILE_MISSING, msg=message)
        signature_path = found_path

    if key_manager.public_key is None:
        return Result(status=Status.KEY_FILE_CORRUPT, msg="缺少公钥")

    try:
        v_data = _read_with_progress(file_path, progress_callback, 0.0, 0.8)

        if progress_callback:
            progress_callback(0.85, "正在读取签名...")

        with open(signature_path, "rb") as f:
            signature = f.read()

        if progress_callback:
            progress_callback(0.9, "正在验证...")

        key_manager.public_key.verify(
            signature,
            v_data,
            padding.PSS(mgf=padding.MGF1(SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            SHA256()
        )

        if progress_callback:
            progress_callback(1.0, "验证完成")

        return Result(status=Status.VERIFY_SUCCESS, msg="签名验证成功：文件完整未被篡改")

    except InvalidSignature:
        return Result(status=Status.VERIFY_FAILED, msg="签名验证失败：文件已被篡改或签名文件不匹配")

    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"验证失败：权限不足: {e}")

    except Exception as e:
        return Result(status=Status.VERIFY_FAILED, msg=f"验证失败: {str(e)}")


"""private methods"""
def _read_with_progress(file_path: Path,
                        progress_callback: Callable[[float, str], None] | None,
                        start: float,
                        end: float) -> bytes:
    """分块读取文件并报告进度"""
    file_size = file_path.stat().st_size
    data = bytearray()
    
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(_CHUNK_SIZE)
            if not chunk:
                break
           
            data.extend(chunk)
            if not progress_callback or file_size <= 0:
                continue

            fraction = start + (end - start) * (len(data) / file_size)
            progress_callback(fraction, f"读取中... {format_size(len(data))}/{format_size(file_size)}")
    
    return bytes(data)
