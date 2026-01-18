# package/app/_modules/app_utils.py
"""数字签名窗口辅助工具"""
from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING

from .. import _utils
from .._utils import Status

if TYPE_CHECKING:
    from tkinter.ttk import Label
    from .._core.keys.loader import KeyLoader
    from .._core.keys.managers import MultiKeyManager
    from .._utils import DirType


def update_directory_info(dir_labels: dict[DirType, Label]) -> None:
    """
    更新所有目录信息显示
    
    Args:
        dir_labels (dict[DirType, Label]): 目录区域标签列表
    """
    for category, label in dir_labels.items():
        # 获取目录路径
        dir_path = _utils.DIRS.get(category)
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
            size_str = _utils.format_size(total_size)
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
    
    if reload_result.is_success():
        return
    
    if reload_result.status == Status.CANCEL_INPUT:
        messagebox.showinfo("取消加载", reload_result.msg)
        return
    
    messagebox.showerror("加载失败", f"重新加载密钥失败:\n\n{reload_result.msg}")
