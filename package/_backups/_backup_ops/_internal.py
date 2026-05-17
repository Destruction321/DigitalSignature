# package/_backups/_backup_utils/_internal.py
"""备份服务内部工具"""
from datetime import datetime
from hashlib import sha256
from json import dump
from logging import warning, error
from os import stat_result
from pathlib import Path
from shutil import copyfile, copytree, rmtree
from typing import Final

from ..._utils.enums import DirType, FileType
from ..._utils.result import Status, Result
from ..._utils.tools import get_path


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


"""public methods"""
def backup_data(data_type: DirType) -> Result:
    """
    通用备份方法
    
    Args:
        data_type (DirType): 备份类型（full=完整备份，keys=密钥备份，texts=文本备份，signatures=签名备份）
        backup_dir (str | None): 备份目录路径（None=自动生成目录）
    
    Returns:
        result (Result): 备份结果，成功时包含备份路径和结果消息
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_type = DATA if data_type == DirType.FULL else data_type.value
    backup_dir = Path(f"{backup_type}{BACKUP}{timestamp}").resolve().as_posix()
        
    data_dir = get_path(DirType.FULL) if data_type == DirType.FULL else get_path(data_type)
    if not Path(data_dir).exists():
        return Result(status=Status.DIR_NOT_FOUND, msg=f"数据目录不存在: {data_dir}")
    
    try:
        copytree(data_dir, backup_dir)
        return Result(
            status=Status.SUCCESS,
            data=backup_dir,
            msg=f"{DATA_TYPE[data_type]}备份完成: {backup_dir}"
        )
        
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"备份失败：权限不足: {e}")
        
    except Exception as e:
        return Result(status=Status.BACKUP_FAILED, msg=f"备份失败: {e}")

def restore_full_backup(backup_dir: Path, _data_type: DirType, overwrite: bool) -> Result:
    """
    恢复完整备份
    
    Args:
        backup_dir (Path): 备份目录路径
        _data_type (DirType): 数据类型，实际为DirType.FULL，但参数保留以匹配接口
        overwrite (bool): 是否覆盖现有文件
    
    Returns:
        result (Result): 恢复结果，成功时包含结果消息
    """
    # 删除所有现有文件（如果覆盖）
    data_dir = Path(get_path(DirType.FULL))
    if overwrite and data_dir.exists():
        rmtree(data_dir)
   
    try:
        _copy_tree_excluding_checksum(backup_dir, data_dir)
        message = (
            f"完整数据恢复完成: \n"
            f"备份目录：{backup_dir.resolve().as_posix()}\n"
            f"恢复目录：{data_dir.resolve().as_posix()}"
        )
        return Result(status=Status.RESTORE_SUCCESS, msg=message)
        
    except Exception as e:
        return Result(status=Status.RESTORE_FAILED, msg=f"完整恢复失败: {e}")

def restore_partial_backup(backup_dir: Path, data_type: DirType, overwrite: bool) -> Result:
    """
    恢复部分备份（密钥、文本、签名）
    
    Args:
        backup_dir (Path): 备份目录路径
        data_type (DirType): 数据类型
        overwrite (bool): 是否覆盖现有文件
    
    Returns:
        result (Result): 恢复结果，成功时包含结果消息
    """
    dir = Path(get_path(data_type))
    dir.mkdir(parents=True, exist_ok=True)
    
    if overwrite:
        result = _rm_dir(dir, data_type)
        if result is not None and not result.is_success:
            return result
                
    # 复制文件
    copied_files = []
    for file_name in backup_dir.iterdir():
        file_name = file_name.name
        if file_name == CHECKSUM_FILE:
            continue
        
        src_path = backup_dir / file_name
        dst_path = dir / file_name
        
        if not src_path.is_file():
            continue
        
        try:
            copyfile(src_path, dst_path)
            copied_files.append(file_name)
            
        except Exception as e:
            message = f"复制文件 {file_name} 失败: {e}"
            return Result(status=Status.RESTORE_FAILED, msg=message)
        
    message = f"{DATA_TYPE[data_type]}恢复完成: 复制了 {len(copied_files)} 个文件到 {dir.resolve().as_posix()}"
    return Result(status=Status.RESTORE_SUCCESS, data=len(copied_files), msg=message)

def create_backup_checksum(backup_dir: Path, backup_type: str) -> None:
    """
    为备份目录创建校验和文件
    
    Args:
        backup_dir (Path): 备份路径
        backup_type (str): 备份类型
    """
    checksum, file_count, total_size = calculate_backup_checksum(backup_dir)
    checksum_data = {
        "backup_type": backup_type,
        "checksum": checksum,
        "file_count": file_count,
        "total_size": total_size,
        "created_time": datetime.now().isoformat(),
        "backup_version": "1.0"
    }

    checksum_file = backup_dir / CHECKSUM_FILE
    with open(checksum_file, "w", encoding="utf-8") as f:
        dump(checksum_data, f, ensure_ascii=False, indent=2)

def calculate_backup_checksum(backup_dir: Path) -> tuple[str, int, int]:
    """
    计算备份目录的校验和、文件数量和总大小
    
    Args:
        backup_dir (Path): 备份路径
        
    Returns:
        result (tuple[str, int, int]): 校验结果，包括哈希值、文件数量、目录大小
    """
    hash_sha256 = sha256()
    file_count = 0
    total_size = 0

    # 排除校验文件本身
    excluded_files = [CHECKSUM_FILE]

    # 递归获取所有文件并计算校验和
    for file_path in sorted(backup_dir.rglob("*")):
        if not file_path.is_file():
            continue
        
        if file_path.name in excluded_files:
            continue

        relative_path = file_path.relative_to(backup_dir).as_posix()
        
        try:
            file_size = file_path.stat().st_size
            file_count += 1
            total_size += file_size

            hash_sha256.update(relative_path.encode('utf-8'))
            hash_sha256.update(str(file_size).encode('utf-8'))

            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b''):
                    hash_sha256.update(chunk)
                    
        except Exception as e:
            warning(f"警告：无法读取文件 {file_path.as_posix()}: {e}")
            continue

    return hash_sha256.hexdigest(), file_count, total_size

def get_backups(backups: list[dict[str, str | Path | datetime | int]], current_dir: Path) -> None:
    """
    获取备份列表
    
    Args:
        backups (list[dict[str, str | Path | datetime | int]]):
            用于存储备份信息的列表，函数会将备份信息添加到该列表中
        current_dir (Path): 当前目录路径，函数会在该目录下查找备份目录
    """
    for item in current_dir.iterdir():
        if not item.is_dir() or not any(pattern in item.name for pattern in [BACKUP]):
            continue

        try:
            backup_info = {
                "name": item.name,
                "path": item,
                "created_time": datetime.fromtimestamp(_get_creation_time(item.stat())),
                "size": _get_directory_size(item)
            }
            backups.append(backup_info)
        except Exception as e:
            error(f"无法访问备份目录 {item.as_posix()}: {e}")
            continue

def detect_backup_type(backup_dir: Path) -> DirType:
    """
    检测备份类型
    
    Args:
        backup_dir (Path): 备份目录路径
        
    Returns:
        dir_type (DirType): 备份类型
    """
    backup_name = backup_dir.name
    KEYS, TEXTS, SIGNATURES = _get_dir_type()
    if backup_name.startswith(f"{DATA}{BACKUP}"):
        return DirType.FULL
    
    if backup_name.startswith(f"{KEYS}{BACKUP}"):
        return DirType.KEYS
    
    if backup_name.startswith(f"{TEXTS}{BACKUP}"):
        return DirType.TEXTS
    
    if backup_name.startswith(f"{SIGNATURES}{BACKUP}"):
        return DirType.SIGNATURES
    
    return _inferred_type(backup_dir)


"""private methods"""
def _rm_dir(dir: Path, data_type: DirType) -> Result | None:
    """删除目录下的所有内容"""
    for file_name in dir.iterdir():
        try:
            if file_name.is_file():
                file_name.unlink()
                
        except Exception as e:
            message = f"清理{DATA_TYPE[data_type]}目录失败: {e}"
            return Result(status=Status.CLEANUP_FAILED, msg=message)

def _get_dir_type() -> tuple[str, str, str]:
    """导出目录类型"""
    return (
        DirType.KEYS.value,
        DirType.TEXTS.value,
        DirType.SIGNATURES.value
    )

def _inferred_type(backup_dir: Path) -> DirType:
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

def _copy_tree_excluding_checksum(src_dir: Path, dst_dir: Path) -> None:
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

def _get_directory_size(directory: Path) -> int:
    """计算目录大小"""
    total_size = 0
    for dir_path, _, file_names in directory.walk():
        for file_name in file_names:
            file_path = dir_path / file_name
            if file_path.is_file():
                total_size += file_path.stat().st_size

    return total_size

def _get_creation_time(stat: stat_result) -> float:
    """获取文件创建时间"""
    birthtime = getattr(stat, "st_birthtime", None)
    if birthtime is not None:
        return birthtime
    
    return getattr(stat, "st_ctime", getattr(stat, "st_mtime", 0.0))

def _get_file_type() -> tuple[str, str, str]:
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