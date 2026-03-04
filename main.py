# main.py
"""数字签名系统主程序入口"""
from logging import basicConfig, INFO
from pathlib import Path
from tkinter import Tk

from package import DIRS
from package.app import APP

try:
    # 创建数据目录
    for dir_path in DIRS.values():
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        
    # 配置日志记录
    Path("logs").mkdir(parents=True, exist_ok=True)
    basicConfig(filename="logs/app.log", level=INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    
    # 启动应用程序
    root = Tk()
    _app = APP(root)
    root.mainloop()
    
except Exception as e:
    from tkinter.messagebox import showerror
    showerror("启动应用程序失败", f"{e}")
