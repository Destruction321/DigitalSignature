# package/_core/signature.py
"""数字签名核心算法"""
from pathlib import Path
from typing import TYPE_CHECKING

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.hashes import SHA256

from .._utils.enums import DirType
from .._utils.result import Status, Result
from .._utils.tools import get_path

if TYPE_CHECKING:
    from .keys.managers import SingleKeyManager


def sign_file(key_manager: SingleKeyManager, file_path: Path, signature_path: str | None = None) -> Result:
    """
    对文件进行数字签名
    
    Args:
        key_manager (SingleKeyManager): 密钥管理器
        file_path (Path): 待签名文件路径
        signature_path (str): 签名文件保存路径（None=默认路径）
        
    Returns:
        signature_result (Result): 签名结果，成功时返回签名路径
    """
    # 校验参数
    if not file_path.exists() or not file_path.is_file():
        return Result(status=Status.FILE_NOT_FOUND, msg=f"待签名文件不存在: {file_path.as_posix()}")
    
    if key_manager is None or key_manager.private_key is None:
        return Result(status=Status.KEY_FILE_CORRUPT, msg="密钥管理器未初始化或缺少私钥")
    
    # 处理签名路径
    if signature_path is None:
        if file_path.parent == Path(get_path(DirType.TEMP)):
            signature_path = get_path(DirType.TEMP, f"{file_path.name}.sig")
        else:
            signature_path = get_path(DirType.SIGNATURES, f"{file_path.name}.sig")
            
    try:
        # 读取文件并签名
        with open(file_path, "rb") as f:
            s_data = f.read()
            
        signature = key_manager.private_key.sign(
            s_data,
            padding.PSS(mgf=padding.MGF1(SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            SHA256()
        )
        
        # 保存签名文件
        with open(signature_path, "wb") as f:
            f.write(signature)
            
        message = f"文件签名成功：{signature_path}"
        return Result(status=Status.SIGN_SUCCESS, data=signature_path, msg=message)
        
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"签名失败：权限不足: {e}")
        
    except Exception as e:
        return Result(status=Status.SIGN_FAILED, msg=f"签名失败: {str(e)}")

def verify_signature(key_manager: SingleKeyManager, file_path: str, signature_path: Path) -> Result:
    """
    验证文件签名
    
    Args:
        key_manager (SingleKeyManager): 密钥管理器
        file_path (str): 待验证文件路径
        signature_path (Path): 签名文件路径
        
    Returns:
        verify_result (Result): 验证结果
    """
    # 校验参数
    file_path_obj = Path(file_path)
    if not file_path_obj.exists() or not file_path_obj.is_file():
        return Result(status=Status.FILE_NOT_FOUND, msg=f"待验证文件不存在: {file_path}")
    
    if not signature_path.exists() or not signature_path.is_file():
        # 尝试自动查找签名文件
        found_path = Path(get_path(DirType.SIGNATURES), f"{file_path_obj.name}.sig")
        if not found_path.exists():
            message = f"签名文件不存在: {signature_path}（自动查找也失败）"
            return Result(status=Status.SIGNATURE_FILE_MISSING, msg=message)
            
        signature_path = found_path
        
    if key_manager.public_key is None:
        return Result(status=Status.KEY_FILE_CORRUPT, msg="缺少公钥")
    
    try:
        # 读取文件和签名
        with open(file_path, "rb") as f:
            v_data = f.read()
            
        with open(signature_path, "rb") as f:
            signature = f.read()
            
        # 验证签名
        key_manager.public_key.verify(
            signature,
            v_data,
            padding.PSS(mgf=padding.MGF1(SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            SHA256()
        )
        return Result(status=Status.VERIFY_SUCCESS, msg=f"签名验证成功：文件完整未被篡改")
    
    except InvalidSignature:
        return Result(status=Status.VERIFY_FAILED, msg="签名验证失败：文件已被篡改或签名文件不匹配")
        
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"验证失败：权限不足: {e}")
    
    except Exception as e:
        return Result(status=Status.VERIFY_FAILED, msg=f"验证失败: {str(e)}")
