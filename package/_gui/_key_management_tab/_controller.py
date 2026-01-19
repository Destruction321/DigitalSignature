# package/_gui/key_management_tab/controller.py
"""密钥管理标签页控制器"""
import tkinter as tk
from tkinter import messagebox
from typing import cast, TYPE_CHECKING

from ._password_validator import PasswordValidator
from ..._core.keys.managers import SingleKeyManager
from ..._utils import ENCRYPTED, PassWord, Status
from ..._utils.ui_state_manager import get_ui_state_manager

if TYPE_CHECKING:
    from ._ui_creator import UICreator
    from ..._core.keys.loader import KeyLoader
    from ..._utils.ui_state_manager import UIStateManager
    

class Controller:
    """控制器"""
    def __init__(self, ui: UICreator, key_loader: KeyLoader):
        self.__ui: UICreator = ui
        self.__ui.multi_km.recovery_callback = self.__handle_key_recovery
        self.__key_listbox: tk.Listbox = cast(tk.Listbox, self.__ui.key_listbox)
        self.__ui_state_mgr: UIStateManager = get_ui_state_manager()
        
        self.__loaded_key_id: str | None = None

        self.__key_loader = key_loader
        self.__key_id_map: dict[str, str] = {}
        
        # 创建密码验证服务
        self.__password_validator = PasswordValidator(
            self.__ui.multi_km,
            self.__ui.parent,
            update_status=self.__ui_state_mgr.update_status,
            refresh_list=self.refresh_key_list,
            update_security=self.update_security_status
        )
        
        
    @property
    def ksy_listbox(self) -> tk.Listbox:
        return self.__key_listbox
    
    @ksy_listbox.setter
    def ksy_listbox(self, key_listbox: tk.Listbox) -> None:
        self.__key_listbox = key_listbox
        
    @property
    def loaded_key_id(self) -> str | None:
        return self.__loaded_key_id

    @loaded_key_id.setter
    def loaded_key_id(self, key_id: str | None) -> None:
        self.__loaded_key_id = key_id
        self.update_key_status()
        
        
    """public methods"""
    def update_security_status(self, is_secure: bool) -> None:
        """
        更新安全状态显示
        
        Args:
            is_secure (bool): 配置验证结果
        """
        if self.__ui.security_status_label is None:
            return

        # 更新MultiKeyManager的安全状态
        self.__ui.multi_km.config_secure = is_secure

        if is_secure:
            self.__ui.security_status_label.config(text="配置完整性: 已验证", foreground="green")
        else:
            self.__ui.security_status_label.config(text="配置完整性: 未验证/已损坏", foreground="orange")

    
    """public methods -- bind to buttons"""
    def refresh_key_list(self, click_refresh_btn: bool = False) -> None:
        """
        刷新密钥列表
        
        Args:
            click_refresh_btn (bool): 是否由按钮触发，默认为False
        """
        if self.__key_listbox is None:
            if click_refresh_btn:
                messagebox.showerror("警告", "密钥列表未初始化")
            return
        
        self.__key_listbox.delete(0, tk.END)
        self.__key_id_map.clear()
        keys = list(self.__ui.multi_km.key_pairs.keys())
        
        if not keys:
            self.__ui.multi_km.recovery_mgr.try_rebuild_from_files()
            keys = list(self.__ui.multi_km.key_pairs.keys())
            if not keys:
                if click_refresh_btn:
                    messagebox.showerror("警告", "没有可用的密钥对")
                return
            
        for key_id in keys:
            status_result = self.__ui.multi_km.get_key_encryption_status(key_id)
            
            if status_result.is_success():
                key_info = self.__ui.multi_km.key_pairs.get(key_id, {})
                key_size = key_info.get("key_size", "未知")
                display_text = f"{key_id}[{status_result.msg}，{key_size}位]"
            else:
                key_info = self.__ui.multi_km.key_pairs.get(key_id, {})
                key_size = key_info.get("key_size", "未知")
                display_text = f"{key_id}[状态未知，{key_size}位]"
                
            self.__key_id_map[display_text] = key_id
            self.__key_listbox.insert(tk.END, display_text)
            self.__ui.key_listbox = self.__key_listbox
            
        if click_refresh_btn:
            messagebox.showinfo("成功", "刷新成功")
    
    def update_key_status(self) -> None:
        """更新密钥状态显示"""
        if self.__ui.key_status_label is None:
            return
        
        current_key_id = self.__ui.multi_km.current_key_id
        if current_key_id is None:
            self.__ui.key_status_label.config(text="未选择密钥", foreground="gray")
            return
        
        status_result = self.__ui.multi_km.get_key_encryption_status(current_key_id)
        if not status_result.is_success():
            self.__ui.key_status_label.config(text="未找到密钥对", foreground="red")
            return
        
        status = status_result.msg
        
        if current_key_id == self.__loaded_key_id:
            status_text = f"当前密钥: {current_key_id} (已加载, {status})"
            color = "green"
        else:
            if ENCRYPTED in status:
                status_text = f"当前密钥: {current_key_id} (未解密, {status})"
            else:
                status_text = f"当前密钥: {current_key_id} (未加载, {status})"   
            color = "orange"
            
        self.__ui.key_status_label.config(text=status_text, foreground=color)

    def recover_config(self) -> None:
        """恢复配置"""
        response = messagebox.askyesno(
            "恢复密钥配置",
            "确定要恢复密钥配置吗？\n\n"
            "这将：\n"
            "1. 扫描密钥目录重建配置\n"
            "2. 遇到加密密钥时提示重新设置密码\n"
            "3. 当前配置将被覆盖"
        )

        if not response:
            return

        result = self.__ui.multi_km.recovery_mgr.try_rebuild_from_files()
        # 执行配置恢复
        if result.is_success():
            messagebox.showinfo("成功", "配置恢复成功")
            self.refresh_key_list()
            self.update_key_status()
            self.__ui_state_mgr.update_status("配置恢复完成")
            # 恢复配置后会保存配置，更新安全状态
            self.update_security_status(True)
            # 配置恢复后，重置加载状态
            self.__loaded_key_id = None
        else:
            messagebox.showerror("错误", f"配置恢复失败: {result.msg}")

    def change_key_password(self) -> None:
        """更改密钥的加密密码"""
        selection = self.__key_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return
        
        display_text = self.__key_listbox.get(selection[0])
        key_id = self.__get_key_id_and_size(display_text)
        if not key_id:
            messagebox.showerror("错误", "无法解析密钥ID")
            return
        
        self.__handle_change_result(key_id, PassWord.CHANGE)
        
    def load_selected_key(self) -> SingleKeyManager | None:
        """加载选中的密钥"""
        selection = self.__key_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return None
        
        display_text = self.__key_listbox.get(selection[0])
        key_id = self.__get_key_id_and_size(display_text)
        if not key_id:
            messagebox.showerror("错误", "无法解析密钥ID")
            return None
        
        try:
            load_result = self.__key_loader.load_key(key_id)
            if load_result.is_success():
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
        selection = self.__key_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return
        
        display_text = self.__key_listbox.get(selection[0])
        key_id = self.__get_key_id_and_size(display_text)
        if not key_id:
            messagebox.showerror("错误", "无法解析密钥ID")
            return
        
        if not messagebox.askyesno("确认", f"确定要删除密钥对 '{key_id}' 吗？"):
            return
        
        delete_result = self.__ui.multi_km.delete_key_pair(key_id)
        if not delete_result.is_success():
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
        selection = self.__key_listbox.curselection()
        if not selection:
            messagebox.showwarning("警告", "请选择一个密钥对")
            return
        
        display_text = self.__key_listbox.get(selection[0])
        key_id = self.__get_key_id_and_size(display_text)
        if not key_id:
            messagebox.showerror("错误", "无法解析密钥ID")
            return

        status_result = self.__ui.multi_km.get_key_encryption_status(key_id)
        if status_result.is_success():
            messagebox.showinfo("加密状态", f"密钥 '{key_id}' 的状态:\n\n{status_result.msg}")
        else:
            messagebox.showerror("错误", status_result.msg)


    """private methods"""
    def __handle_key_recovery(self, key_id: str, action: PassWord) -> None:
        """处理密钥恢复"""
        if action != PassWord.RECOVERY:
            return

        # 询问用户想要做什么
        choice = messagebox.askyesno(
            "加密密钥恢复",
            f"发现加密密钥 '{key_id}'，您想要做什么？\n\n"
            f"是(Y): 重置密码（需要输入旧密码，最多尝试3次）\n"
            f"否(N): 暂时跳过，稍后手动处理\n"
        )

        if choice: # 用户选择重置密码
            self.__handle_change_result(key_id, PassWord.RECOVERY)
        else:  # 用户选择跳过
            self.__ui_state_mgr.update_status(f"跳过加密密钥 '{key_id}' 的恢复")

    def __handle_change_result(self, key_id: str, mode: PassWord) -> None:
        change_result = self.__password_validator.validate_and_reset_password(
            key_id=key_id,
            mode=mode
        )
        if change_result.is_success():
            messagebox.showinfo("成功", f"密钥 '{key_id}' 密码修改成功：{change_result.msg}")
            return
        
        if change_result.status == Status.CANCEL_INPUT:
            messagebox.showinfo("取消", f"密钥 '{key_id}' 已{change_result.msg}")
            return
            
        messagebox.showerror("错误", f"密钥 '{key_id}' 修改密码失败：{change_result.msg}")

    def __get_key_id_and_size(self, display_text: str) -> str:
        """从显示文本中提取密钥ID和长度"""
        if display_text in self.__key_id_map:
            return self.__key_id_map[display_text]

        # 密钥ID[加密状态，密钥长度位]
        if "[" in display_text:
            return display_text.split("[")[0].strip()
        else:
            return display_text
