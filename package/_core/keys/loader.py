# package/_core/keys/loader.py
"""密钥加载器"""
from typing import Callable, cast, TYPE_CHECKING

from .managers import SingleKeyManager
from ..._utils.constants import MAX_PASSWORD_ATTEMPTS
from ..._utils.result import Status, Result

if TYPE_CHECKING:
    from .managers import SingleKeyManager, MultiKeyManager


class KeyLoader:
    """密钥加载器"""
    def __init__(self, 
                 multi_key_manager: MultiKeyManager, 
                 password_provider: Callable[[str], str | None],
                 key_loaded_callback: Callable[[SingleKeyManager | None], None]) -> None:
        self.__multi_km: MultiKeyManager = multi_key_manager
        self.__password_provider: Callable[[str], str | None] = password_provider
        self.__key_loaded_callback: Callable[[SingleKeyManager | None], None] = key_loaded_callback


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
        if not status_result.is_success:
            return status_result
        
        # 静默加载处理
        if silent:
            if status_result.data:  # data为bool（是否加密）
                return Result(status=Status.NEED_PASSWORD)
            
            # 尝试静默加载
            load_result = self.__multi_km.load_key_pair(key_id, None)
            if load_result.is_success:
                self.__key_loaded_callback(cast(SingleKeyManager, load_result.data))
                    
            return load_result

        # 交互式输入密码（如果需要）
        password: Result | None = None
        if status_result.data:  # 已加密
            password = self.__validate_password(key_id)
            
            if not password.is_success:  # 用户取消
                return password
            
        # 尝试加载
        return self.__attempt_key_loading(key_id, password)

    
    """private methods"""
    def __validate_password(self, key_id: str, attempt: int = 1, is_retry: bool = False) -> Result:
        """验证密码"""
        while True:
            prompt: str = self.__build_password_prompt(key_id, attempt, is_retry)
            password: str | None = self.__password_provider(prompt)

            if password is None:
                return Result(status=Status.CANCEL_INPUT)

            if password.strip():
                return Result(status=Status.SUCCESS, data=password)
               
    @staticmethod
    def __build_password_prompt(key_id: str, attempt: int, is_retry: bool) -> str:
        """构建密码提示信息"""
        if is_retry:
            return f"密码错误，请重新输入密码 ({attempt}/{MAX_PASSWORD_ATTEMPTS}):"
        else:
            return f"密钥 '{key_id}' 已加密\n请输入密码:"
        
    def __attempt_key_loading(self, key_id: str, password: Result | None) -> Result:
        """尝试加载密钥（带重试机制）"""
        for attempt in range(1, MAX_PASSWORD_ATTEMPTS + 1):
            load_result = self.__multi_km.load_key_pair(key_id, password.data if password else None)
            
            # 成功：回调并返回结果
            if load_result.is_success:
                self.__key_loaded_callback(cast(SingleKeyManager, load_result.data))
                return load_result
            
            # 其他业务错误：直接返回
            if load_result.status != Status.PASSWORD_ERROR:
                return load_result
            
            # 密码错误：重试
            if attempt >= MAX_PASSWORD_ATTEMPTS:
                break

            password = self.__validate_password(key_id, attempt + 1, True)
            if not password.is_success:  # 用户取消
                return password
            
        self.__key_loaded_callback(None)
            
        return Result(status=Status.PASSWORD_ERROR, msg="密码错误次数过多，加载失败")
