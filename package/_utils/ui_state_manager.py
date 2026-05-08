# package/_utils/ui_state_manager.py
"""UI状态管理器"""
from logging import getLogger
from typing import Any, Callable


class UIStateManager:
    """UI状态管理器"""
    def __init__(self) -> None:
        self.__status_handlers: list[Callable[[str], None]] = []
        self.__result_handlers: list[Callable[[str, str], None]] = []
        self.__dir_handlers: list[Callable[[], None]] = []
        self.__logger = getLogger(__name__)

    
    """public methods"""
    def register_status_handler(self, handler: Callable[[str], None]) -> None:
        """
        注册状态处理器
        
        Args:
            handler: 需要注册的状态处理器
        """
        self.__status_handlers.append(handler)
        self.__logger.debug(f"注册状态处理器: {handler.__name__}")

    def register_result_handler(self, handler: Callable[[str, str], None]) -> None:
        """
        注册结果处理器
        
        Args:
            handler: 需要注册的结果处理器
        """
        self.__result_handlers.append(handler)
        self.__logger.debug(f"注册结果处理器: {handler.__name__}")
        
    def register_dir_labels_handler(self, handler: Callable[[], None]) -> None:
        """
        注册目录标签更新处理器
        
        Args:
            handler: 需要注册的目录标签更新处理器
        """
        self.__dir_handlers.append(handler)
        self.__logger.debug(f"注册目录标签更新处理器: {handler.__name__}")

    def update_dir_labels(self) -> None:
        """通知所有目录标签更新处理器"""
        for handler in self.__dir_handlers:
            try:
                handler()
            except Exception as e:
                self.__logger.error(f"目录标签处理器错误: {e}")

    def update_status(self, message: Any) -> None:
        """
        更新状态 - 通知所有注册的处理器（目录标签更新除外）
        
        Args:
            message: 提示信息
        """
        status_message = self.__ensure_string(message)
        self.__logger.info(f"状态更新: {status_message}")

        for handler in self.__status_handlers:
            try:
                handler(status_message)
            except Exception as e:
                self.__logger.error(f"状态处理器错误: {e}")

    def show_result(self, text: Any, tab_type: str = "file") -> None:
        """
        显示结果 - 通知所有注册的处理器（目录标签更新除外）
        
        Args:
            text: 显示文本
            tab_type: 当前文件类型
        """
        result_text = self.__ensure_string(text)
        self.__logger.info(f"结果显示 [{tab_type}]: {result_text[:50]}...")

        for handler in self.__result_handlers:
            try:
                handler(result_text, tab_type)
            except Exception as e:
                self.__logger.error(f"结果处理器错误: {e}")


    """private methods"""
    def __ensure_string(self, obj: Any) -> str:
        """确保对象转换为有意义的字符串"""
        if isinstance(obj, str):
            return obj
        elif obj is None:
            return ""

        class_name = obj.__class__.__name__

        if class_name == "SingleKeyManager":
            return self.__format_key_manager_string(obj)

        elif hasattr(obj, "__dict__"):
            return self.__format_object_string(obj, class_name)
        else:
            return str(obj)

    @staticmethod
    def __format_key_manager_string(key_manager: Any) -> str:
        """格式化 SingleKeyManager 对象的字符串表示"""
        try:
            key_id = getattr(key_manager, "_key_id", "未知")
            key_size = getattr(key_manager, "_key_size", "未知")

            if key_id and key_id != "未知":
                return f"已加载密钥: {key_id} ({key_size}位)"
            else:
                return f"密钥管理器 ({key_size}位)"

        except Exception as e:
            return f"密钥管理器对象：{e}"

    @staticmethod
    def __format_object_string(obj: Any, class_name: str) -> str:
        """格式化通用对象的字符串表示"""
        try:
            attrs = obj.__dict__
            meaningful_attrs = []
            for attr_name, attr_value in attrs.items():
                if attr_name.startswith("_"):
                    continue

                if isinstance(attr_value, (str, int, float, bool)):
                    meaningful_attrs.append(f"{attr_name}={attr_value}")
                elif attr_name in ["current_key_id", "_key_id", "status", "message"]:
                    meaningful_attrs.append(f"{attr_name}={attr_value}")

            if meaningful_attrs:
                return f"{class_name}({", ".join(meaningful_attrs)})"
            else:
                return f"{class_name}对象"

        except Exception as e:
            return f"{class_name}对象：{e}"


# 创建全局实例
_ui_state_manager = UIStateManager()

def get_ui_state_manager() -> UIStateManager:
    """
    获取全局UI状态管理器实例
    
    Returns:
        UI状态管理器实例
    """
    return _ui_state_manager
