# package/_core/keys/key_creator.py
"""密钥创建模块"""
import tkinter as tk
from dataclasses import dataclass
from datetime import datetime
from tkinter import messagebox
from typing import Callable, cast, TYPE_CHECKING

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa

from .key_manager import SingleKeyManager
from ..._utils import ENCRYPTED, Status, Result

if TYPE_CHECKING:
    from tkinter.ttk import Combobox
    from .key_manager import MultiKeyManager


@dataclass
class KeySetter:
    """密钥设置组件"""
    key_id_entry: tk.Entry
    key_size_combo: Combobox
    encryption_var: tk.BooleanVar
    password_entry: tk.Entry

@dataclass
class CallBacks:
    """回调列表"""
    update_status_callback: Callable[[str], None]
    refresh_callback: Callable[[], None]
    update_key_status_callback: Callable[[], None]
    toggle_password_callback: Callable[[], None]


"""public methods"""
def create_key_pair(key_setter: KeySetter, multi_km: MultiKeyManager, callbacks: CallBacks) -> None:
    """
    创建新的密钥对
    
    Args:
        key_setter (KeySetter): 密钥设置组件
        multi_km (MultiKeyManager): 密钥对管理器实例
        callbacks (CallBacks): 回调列表
    """
    # 验证输入
    validate_result = _validate_key_creation_inputs(key_setter)
    if validate_result is None:
        return
    
    key_id, key_size, password = validate_result
    
    # 检查密钥ID是否重复
    if key_id in multi_km.key_pairs:
        messagebox.showerror("创建密钥对失败", Status.KEY_ID_DUPLICATE.desc)
        callbacks.update_status_callback(Status.KEY_ID_DUPLICATE.desc)
        return
    
    # 创建密钥对
    create_result = _create_key_pair(multi_km, key_id, key_size, password)
    if create_result.is_success():
        # 4. 处理成功
        _handle_key_creation_success(key_id, create_result.msg, key_setter, callbacks, multi_km)
    else:
        messagebox.showerror("创建密钥对失败", create_result.msg)
        callbacks.update_status_callback(f"创建密钥对失败: {create_result.msg}")


"""private methods"""
def _validate_key_creation_inputs(key_setter: KeySetter) -> tuple[str, int, str | None] | None:
    """验证密钥创建输入"""
    # 密钥ID
    key_id = key_setter.key_id_entry.get().strip()
    if not key_id:
        messagebox.showerror("创建密钥对失败", "密钥ID不能为空")
        return None
    
    # 密钥长度
    try:
        key_size = int(key_setter.key_size_combo.get())
    except (ValueError, AttributeError):
        messagebox.showerror("创建密钥对失败", Status.KEY_SIZE_ERROR.desc)
        return None
    
    # 密码验证
    password = _get_and_validate_password(key_setter.encryption_var, key_setter.password_entry)
    if password is False:
        return None
    
    return key_id, key_size, cast(str | None, password)

def _create_key_pair(multi_km: MultiKeyManager, key_id: str, key_size: int, password: str | None) -> Result:
    """创建新的密钥对 -- 主逻辑"""
    try:
        # 生成RSA密钥对
        new_keys = SingleKeyManager(key_size, key_id)
        new_keys.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=new_keys.key_size,
            backend=default_backend()
        )
        new_keys.public_key = cast(rsa.RSAPrivateKey, new_keys.private_key).public_key()
        
        # 获取保存路径
        private_key_path, public_key_path = multi_km.get_key_paths(key_id, key_size, password is not None)
        
        # 保存密钥文件
        save_result = new_keys.save_keys(private_key_path, public_key_path, password)
        if not save_result.is_success():
            return save_result
        
        # 记录密钥信息到配置
        multi_km.key_pairs[key_id] = {
            "private_key_path": private_key_path,
            "public_key_path": public_key_path,
            "key_size": key_size,
            "created_time": datetime.now().isoformat(),
            "is_encrypted": password is not None
        }
        
        # 保存配置
        config_result = multi_km.save_keys_config()
        if not config_result.is_success():
            return config_result
        
        encryption_status = ENCRYPTED if password else "未加密"
        message = f"密钥对 '{key_id}' 创建成功（{encryption_status}）"
        return Result(status=Status.SUCCESS, msg=message)
        
    except Exception as e:
        return Result(status=Status.KEY_FILE_CORRUPT, msg=f"创建密钥对失败: {str(e)}")

def _get_and_validate_password(encryption_var: tk.BooleanVar, password_entry: tk.Entry) -> str | bool | None:
    """获取并验证密码"""
    if not encryption_var.get():
        return None
    
    password = password_entry.get().strip()
    if not password:
        messagebox.showerror("创建密钥对失败", Status.NO_PASSWORD.desc)
        return False
    
    if len(password) < 6:
        messagebox.showerror("创建密钥对失败", Status.PASSWORD_TOO_SHORT.desc)
        return False
    
    return password

def _handle_key_creation_success(key_id: str, message: str,
                                 key_setter: KeySetter, callbacks: CallBacks,
                                 multi_km: MultiKeyManager) -> None:
    """处理密钥创建成功"""
    messagebox.showinfo("成功", message)
    
    # 重置表单
    key_setter.key_id_entry.delete(0, tk.END)
    key_setter.password_entry.delete(0, tk.END)
    key_setter.encryption_var.set(False)
    callbacks.toggle_password_callback()
    
    # 回调更新状态
    callbacks.update_status_callback(f"密钥 '{key_id}' 创建成功")
    if callbacks.refresh_callback:
        callbacks.refresh_callback()
        
    if callbacks.update_key_status_callback:
        callbacks.update_key_status_callback()
        
    # 更新安全状态
    if hasattr(multi_km, "config_secure"):
        multi_km.config_secure = True
