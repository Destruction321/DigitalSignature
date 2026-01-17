# package/_utils/tools.py
"""工具函数"""
from .constants import DIRS, DirType


def get_path(category: DirType, file_name: str | None = None) -> str:
    """
    获取指定类别的文件路径
        
    Args:
        category (DirType): 目录类别：DirType.KEYS, DirType.TEXTS, DirType.SIGNATURES, DirType.TEMP
        file_name (str): 可选的文件名
    
    Raises:
        Error (KeyError): 如果类别不存在，抛出异常
            
    Returns:
        file_path (str): 完整的文件路径
    """
    if category not in DIRS:
        raise KeyError(
            f"目录类型 '{category.value}' 不存在。可用的类型:"
            f"{DirType.FULL.value}, "
            f"{DirType.KEYS.value}, "
            f"{DirType.TEXTS.value}, "
            f"{DirType.SIGNATURES.value}, "
            f"{DirType.TEMP.value}"
        )
    
    return str(DIRS[category]) if file_name is None else str(DIRS[category] / file_name)

def format_size(size: int) -> str:
    """
    格式化文件大小
    
    Args:
        size (int): 文件大小（字节）
        
    Returns:
        formatted_size (str): 格式化后的文件大小字符串
    """
    if size >= 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024 * 1024):.2f} GB"
    elif size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"
    elif size >= 1024:
        return f"{size / 1024:.2f} KB"
    else:
        return f"{size} 字节"
