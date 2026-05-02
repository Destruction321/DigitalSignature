# package/_utils/tools.py
"""工具函数"""
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING

from .constants import DIRS
from .enums import DirType
from .result import Status

if TYPE_CHECKING:
    from tkinter.ttk import Label
    from .._core.keys.loader import KeyLoader
    from .._core.keys.managers import MultiKeyManager
    

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

def update_directory_info(dir_labels: dict[DirType, Label]) -> None:
    """
    更新所有目录信息显示
    
    Args:
        dir_labels (dict[DirType, Label]): 目录区域标签列表
    """
    for category, label in dir_labels.items():
        # 获取目录路径
        dir_path = DIRS.get(category)
        if not dir_path:
            label.config(text=f"未知目录类别: {category}")
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
            size_str = format_size(total_size)
            label.config(text=f"{file_count}文件/{size_str}")
            
        except (PermissionError, OSError) as e:
            label.config(text=f"访问错误: {e}")

def reload_current_key(multi_km: MultiKeyManager, key_loader: KeyLoader, click_reload_btn: bool = False) -> None:
    """
    重新加载当前密钥
    
    Args:
        multi_km (MultiKeyManager): 当前的多密钥对管理器
        key_loader (KeyLoader): 当前的密钥加载器
        click_reload_btn (bool): 是否由按钮触发，默认为False（非按钮触发）
    """
    if multi_km.current_key_id is None:
        if click_reload_btn:
            messagebox.showwarning("警告", "没有加载的密钥对")
        return

    # 使用统一的KeyLoader加载密钥
    reload_result = key_loader.load_key(multi_km.current_key_id)
    
    if reload_result.is_success:
        return
    
    if reload_result.status == Status.CANCEL_INPUT:
        messagebox.showinfo("取消加载", reload_result.msg)
        return
    
    messagebox.showerror("加载失败", f"重新加载密钥失败:\n\n{reload_result.msg}")
