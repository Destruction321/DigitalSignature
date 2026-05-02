# package/_backups/_backup_utils/_internal/_internal.py
"""备份服务内部工具"""
from pathlib import Path
from shutil import copyfile, copytree
from typing import Final

from ...._utils.enums import DirType, FileType
from ...._utils.result import Status, Result


"""constants"""
BACKUP: Final[str] = DirType.BACKUP.value

DATA: Final[str] = "data"

CHECKSUM_FILE: Final[str] = "backup_checksum.json"

DATA_TYPE: Final[dict[DirType, str]] = {
    DirType.FULL: "数据",
    DirType.KEYS: "密钥",
    DirType.TEXTS: "文本",
    DirType.SIGNATURES: "签名"
}


"""public methods in module 'internal'"""
def rm_dir(dir: Path, data_type: DirType) -> Result | None:
    """删除目录下的所有内容"""
    for file_name in dir.iterdir():
        try:
            if file_name.is_file():
                file_name.unlink()
                
        except Exception as e:
            message = f"清理{DATA_TYPE[data_type]}目录失败: {e}"
            return Result(status=Status.CLEANUP_FAILED, msg=message)

def get_dir_type():
    """导出目录类型"""
    return (
        DirType.KEYS.value,
        DirType.TEXTS.value,
        DirType.SIGNATURES.value
    )

def inferred_type(backup_dir: Path) -> DirType:
    """通过目录内容推断类型"""
    _PEM, _TXT, _SIG = _get_file_type()
    if (backup_dir / DirType.KEYS.value).exists():
        return DirType.FULL
    if _extension_exists(backup_dir, _PEM):
        return DirType.KEYS
    if _extension_exists(backup_dir, _TXT):
        return DirType.TEXTS
    if _extension_exists(backup_dir, _SIG):
        return DirType.SIGNATURES

    return DirType.UNKNOWN

def copy_tree_excluding_checksum(src_dir: Path, dst_dir: Path) -> None:
    """递归复制目录树，排除校验和文件"""
    dst_dir.mkdir(parents=True, exist_ok=True)

    for item in src_dir.iterdir():
        item = item.name
        src_path = src_dir / item
        dst_path = dst_dir / item

        # 跳过校验和文件
        if item == CHECKSUM_FILE:
            continue

        if src_path.is_dir():
            copytree(src_path, dst_path)
        else:
            copyfile(src_path, dst_path)

def get_directory_size(directory: Path) -> int:
    """计算目录大小"""
    total_size = 0
    for dir_path, _, file_names in directory.walk():
        for file_name in file_names:
            file_path = dir_path / file_name
            if file_path.is_file():
                total_size += file_path.stat().st_size

    return total_size


"""private methods"""
def _get_file_type():
    """导出文件类型"""
    return (
        FileType.KEY.value,
        FileType.TEXT.value,
        FileType.SIGNATURE.value
    )

def _extension_exists(backup_dir: Path, extension: str) -> bool:
    """通过扩展名判断"""
    for file_name in backup_dir.iterdir():
        # 构建完整路径
        full_path = backup_dir / file_name
        
        # 检查是否为文件
        if not full_path.is_file():
            continue  # 跳过目录
        
        # 检查文件扩展名
        if str(file_name).endswith(extension):
            return True  # 找到就立即返回
    
    return False  # 遍历完没找到
