# package/_utils/ui_state_manager.py
"""UI状态管理器"""
from logging import getLogger
from typing import Callable

from .enums import Level


class UIStateManager:
    """UI状态管理器"""
    def __init__(self) -> None:
        # 处理器列表
        self.__status_handlers: list[Callable[[str], None]] = []
        self.__result_handlers: list[Callable[[str, str], None]] = []
        self.__dir_handlers: list[Callable[[], None]] = []
        
        # 日志记录器
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

    def update_status(self, message: str, level: Level = Level.INFO, log: bool = False) -> None:
        """
        更新状态 - 通知所有注册的处理器（目录标签更新除外）
        
        Args:
            message (str): 提示信息
            level (Level): 日志级别
            log (bool): 是否记录日志，默认为 False（不记录）
        """
        if log:
            getattr(self.__logger, level.value)(message)
        
        for handler in self.__status_handlers:
            try:
                handler(message)
            except Exception as e:
                self.__logger.error(f"状态处理器错误: {e}")

    def show_result(self, text: str, tab_type: str, level: Level = Level.INFO, log: bool = False) -> None:
        """
        显示结果 - 通知所有注册的处理器（目录标签更新除外）
        
        Args:
            text (str): 显示文本
            tab_type (str): 当前文件类型
            level (Level): 日志级别
            log (bool): 是否记录日志，默认为 False（不记录）
        """
        if log:
            getattr(self.__logger, level.value)(f"结果显示 [{tab_type}]: {text[:50]}...")

        for handler in self.__result_handlers:
            try:
                handler(text, tab_type)
            except Exception as e:
                self.__logger.error(f"结果处理器错误: {e}")


# 创建全局实例
_ui_state_manager = UIStateManager()

def get_ui_state_manager() -> UIStateManager:
    """
    获取全局UI状态管理器实例
    
    Returns:
        UI状态管理器实例
    """
    return _ui_state_manager
