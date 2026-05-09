# main.py
"""数字签名系统主程序入口"""
import logging, sys
from pathlib import Path
from tkinter import Tk, messagebox

import package


def _initialize_loggers() -> None:
    """初始化日志记录器"""
    log_dir = Path("logs")
    test = not log_dir.exists()
    log_dir.mkdir(parents=True, exist_ok=True)

    # 创建根 logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 设为最低级别，让所有日志都经过处理器

    # 定义统一的日志格式
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    # ----- 处理器1：记录 INFO 及以下到 info.log -----
    info_handler = logging.FileHandler(log_dir / "info.log", encoding="utf-8")
    info_handler.addFilter(lambda record: record.levelno <= logging.INFO)
    info_handler.setFormatter(formatter)

    # ----- 处理器2：记录 WARNING 及以上到 warning.log -----
    warn_handler = logging.FileHandler(log_dir / "warning.log", encoding="utf-8")
    warn_handler.setLevel(logging.WARNING)
    warn_handler.setFormatter(formatter)

    # 将处理器添加到根 logger
    logger.addHandler(info_handler)
    logger.addHandler(warn_handler)

    # 测试日志
    if test:
        logging.debug("这是 debug 信息")
        logging.info("这是 info 信息")
        logging.warning("这是 warning 信息")
        logging.error("这是 error 信息")
        logging.critical("这是 critical 信息")

def _handler(exc_type, exc_value, exc_tb):
    """全局错误捕获钩子"""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        return

    # 记录完整堆栈
    logging.critical("未捕获的异常", exc_info=(exc_type, exc_value, exc_tb))
    messagebox.showerror(
        "程序错误",
        f"发生未预期的错误，程序可能处于不稳定状态。\n\n"
        f"错误类型：{exc_type.__name__}\n"
        f"错误信息：{exc_value}\n\n"
        f"详细信息已记录到日志文件。"
    )


if __name__ == "__main__":
    try:
        # 创建数据目录
        for dir_path in package.DIRS.values():
            Path(dir_path).mkdir(parents=True, exist_ok=True)

        # 配置日志记录
        _initialize_loggers()

        # 设置全局异常钩子
        sys.excepthook = _handler

        # 启动应用程序
        root = Tk()
        _app = package.APP(root)
        root.mainloop()

    except Exception as e:
        logging.critical("应用启动失败", exc_info=True)
        messagebox.showerror("启动失败", f"{e}")
