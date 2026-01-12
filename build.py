"""构建脚本"""
import shutil, subprocess, sys
from pathlib import Path

# 项目配置
PROJECT_NAME = "DS_System"
PROJECT_ROOT = Path(__file__).parent
MAIN_ENTRY = PROJECT_ROOT / "main.py"
BUILD_RESOURCES_DIR = PROJECT_ROOT / "build_resources"
ICON_FILE = BUILD_RESOURCES_DIR / "icon.ico"


# 构建函数
def clean_build():
    """清理构建文件"""
    print("清理构建文件...")

    # 清理构建目录
    for dir_name in ["build", "dist"]:
        dir_path = PROJECT_ROOT / dir_name
        if not dir_path.exists():
            continue
        
        try:
            shutil.rmtree(dir_path)
            print(f"  ✓ 已清理 {dir_name}")
        except Exception as e:
            print(f"  ✗ 清理 {dir_name} 失败: {e}")

    # 清理所有位置的 spec 文件
    spec_locations = [
        PROJECT_ROOT,  # 根目录
        BUILD_RESOURCES_DIR,  # build_resources目录
    ]

    for location in spec_locations:
        spec_file = location / f"{PROJECT_NAME}.spec"
        if not spec_file.exists():
            continue

        try:
            spec_file.unlink()
            print(f"  ✓ 已清理 spec 文件: {spec_file}")
        except Exception as e:
            print(f"  ✗ 清理 spec 文件失败: {e}")


def build_project(onefile=False):
    """构建项目"""
    print(f"构建 {PROJECT_NAME} ({"单文件" if onefile else "目录"}模式)...")

    # 确保 build_resources 目录存在
    BUILD_RESOURCES_DIR.mkdir(exist_ok=True)

    # 构建命令 - 使用 --specpath 将spec文件生成到build_resources目录
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "--noconfirm",
        "--log-level", "WARN",
        "--name", PROJECT_NAME,
        "--specpath", str(BUILD_RESOURCES_DIR),  # 关键：指定spec文件生成位置
    ]

    if onefile:
        cmd.append("--onefile")
    else:
        cmd.append("--onedir")

    # Windows设置
    cmd.append("--windowed")

    # 图标
    if ICON_FILE.exists():
        cmd.extend(["--icon", str(ICON_FILE)])

    # 主要依赖
    for hidden in ["cryptography", "tkinter", "cryptography.hazmat",
                   "cryptography.hazmat.backends", "cryptography.hazmat.primitives"]:
        cmd.extend(["--hidden-import", hidden])

    # 主程序
    cmd.append(str(MAIN_ENTRY))

    print(f"执行命令: {" ".join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

        if result.returncode != 0:
            print("✗ 构建失败！")
            if result.stderr:
                print("错误信息:", result.stderr)
            return False
        
        print("✓ 构建成功！")

        # 检查并清理根目录可能误生成的 spec 文件
        root_spec = PROJECT_ROOT / f"{PROJECT_NAME}.spec"
        if root_spec.exists():
            try:
                root_spec.unlink()
                print("✓ 已清理根目录误生成的 spec 文件")
            except Exception as e:
                print(e)

        # 检查 spec 文件是否在 build_resources 目录
        spec_file = BUILD_RESOURCES_DIR / f"{PROJECT_NAME}.spec"
        if spec_file.exists():
            print(f"✓ spec 文件已生成到: {spec_file}")
        else:
            print(f" 注意: spec 文件未在指定位置生成")

        # 显示构建结果
        dist_dir = PROJECT_ROOT / "dist"
        if onefile:
            exe_file = dist_dir / f"{PROJECT_NAME}.exe"
            if exe_file.exists():
                size = exe_file.stat().st_size / (1024 * 1024)
                print(f"单文件: {exe_file} ({size:.1f} MB)")
        else:
            exe_dir = dist_dir / PROJECT_NAME
            if exe_dir.exists():
                print(f"目录: {exe_dir}")

        return True

    except Exception as e:
        print(f"构建出错: {e}")
        return False


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description=f"构建 {PROJECT_NAME}")
    parser.add_argument("--onefile", action="store_true", help="单文件模式")
    parser.add_argument("--clean", action="store_true", help="清理构建文件")

    args = parser.parse_args()

    if args.clean:
        clean_build()

    success = build_project(onefile=args.onefile)

    if success:
        print("\n🎉 构建完成！")
        sys.exit(0)
    else:
        print("\n❌ 构建失败！")
        sys.exit(1)


if __name__ == "__main__":
    main()
