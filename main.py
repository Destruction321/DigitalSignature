# main.py
"""数字签名系统主程序入口"""
import tkinter as tk
from pathlib import Path

from package.app import APP
from package.utils import DIRS


# 创建数据目录
for dir_path in DIRS.values():
    Path(dir_path).mkdir(parents=True, exist_ok=True)
    
# 启动应用程序
try:
    root = tk.Tk()
    _app = APP(root)
    root.mainloop()
except Exception as e:
    from tkinter.messagebox import showerror
    showerror("启动应用程序失败", f"{e}")
