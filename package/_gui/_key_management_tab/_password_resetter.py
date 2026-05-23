# package/_gui/_key_management_tab/_password_resetter.py
"""密码重置器"""
from tkinter import messagebox, simpledialog
from typing import Callable, cast, TYPE_CHECKING, TypedDict

from ..._utils.constants import MAX_PASSWORD_ATTEMPTS
from ..._utils.enums import PassWord
from ..._utils.result import Status, Result
from ..._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from tkinter import Widget
    from ..._core.keys.managers import MultiKeyManager


class _SetNewPassword(TypedDict):
    """重置密码所需数据"""
    key_id: str
    old_password: str | None
    mode: PassWord
    is_encrypted: bool


class PasswordResetter:
    """密码重置器"""
    def __init__(self,
                 multi_key_manager: MultiKeyManager,
                 parent_window: Widget,
                 refresh_list: Callable[[], None],
                 update_security: Callable[[bool], None]) -> None:
        self.__multi_km = multi_key_manager
        self.__parent_window = parent_window
        self.__refresh_callback: Callable[[], None] = refresh_list
        self.__update_security_callback: Callable[[bool], None] = update_security


    """public methods"""
    def reset_password(self, key_id: str, mode: PassWord = PassWord.CHANGE) -> Result:
        """
        验证旧密码并重置为新密码
        
        Args:
            key_id (str): 密钥ID
            mode (PassWord): 操作上下文（PassWord.CHANGE=更改密码, PassWord.RECOVERY=恢复配置）
            
        Returns:
            reset_result (Result): 重置结果
        """
        # 检查密钥是否存在
        if not key_id.strip():
            return Result(status=Status.PARAM_EMPTY)
        if key_id not in self.__multi_km.key_pairs:
            return Result(status=Status.KEY_NOT_FOUND, msg=f"密钥 '{key_id}' 不存在")
            
        # 获取密钥加密状态
        status_result = self.__multi_km.get_key_encryption_status(key_id)
        if not status_result.is_success:
            return status_result
        
        # 验证旧密码
        old_password: str | None = None
        if status_result.data:
            verify_result = self.__verify_old_password(key_id, mode)
            if not verify_result.is_success:
                return verify_result  # 传递旧密码验证失败状态
            
            old_password = cast(str, verify_result.data)  # 验证成功则data为旧密码
            
        # 设置新密码
        return self.__set_new_password({
            "key_id": key_id,
            "old_password": old_password,
            "mode": mode,
            "is_encrypted": status_result.data
        })


    """private methods"""
    def __verify_old_password(self, key_id: str, mode: PassWord) -> Result:
        """验证旧密码"""
        attempts_left = MAX_PASSWORD_ATTEMPTS
        context_text = "恢复配置" if mode == PassWord.RECOVERY else "更改密码"
        
        while attempts_left > 0:
            # 构建提示信息
            prompt = f"正在进行{context_text}\n请输入密钥 '{key_id}' 的旧密码（剩余次数: {attempts_left}）"

            # 请求输入旧密码
            old_password = simpledialog.askstring(
                "验证旧密码", prompt, show="*", parent=self.__parent_window
            )

            # 用户取消
            if old_password is None:
                return Result(status=Status.CANCEL_INPUT, msg=f"取消{context_text}")

            # 密码为空
            if not old_password.strip():
                messagebox.showerror("错误", "密码不能为空", parent=self.__parent_window)
                attempts_left -= 1
                if attempts_left <= 0:
                    break
                continue
            
            # 尝试验证密码（保存当前密钥ID，防止 load_key_pair 的副作用切换密钥）
            saved_key_id = self.__multi_km.current_key_id
            load_result = self.__multi_km.load_key_pair(key_id, old_password)
            if load_result.status == Status.PASSWORD_ERROR:
                self.__multi_km.current_key_id = saved_key_id
            elif load_result.is_success:
                self.__multi_km.current_key_id = saved_key_id
                return Result(status=Status.SUCCESS, data=old_password)
            
            elif load_result.status == Status.SYSTEM_ERROR:
                self.__multi_km.current_key_id = saved_key_id
                return load_result
                
            # 密码错误
            attempts_left -= 1
            if attempts_left <= 0:
                break
                
            # 询问是否重试
            retry = messagebox.askretrycancel(
                "密码错误", f"密码错误！剩余尝试次数: {attempts_left}\n是否重试？",
                parent=self.__parent_window
            )
            
            if not retry:
                return Result(status=Status.CANCEL_INPUT, msg=f"放弃{context_text}")
                
        message = f"密码验证失败次数过多！密钥 '{key_id}' 的{context_text}已被锁定"
        return Result(status=Status.OLD_PASSWORD_ERROR, msg=message)

    def __set_new_password(self, set_new_password: _SetNewPassword) -> Result:
        """设置新密码"""
        key_id = set_new_password["key_id"]
        old_password = set_new_password["old_password"]
        mode = set_new_password["mode"]
        is_encrypted = set_new_password["is_encrypted"]

        context_text = "恢复配置" if mode == PassWord.RECOVERY else "更改密码"
        
        # 构建提示信息
        if is_encrypted:
            prompt = f"验证成功！请为密钥 '{set_new_password["key_id"]}' 设置新密码（留空则移除加密）:"
        else:
            prompt = f"密钥 '{set_new_password["key_id"]}' 当前未加密，请输入新密码（留空则保持不加密）:"
            
        # 请求输入新密码
        new_password = simpledialog.askstring(
            "设置新密码", prompt, show="*", parent=self.__parent_window
        )
        
        # 用户取消
        if new_password is None:
            return Result(status=Status.CANCEL_INPUT, msg="取消设置新密码")
            
        # 处理新密码（留空=移除加密）
        new_password = new_password.strip() if new_password else None
        if new_password and len(new_password) < 6:
            # 新密码过短
            return Result(status=Status.PASSWORD_TOO_SHORT)
        
        # 执行密码更改
        change_result = self.__multi_km.change_key_password(key_id, old_password, new_password)
        if not change_result.is_success:
            return change_result  # 传递更改失败状态
        
        # 成功回调
        self.__refresh_callback()
        self.__update_security_callback(True)
        get_ui_state_manager().update_status(f"{context_text}密钥密码: {key_id}")
        
        # 成功结果
        status_desc = "设置加密" if new_password else "移除加密"
        message = f"{context_text}成功（{status_desc}）"
        return Result(status=Status.SUCCESS, msg=message)
