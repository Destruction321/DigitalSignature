# package/_backups/_backup_utils/_internal.py
"""备份服务内部工具"""
import shutil
from datetime import datetime
from hashlib import sha256
from json import dump
from logging import warning, error
from pathlib import Path
from typing import Final, TYPE_CHECKING

from ..._utils.constants import BACKUP_DIR
from ..._utils.enums import DirType
from ..._utils.result import Status, Result
from ..._utils.tools import get_path

if TYPE_CHECKING:
    from os import stat_result
    from .._backup_list_type import BackupItem, BackupList
    from ..._utils.worker import ProgressCallback


"""constants"""
BACKUP: Final[str] = "_backup_"
CHECKSUM_FILE: Final[str] = "backup_checksum.json"
_BACKUP_IGNORE = shutil.ignore_patterns("*log*")
DATA_TYPE: Final[dict[DirType, str]] = {
    DirType.DATA: "数据",
    DirType.KEYS: "密钥",
    DirType.TEXTS: "文本",
    DirType.SIGNATURES: "签名"
}


"""public methods"""
def backup_data(data_type: DirType) -> Result:
    """
    通用备份方法
    
    Args:
        data_type (DirType): 备份类型（data=完整备份，keys=密钥备份，texts=文本备份，signatures=签名备份）
        backup_dir (str | None): 备份目录路径（None=自动生成目录）
    
    Returns:
        result (Result): 备份结果，成功时包含备份路径和结果消息
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_type = data_type.value
    backup_dir = (
        BACKUP_DIR / backup_type / f"{backup_type}{BACKUP}{timestamp}"
    ).resolve().as_posix()
        
    data_dir = get_path(data_type)
    if not Path(data_dir).exists():
        return Result(status=Status.DIR_NOT_FOUND, msg=f"数据目录不存在: {data_dir}")
    
    try:
        shutil.copytree(data_dir, backup_dir, ignore=_BACKUP_IGNORE)
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
        _data_type (DirType): 备份类型（此函数中用于做操作映射参数适配，无实际作用）
        overwrite (bool): 是否覆盖现有数据
    
    Returns:
        result (Result): 恢复结果，包含状态和消息
    """
    data_dir = Path(get_path(DirType.DATA))
    if overwrite and data_dir.exists():
        shutil.rmtree(data_dir)

    try:
        _copy_dir_tree(backup_dir, data_dir)
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
        data_type (DirType): 备份类型（keys=密钥备份，texts=文本备份，signatures=签名备份）
        overwrite (bool): 是否覆盖现有数据
        
    Returns:
        result (Result): 恢复结果，包含状态和消息
    """
    data_dir = Path(get_path(data_type)).resolve()
    data_dir.mkdir(parents=True, exist_ok=True)

    if overwrite:
        result = _rm_dir(data_dir, data_type)
        if result is not None and not result.is_success:
            return result

    copied_files = []
    for file_name in backup_dir.iterdir():
        file_name = file_name.name
        if file_name == CHECKSUM_FILE:
            continue

        src_path = backup_dir / file_name
        dst_path = data_dir / file_name

        if not src_path.is_file():
            continue

        try:
            shutil.copyfile(src_path, dst_path)
            copied_files.append(file_name)
        except Exception as e:
            message = f"复制文件 {file_name} 失败: {e}"
            return Result(status=Status.RESTORE_FAILED, msg=message)

    message = (
        f"{DATA_TYPE[data_type]}恢复完成: 复制了 {len(copied_files)} 个文件到 {data_dir.as_posix()}"
    )
    return Result(status=Status.RESTORE_SUCCESS, data=len(copied_files), msg=message)

def create_checksum(backup_dir: Path, backup_type: str) -> None:
    """
    为备份目录创建校验和文件
    
    Args:
        backup_dir (Path): 备份路径
        backup_type (str): 备份类型
    """
    checksum, file_count, total_size = calculate_checksum(backup_dir)
    checksum_data = {
        "backup_type": backup_type,
        "checksum": checksum,
        "file_count": file_count,
        "total_size": total_size,
        "created_time": datetime.now().isoformat(),
    }

    checksum_file = backup_dir / CHECKSUM_FILE
    with open(checksum_file, "w", encoding="utf-8") as f:
        dump(checksum_data, f, ensure_ascii=False, indent=2)

def calculate_checksum(backup_dir: Path,
                       progress_callback: ProgressCallback | None = None) -> tuple[str, int, int]:
    """
    计算备份目录的校验和、文件数量和总大小

    Args:
        backup_dir (Path): 备份路径
        progress_callback (ProgressCallback | None): 可选进度回调 (fraction, message)

    Returns:
        result (tuple[str, int, int]): 校验结果，包括哈希值、文件数量、目录大小
    """
    excluded_files = [CHECKSUM_FILE]
    file_list = sorted(
        p for p in backup_dir.rglob("*")
        if p.is_file() and p.name not in excluded_files
    )
    total_files = len(file_list)
    if total_files == 0:
        return sha256().hexdigest(), 0, 0

    hash_sha256 = sha256()
    file_count = 0
    total_size = 0
    processed = 0

    for file_path in file_list:
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

            processed += 1
            if progress_callback:
                progress_callback(processed / total_files, f"校验中... {processed}/{total_files}")

        except Exception as e:
            warning(f"警告：无法读取文件 {file_path.as_posix()}: {e}")
            continue

    return hash_sha256.hexdigest(), file_count, total_size

def scan_backups(backups_dir: Path) -> BackupList | None:
    """
    获取备份列表，扫描 backups/ 下各类型子目录中的备份

    Args:
        backups_dir: 备份根目录路径
        
    Returns:
        backups (BackupList | None): 备份列表，包含备份名称、路径、创建时间和大小等信息；如果目录不存在则返回 None
    """
    if not backups_dir.exists():
        return None

    backups: BackupList = []
    for type_dir in backups_dir.iterdir():
        if not type_dir.is_dir():
            continue

        for item in type_dir.iterdir():
            if not item.is_dir() or BACKUP not in item.name:
                continue

            try:
                backup_info: BackupItem = {
                    "name": f"{item.name}",
                    "path": item,
                    "created_time": datetime.fromtimestamp(_get_creation_time(item.stat())),
                    "size": _get_directory_size(item),
                }
                backups.append(backup_info)
            except Exception as e:
                error(f"无法访问备份目录 {item.as_posix()}: {e}")
                continue
    
    backups.sort(key=lambda x: (x["name"], x["created_time"], x["size"]))
    return backups

def detect_backup_type(backup_dir: Path) -> DirType:
    """通过父目录名检测备份类型"""
    parent_name = backup_dir.parent.name
    type_map = {d.value: d for d in (DirType.DATA, DirType.KEYS, DirType.TEXTS, DirType.SIGNATURES)}
    return type_map.get(parent_name, DirType.UNKNOWN)


"""private methods"""
def _rm_dir(data_dir: Path, data_type: DirType) -> Result | None:
    """删除目录下的所有内容"""
    for file_name in data_dir.iterdir():
        try:
            if file_name.is_file():
                file_name.unlink()
                
        except Exception as e:
            message = f"清理{DATA_TYPE[data_type]}目录失败: {e}"
            return Result(status=Status.CLEANUP_FAILED, msg=message)

def _copy_dir_tree(src_dir: Path, dst_dir: Path) -> None:
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
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copyfile(src_path, dst_path)

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
