# build.py
"""构建脚本"""
import sys
from pathlib import Path
from shutil import which
from subprocess import run, CalledProcessError

def get_pyinstaller_exe() -> Path | None:
    """
    获取 pyinstaller.exe 的路径
    
    Returns:
        exe_path (Path | None): pyinstaller.exe 的完整路径，如果未找到则返回 None
    """
    # 方法1：从当前 Python 环境的 Scripts 目录查找
    python_dir = Path(sys.executable).parent
    exe_path = python_dir / "Scripts" / "pyinstaller.exe"
    
    if exe_path.exists():
        return exe_path
    
    # 方法2：从虚拟环境目录查找
    if hasattr(sys, "base_prefix"):
        venv_dir = Path(sys.prefix)
        exe_path = venv_dir / "Scripts" / "pyinstaller.exe"
        if exe_path.exists():
            return exe_path.resolve()
    
    # 方法3：从 PATH 中查找
    try:
        exe_path = which("pyinstaller.exe")
        if exe_path:
            return Path(exe_path).resolve()
    except:
        pass
    
    return None

def build_command(pyinstaller_exe: Path, project_root: Path, project_build: Path) -> list[str]:
    """
    构建 PyInstaller 命令
    
    Args:
        pyinstaller_exe (Path): pyinstaller.exe 的路径
        project_root (Path): 项目根目录的路径
        project_build (Path): 项目构建目录的路径

    Returns:
        cmd (list[str]): 构建命令列表
    """
    cmd = [
        str(pyinstaller_exe),
        "--clean",
        "--onedir",
        "--windowed",
        "--name", "DS_System",
        "--workpath", str(project_build),
        "--distpath", str(project_build / "dist"),
        "--specpath", str(project_build / "build_resources"),
    ]

    icon_path = project_build / "build_resources" / "icon.ico"
    if icon_path.exists():
        print(f"\033[33m发现图标文件：{icon_path}\033[0m")
        cmd.extend(["--icon", str(icon_path)])
    else:
        print(f"\033[31m警告: 图标文件不存在: {icon_path}\033[0m")
    
    cmd.append(str(project_root / "main.py"))
    return cmd

def build_dist(cmd: list[str], project_build: Path) -> None:
    """
    执行构建命令并显示结果
    
    Args:
        cmd (list[str]): 构建命令列表
        project_root (Path): 项目根目录的路径
        project_build (Path): 项目构建目录的路径
    """
    try:
        run(cmd, check=True)
        print("\n\033[33m构建完成！\033[0m")
        
        # 显示结果
        exe_path = project_build / "dist" / "DS_System"

        if not exe_path.exists():
            print(f"\n\033[31m输出目录不存在！\033[0m")
            return
        
        total_size = 0
        for file_path in exe_path.rglob("*"):  # rglob 递归遍历
            if not file_path.is_file():
                continue

            try:
                total_size += file_path.stat().st_size
            except OSError:
                continue
        
        total_size /= (1024 * 1024)
        print(f"\033[33m输出目录: {exe_path}\033[0m")
        print(f"\033[33m目录大小: {total_size:.1f} MB\033[0m")
            
    except CalledProcessError as e:
        print(f"\n\033[31m构建失败: {e}\033[0m")
    except Exception as e:
        print(f"\n\033[31m发生错误: {e}\033[0m")


if __name__ == "__main__":
    # 查找 pyinstaller.exe
    pyinstaller_exe = get_pyinstaller_exe()
    
    if not pyinstaller_exe:
        print("\033[31m找不到 pyinstaller.exe\033[0m")
        print("\033[31m请确保已安装 PyInstaller: pip install pyinstaller\033[0m")
    
    else:
        print(f"\033[33m找到 PyInstaller: {pyinstaller_exe}\033[0m")

        # 构建命令
        project_root = (Path(__file__).parent).resolve()
        project_build = project_root / "build"
        cmd = build_command(pyinstaller_exe, project_root, project_build)
        
        # 执行构建命令
        print(f"\033[35m\n执行命令:\033[0m")
        print(f"\033[34m{" ".join(cmd)}\033[0m")
        build_dist(cmd, project_build)