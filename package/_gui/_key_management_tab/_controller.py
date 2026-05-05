# package/_gui/_key_management_tab/_controller.py
"""密钥管理标签页控制器"""
from tkinter import messagebox
from typing import cast, TYPE_CHECKING

from ._password_validator import PasswordValidator
from ..._core.keys.managers import SingleKeyManager
from ..._utils.constants import ENCRYPTED
from ..._utils.enums import PassWord
from ..._utils.result import Status
from ..._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from tkinter import Widget
    from ._km_protocol import KeyManagerProtocol
    from ..._core.keys.loader import KeyLoader
    from ..._core.keys.managers import MultiKeyManager
    from ..._utils.ui_state_manager import UIStateManager
    

class Controller:
    """密钥管理标签页控制器"""
    def __init__(self,
                 km_protocol: KeyManagerProtocol,
                 multi_km: MultiKeyManager,
                 key_loader: KeyLoader,
                 parent: Widget) -> None:
        self.__km_protocol: KeyManagerProtocol = km_protocol
        self.__multi_km: MultiKeyManager = multi_km
        self.__key_loader: KeyLoader = key_loader
        self.__ui_state_mgr: UIStateManager = get_ui_state_manager()
        self.__loaded_key_id: str | None = None
        self.__key_id_map: dict[str, str] = {}

        # 注册恢复回调
        self.__multi_km.recovery_callback = self.__handle_key_recovery

        # 密码验证服务
        self.__password_validator = PasswordValidator(
            self.__multi_km,
            parent,
            update_status=self.__ui_state_mgr.update_status,
            refresh_list=self.refresh_key_list,
            update_security=self.update_security_status,
        )


    @property
    def loaded_key_id(self) -> str | None:
        return self.__loaded_key_id

    @loaded_key_id.setter
    def loaded_key_id(self, key_id: str | None) -> None:
        self.__loaded_key_id = key_id
        self.update_key_status()


    """public methods"""
    def refresh_key_list(self, click_refresh_btn: bool = False) -> None:
        """
        刷新密钥列表
        
        Args:
            click_refresh_btn (bool): 是否由点击刷新按钮触发，默认为 False（非按钮触发）
        """
        keys = list(self.__multi_km.key_pairs.keys())

        if not keys:
            self.__multi_km.recovery_mgr.try_rebuild_from_files()
            keys = list(self.__multi_km.key_pairs.keys())
            if not keys:
                if click_refresh_btn:
                    messagebox.showerror("警告", "没有可用的密钥对")
                return

        items: list[tuple[str, str]] = []
        for key_id in keys:
            status_result = self.__multi_km.get_key_encryption_status(key_id)
            key_info = self.__multi_km.key_pairs.get(key_id, {})
            key_size = key_info.get("key_size", "未知")

            if status_result.is_success:
                display_text = f"{key_id}[{status_result.msg}，{key_size}位]"
            else:
                display_text = f"{key_id}[状态未知，{key_size}位]"

            items.append((display_text, key_id))

        # 同步更新内部映射，供后续解析选中项使用
        self.__key_id_map = {display: key_id for display, key_id in items}
        self.__km_protocol.populate_key_list(items)

        if click_refresh_btn:
            messagebox.showinfo("成功", "刷新成功")

    def update_key_status(self) -> None:
        """更新密钥状态显示"""
        current_key_id = self.__multi_km.current_key_id
        if current_key_id is None:
            self.__km_protocol.set_key_status("未选择密钥", "gray")
            return

        status_result = self.__multi_km.get_key_encryption_status(current_key_id)
        if not status_result.is_success:
            self.__km_protocol.set_key_status("未找到密钥对", "red")
            return

        status = status_result.msg
        if current_key_id == self.__loaded_key_id:
            text = f"当前密钥: {current_key_id} (已加载, {status})"
            color = "green"
        else:
            label = "未解密" if ENCRYPTED in status else "未加载"
            text = f"当前密钥: {current_key_id} ({label}, {status})"
            color = "orange"

        self.__km_protocol.set_key_status(text, color)

    def update_security_status(self, is_secure: bool) -> None:
        """更新配置安全状态显示"""
        self.__multi_km.config_secure = is_secure
        if is_secure:
            self.__km_protocol.set_security_status("配置完整性: 已验证", "green")
        else:
            self.__km_protocol.set_security_status("配置完整性: 未验证/已损坏", "orange")

    def load_selected_key(self) -> SingleKeyManager | None:
        """加载选中的密钥"""
        key_id = self.__get_selected_key_id()
        if key_id is None:
            return None

        try:
            load_result = self.__key_loader.load_key(key_id)
            if load_result.is_success:
                self.update_key_status()
                return cast(SingleKeyManager, load_result.data)
            else:
                messagebox.showerror("加载失败", load_result.msg)
                self.__ui_state_mgr.update_status(f"加载失败: {load_result.msg}")
                return None
        except Exception as e:
            messagebox.showerror("系统错误", f"加载密钥时发生系统错误: {str(e)}")
            return None

    def delete_selected_key(self) -> None:
        """删除选中的密钥"""
        key_id = self.__get_selected_key_id()
        if key_id is None:
            return

        if not messagebox.askyesno("确认", f"确定要删除密钥对 '{key_id}' 吗？"):
            return

        delete_result = self.__multi_km.delete_key_pair(key_id)
        if not delete_result.is_success:
            messagebox.showerror("删除失败", delete_result.msg)
            return

        self.refresh_key_list()
        self.update_key_status()
        self.__ui_state_mgr.update_status(f"删除密钥对: {key_id}")

        if key_id == self.__loaded_key_id:
            self.__loaded_key_id = None

        self.update_security_status(True)
        messagebox.showinfo("成功", delete_result.msg)

    def show_encryption_status(self) -> None:
        """显示选中密钥的加密状态"""
        key_id = self.__get_selected_key_id()
        if key_id is None:
            return

        status_result = self.__multi_km.get_key_encryption_status(key_id)
        if status_result.is_success:
            messagebox.showinfo("加密状态", f"密钥 '{key_id}' 的状态:\n\n{status_result.msg}")
        else:
            messagebox.showerror("错误", status_result.msg)

    def change_key_password(self) -> None:
        """更改选中密钥的加密密码"""
        key_id = self.__get_selected_key_id()
        if key_id is None:
            return

        self.__handle_change_result(key_id, PassWord.CHANGE)

    def recover_config(self) -> None:
        """恢复配置"""
        if not messagebox.askyesno(
            "恢复密钥配置",
            "确定要恢复密钥配置吗？\n\n"
            "这将：\n"
            "1. 扫描密钥目录重建配置\n"
            "2. 遇到加密密钥时提示重新设置密码\n"
            "3. 当前配置将被覆盖",
        ):
            return

        result = self.__multi_km.recovery_mgr.try_rebuild_from_files()
        if result.is_success:
            messagebox.showinfo("成功", "配置恢复成功")
            self.refresh_key_list()
            self.update_key_status()
            self.__ui_state_mgr.update_status("配置恢复完成")
            self.update_security_status(True)
            self.__loaded_key_id = None
        else:
            messagebox.showerror("错误", f"配置恢复失败: {result.msg}")


    """private methods"""
    def __get_selected_key_id(self) -> str | None:
        """从视图获取选中项并解析出 key_id，无选中时弹出警告并返回 None"""
        display_text = self.__km_protocol.get_selected_display_text()
        if display_text is None:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return None

        return self.__parse_key_id(display_text)

    def __parse_key_id(self, display_text: str) -> str | None:
        """从显示文本解析 key_id"""
        if display_text in self.__key_id_map:
            return self.__key_id_map[display_text]
        if "[" in display_text:
            return display_text.split("[")[0].strip()
        if display_text:
            return display_text
        messagebox.showerror("错误", "无法解析密钥ID")
        return None

    def __handle_key_recovery(self, key_id: str, action: PassWord) -> None:
        """处理密钥恢复回调"""
        if action != PassWord.RECOVERY:
            return

        if messagebox.askyesno(
            "加密密钥恢复",
            f"发现加密密钥 '{key_id}'，您想要做什么？\n\n"
            f"是(Y): 重置密码（需要输入旧密码，最多尝试3次）\n"
            f"否(N): 暂时跳过，稍后手动处理",
        ):
            self.__handle_change_result(key_id, PassWord.RECOVERY)
        else:
            self.__ui_state_mgr.update_status(f"跳过加密密钥 '{key_id}' 的恢复")

    def __handle_change_result(self, key_id: str, mode: PassWord) -> None:
        """处理密码修改结果"""
        change_result = self.__password_validator.validate_and_reset_password(
            key_id=key_id, mode=mode
        )
        if change_result.is_success:
            messagebox.showinfo("成功", f"密钥 '{key_id}' 密码修改成功：{change_result.msg}")
        elif change_result.status == Status.CANCEL_INPUT:
            messagebox.showinfo("取消", f"密钥 '{key_id}' 已{change_result.msg}")
        else:
            messagebox.showerror("错误", f"密钥 '{key_id}' 修改密码失败：{change_result.msg}")
