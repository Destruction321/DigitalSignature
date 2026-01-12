# package/_core/keys/key_loader.py
"""密钥加载器"""
from tkinter import messagebox
from tkinter.simpledialog import askstring
from typing import Any, Callable, cast, TYPE_CHECKING

from .key_manager import SingleKeyManager
from ... import utils
from ...utils import Status, Result

if TYPE_CHECKING:
    from tkinter import Tk
    from .key_manager import MultiKeyManager


class KeyLoader:
    """密钥加载器"""
    def __init__(self, 
                 multi_key_manager: MultiKeyManager, 
                 parent: Tk,
                 key_loaded_callback: Callable[[Any], None] | None = None,
                 update_status_callback: Callable[[str], None] | None = None,) -> None:
        self.__multi_km: MultiKeyManager = multi_key_manager
        self.__parent: Tk = parent
        self.__key_loaded_callback: Callable[[Any], None] | None = key_loaded_callback
        self.__update_status: Callable[[str], None] | None = update_status_callback
    

    """public methods"""
    def load_key(self, key_id: str, silent: bool = False) -> Result:
        """
        加载指定密钥

        Args:
            key_id (str): 密钥ID
            silent (bool): 是否静默加载（True=静默加载，False=正常加载）
            
        Returns:
            load_result (Result): 加载结果，成功时返回当前密钥对的管理器
        """
        # 校验密钥存在性
        if not key_id.strip():
            return Result(status=Status.PARAM_EMPTY)
        
        if key_id not in self.__multi_km.key_pairs:
            return Result(status=Status.KEY_NOT_FOUND)
        
        # 获取加密状态
        status_result = self.__multi_km.get_key_encryption_status(key_id)
        if not status_result.is_success():
            return status_result
        
        # 静默加载处理
        if silent:
            if status_result.data:  # data为bool（是否加密）
                return Result(status=Status.NEED_PASSWORD)
            
            # 尝试静默加载
            load_result = self.__multi_km.load_key_pair(key_id, None)
            if load_result.is_success():
                if self.__key_loaded_callback:
                    self.__key_loaded_callback(cast(SingleKeyManager, load_result.data))
                    
            return load_result

        # 交互式输入密码（如果需要）
        password: str | None = None
        if status_result.data:  # 已加密
            password_result = self.__request_password_interactive(key_id, status_result.msg)
            
            if password_result is False:  # 用户取消
                return Result(status=Status.CANCEL_INPUT, msg="密码输入已取消")
                
            password = cast(str | None, password_result)
            
        # 尝试加载
        return self.__attempt_key_loading(key_id, password)


    """private methods"""
    def __request_password_interactive(self, key_id: str, status_message: str) -> str | bool | None:
        """交互式请求密码"""
        if utils.ENCRYPTED not in status_message:
            return None  # 不需要密码

        return self.__request_and_validate_password(key_id)

    def __request_and_validate_password(self, key_id: str, attempt: int = 1, is_retry: bool = False) -> str | bool:
        """请求并验证密码"""
        prompt: str = self.__build_password_prompt(key_id, attempt, is_retry)
        password: str | None = askstring("密码输入", prompt, show="*", parent=self.__parent)

        if password is None:
            return False  # 用户取消

        if not password.strip():
            messagebox.showerror("错误", "密码不能为空")
            return self.__request_and_validate_password(key_id, attempt, is_retry)  # 重试

        return password

    def __build_password_prompt(self, key_id: str, attempt: int, is_retry: bool) -> str:
        """构建密码提示信息"""
        if is_retry:
            return f"密码错误，请重新输入密码 ({attempt}/{utils.MAX_PASSWORD_ATTEMPTS}):"
        else:
            return f"密钥 '{key_id}' 已加密\n请输入密码:"

    def __attempt_key_loading(self, key_id: str, password: str | bool | None) -> Result:
        """尝试加载密钥（带重试机制）"""
        for attempt in range(1, utils.MAX_PASSWORD_ATTEMPTS + 1):
            load_result = self.__multi_km.load_key_pair(key_id, cast(str | None, password))
            
            # 成功：回调并返回结果
            if load_result.is_success():
                self.__handle_key_loading_success(key_id, cast(SingleKeyManager, load_result.data))
                return load_result
            
            # 密码错误：重试
            if load_result.status == Status.PASSWORD_ERROR:
                if attempt >= utils.MAX_PASSWORD_ATTEMPTS:
                    # 重试次数用尽
                    break

                password = self.__request_and_validate_password(key_id, attempt + 1, True)
                if password is False:  # 用户取消
                    return Result(status=Status.CANCEL_INPUT, msg="密码输入已取消")
                
                continue
            
            # 其他业务错误：直接返回
            return load_result
        
        self.__handle_error("密码错误次数过多，加载密钥失败")
        return Result(status=Status.PASSWORD_ERROR, msg="密码错误次数过多，加载失败")
        
    def __handle_key_loading_success(self, key_id: str, key_manager: SingleKeyManager) -> None:
        """处理加载成功"""
        if self.__update_status:
            self.__update_status(f"已加载密钥对: {key_id}")
            
        if self.__key_loaded_callback:
            self.__key_loaded_callback(key_manager)
            
        messagebox.showinfo("成功", f"密钥对 '{key_id}' 加载成功")
        
    def __handle_error(self, error_message: str) -> None:
        """处理错误"""
        messagebox.showerror("错误", error_message)
        
        if self.__update_status:
            self.__update_status(f"加载失败: {error_message}")
            
        if self.__key_loaded_callback:
            self.__key_loaded_callback(None)
            