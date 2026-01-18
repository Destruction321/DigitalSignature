"""build_simple.py - 最简单的构建脚本"""
import os
import sys
import subprocess
from pathlib import Path

def get_pyinstaller_exe():
    """获取 pyinstaller.exe 的路径"""
    # 方法1：从当前 Python 环境的 Scripts 目录查找
    python_dir = Path(sys.executable).parent
    exe_path = python_dir / "Scripts" / "pyinstaller.exe"
    
    if exe_path.exists():
        return exe_path
    
    # 方法2：从虚拟环境目录查找
    if hasattr(sys, 'base_prefix'):
        venv_dir = Path(sys.prefix)
        exe_path = venv_dir / "Scripts" / "pyinstaller.exe"
        if exe_path.exists():
            return exe_path
    
    # 方法3：从 PATH 中查找
    import shutil
    try:
        exe_path = shutil.which("pyinstaller.exe")
        if exe_path:
            return Path(exe_path)
    except:
        pass
    
    return None

def main():
    project_root = Path(__file__).parent
    
    # 查找 pyinstaller.exe
    pyinstaller_exe = get_pyinstaller_exe()
    
    if not pyinstaller_exe:
        print("❌ 找不到 pyinstaller.exe")
        print("请确保已安装 PyInstaller: pip install pyinstaller")
        return
    
    print(f"✅ 找到 PyInstaller: {pyinstaller_exe}")

    # 构建命令
    cmd = [
        str(pyinstaller_exe),
        "--clean",
        "--onedir",
        "--windowed",
        "--name", "DS_System",
        "--workpath", str(project_root / "build"),
        "--distpath", str(project_root / "dist"),
        "--specpath", str(project_root / "build_resources"),
        "--icon", str(project_root / "build_resources" / "icon.ico"),
        str(project_root / "main.py")
    ]
    
    print(f"\n执行命令:")
    print(" ".join(cmd))
    
    # 直接运行，不捕获输出，实时显示
    try:
        subprocess.run(cmd, check=True)
        print("\n✅ 构建完成！")
        
        # 显示结果
        exe_path = project_root / "dist" / "DS_System"

        if not exe_path.exists():
            print(f"\n❌ 输出目录不存在！")
            return
        
        total_size = 0
        for file_path in exe_path.rglob('*'):  # rglob 递归遍历
            if file_path.is_file():
                try:
                    total_size += file_path.stat().st_size
                except OSError:
                    continue
        
        total_size /= 1024
        print(f"输出目录: {exe_path}")
        print(f"文件大小: {total_size:.1f} MB")
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 构建失败: {e}")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")

if __name__ == "__main__":
    main()