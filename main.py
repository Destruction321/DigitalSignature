# main.py
"""数字签名系统主程序入口"""
import logging
from pathlib import Path
from tkinter import Tk

from package import DIRS
from package.app import APP


def _initialize_loggers(test: bool = False) -> None:
    """初始化日志记录器"""
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # 创建根 logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)  # 设为最低级别，让所有日志都经过处理器，由处理器和过滤器控制

    # 定义统一的日志格式
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

    # ----- 处理器1：记录 INFO 及以下到 info.log -----
    info_handler = logging.FileHandler(log_dir / "info.log", encoding="utf-8")

    # 添加过滤器，只允许 INFO 及以下通过
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


if __name__ == "__main__":
    try:
        # 创建数据目录
        for dir_path in DIRS.values():
            Path(dir_path).mkdir(parents=True, exist_ok=True)
            
        # 配置日志记录
        _initialize_loggers()
        
        # 启动应用程序
        root = Tk()
        _app = APP(root)
        root.mainloop()
        
    except Exception as e:
        from tkinter.messagebox import showerror
        showerror("启动应用程序失败", f"{e}")
