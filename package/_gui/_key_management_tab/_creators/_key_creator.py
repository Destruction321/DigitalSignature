# package/_gui/_key_management_tab/_creators/_key_creator.py
"""密钥创建模块"""
from dataclasses import dataclass
from datetime import datetime
from tkinter import END, messagebox
from typing import Callable, TYPE_CHECKING

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

from ...progress_dialog import ProgressDialog
from ...._core.keys.managers import SingleKeyManager
from ...._utils.constants import ENCRYPTED, UNENCRYPTED
from ...._utils.enums import Level
from ...._utils.result import Status, Result
from ...._utils.ui_state_manager import get_ui_state_manager
from ...._utils.worker import Worker

if TYPE_CHECKING:
    from tkinter import BooleanVar, Entry, Widget
    from tkinter.ttk import Combobox
    from ...._core.keys.managers import MultiKeyManager


@dataclass
class KeySetter:
    """
    密钥设置组件
    
    Attributes:
        key_id_entry (Entry): 密钥ID输入框
        key_size_combo (Combobox): 密钥长度选择框
        encryption_var (BooleanVar): 是否加密选择变量
        password_entry (Entry): 密码输入框
    """
    key_id_entry: Entry
    key_size_combo: Combobox
    encryption_var: BooleanVar
    password_entry: Entry

@dataclass
class CallBacks:
    """
    回调列表
    
    Attributes:
        refresh_callback (Callable[[], None]): 刷新密钥列表回调
        update_key_status_callback (Callable[[], None]): 更新密钥状态回调
        toggle_password_callback (Callable[[], None]): 切换密码输入框显示回调
    """
    refresh_callback: Callable[[], None]
    update_key_status_callback: Callable[[], None]
    toggle_password_callback: Callable[[], None]


class _KeyCreationWorker(Worker):
    """在后台线程生成 RSA 密钥对并保存"""
    def __init__(self,
                 multi_km: MultiKeyManager,
                 key_id: str,
                 key_size: int, password: str | None) -> None:
        super().__init__()
        self.__multi_km = multi_km
        self.__key_id = key_id
        self.__key_size = key_size
        self.__password = password


    def do_work(self) -> Result:
        self._report_progress(0.0, "正在生成密钥对...")
        if self.is_cancelled:
            return Result(status=Status.CANCEL_INPUT, msg="操作已取消")
       
        result = _create_key_pair(self.__multi_km, self.__key_id, self.__key_size, self.__password)
        if result.is_success and not self.is_cancelled:
            self._report_progress(1.0, "生成完成")
        
        return result


"""public methods"""
def create_key_pair(key_setter: KeySetter, multi_km: MultiKeyManager, callbacks: CallBacks, parent: Widget) -> None:
    """
    创建新的密钥对

    Args:
        key_setter (KeySetter): 密钥设置组件
        multi_km (MultiKeyManager): 密钥对管理器实例
        callbacks (CallBacks): 回调列表
        parent (tk.Widget): 父窗口
    """
    # 验证输入
    validate_result = _validate_inputs(key_setter)
    if validate_result is None:
        return

    key_id, key_size, password = validate_result
    ui_state_mgr = get_ui_state_manager()

    # 检查密钥ID是否重复
    if key_id in multi_km.key_pairs:
        messagebox.showerror("创建密钥对失败", Status.KEY_ID_DUPLICATE.msg)
        ui_state_mgr.update_status(Status.KEY_ID_DUPLICATE.msg)
        return

    # 启动后台线程 + 进度对话框
    dialog = ProgressDialog(
        parent=parent,
        title="生成密钥对",
        message=f"正在生成 {key_size} 位 RSA 密钥对...",
        indeterminate=True,
    )
    worker = _KeyCreationWorker(multi_km, key_id, key_size, password)
    create_result = dialog.run(worker)

    if create_result.is_success:
        _handle_creation_success(key_id, create_result.msg, key_setter, callbacks, multi_km)
        ui_state_mgr.update_dir_labels()
        return

    if create_result.status != Status.CANCEL_INPUT:
        messagebox.showerror("创建密钥对失败", create_result.msg)
        ui_state_mgr.update_status(f"创建密钥对失败: {create_result.msg}", Level.ERROR, log=True)


"""private methods"""
def _validate_inputs(key_setter: KeySetter) -> tuple[str, int, str | None] | None:
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
        messagebox.showerror("创建密钥对失败", Status.KEY_SIZE_ERROR.msg)
        return None
    
    # 密码验证
    password = _validate_password(key_setter.encryption_var, key_setter.password_entry)
    if not password.is_success:
        return None
    
    return key_id, key_size, password.data

def _create_key_pair(multi_km: MultiKeyManager, key_id: str, key_size: int, password: str | None) -> Result:
    """创建新的密钥对 -- 主逻辑"""
    try:
        # 生成RSA密钥对
        new_keys = SingleKeyManager(key_size, key_id)
        private_key = generate_private_key(
            public_exponent=65537,
            key_size=new_keys.key_size,
            backend=default_backend()
        )
        new_keys.private_key = private_key
        new_keys.public_key = private_key.public_key()
        
        # 获取保存路径
        private_key_path, public_key_path = multi_km.get_key_paths(key_id, key_size, password is not None)
        
        # 保存密钥文件
        save_result = new_keys.save_keys(private_key_path, public_key_path, password)
        if not save_result.is_success:
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
        if not config_result.is_success:
            return config_result
        
        encryption_status = ENCRYPTED if password else UNENCRYPTED
        message = f"密钥对 '{key_id}' 创建成功（{encryption_status}）"
        return Result(status=Status.SUCCESS, msg=message)
        
    except Exception as e:
        return Result(status=Status.KEY_FILE_CORRUPT, msg=f"创建密钥对失败: {str(e)}")

def _validate_password(encryption_var: BooleanVar, password_entry: Entry) -> Result:
    """获取密码"""
    if not encryption_var.get():
        return Result(status=Status.SUCCESS, data=None)  # 不加密，密码为None
    
    password = password_entry.get().strip()
    if not password:
        messagebox.showerror("创建密钥对失败", Status.NO_PASSWORD.msg)
        return Result(status=Status.NO_PASSWORD)
    
    if len(password) < 6:
        messagebox.showerror("创建密钥对失败", Status.PASSWORD_TOO_SHORT.msg)
        return Result(status=Status.PASSWORD_TOO_SHORT)
    
    return Result(status=Status.SUCCESS, data=password)

def _handle_creation_success(key_id: str,
                             message: str,
                             key_setter: KeySetter,
                             callbacks: CallBacks,
                             multi_km: MultiKeyManager) -> None:
    """处理创建成功"""
    messagebox.showinfo("成功", message)
    
    # 重置表单
    key_setter.key_id_entry.delete(0, END)
    key_setter.password_entry.delete(0, END)
    key_setter.encryption_var.set(False)
    callbacks.toggle_password_callback()
    
    # 回调更新状态
    get_ui_state_manager().update_status(f"密钥 '{key_id}' 创建成功")
    callbacks.refresh_callback()
    callbacks.update_key_status_callback()
        
    # 更新安全状态
    multi_km.config_secure = True
