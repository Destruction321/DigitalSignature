# package/_backups/_modules/backup_utils.py
"""统一备份服务"""
import shutil
from datetime import datetime
from hashlib import sha256
from json import load, dump
from logging import warning
from os.path import relpath
from pathlib import Path
from typing import Any, Callable, Final

from .. import _utils
from .._utils import DirType, Status, Result

_BACKUP_: Final[str] = DirType.BACKUP.value

_DATA: Final[str] = "data"

_CHECKSUM_FILE: Final[str] = "backup_checksum.json"

_BACKUP_OPERATIONS: Final[dict[DirType, Callable[[str | None], Result]]] = {
    DirType.FULL: lambda backup_dir=None: _backup_data(DirType.FULL, backup_dir),
    DirType.KEYS: lambda backup_dir=None: _backup_data(DirType.KEYS, backup_dir),
    DirType.TEXTS: lambda backup_dir=None: _backup_data(DirType.TEXTS, backup_dir),
    DirType.SIGNATURES: lambda backup_dir=None: _backup_data(DirType.SIGNATURES, backup_dir)
}

_RESTORE_OPERATIONS: Final[dict[DirType, Callable[[Path, Any, bool], Result]]] = {
    DirType.FULL: lambda bd, dd, ov: _restore_full_backup(bd, dd, ov),
    DirType.KEYS: lambda bd, dd, ov: _restore_partial_backup(bd, dd, ov),
    DirType.TEXTS: lambda bd, dd, ov: _restore_partial_backup(bd, dd, ov),
    DirType.SIGNATURES: lambda bd, dd, ov: _restore_partial_backup(bd, dd, ov)
}

_DATA_TYPE: Final[dict[DirType, str]] = {
    DirType.FULL: "数据",
    DirType.KEYS: "密钥",
    DirType.TEXTS: "文本",
    DirType.SIGNATURES: "签名"
}


"""public methods"""
def create_backup(backup_type: DirType = DirType.FULL, backup_dir: str | None = None) -> Result:
    """
    创建备份
    
    Args:
        backup_type (DirType): 备份类型（full=完整备份，keys=密钥备份，texts=文本备份，signatures=签名备份）
        backup_dir (str | None): 备份目录路径（None=自动生成目录）
        
    Returns:
        result (Result): 备份结果，成功时包含备份路径和结果消息
    """
    operation = _BACKUP_OPERATIONS.get(backup_type)
    if not operation:
        message = f"不支持的备份类型: {backup_type.value}"
        return Result(status=Status.PARAM_EMPTY, msg=message)
        
    # 执行备份
    backup_result = operation(backup_dir)
    if not backup_result.is_success:
        return backup_result
    
    # 生成校验和
    backup_path = _extract_backup_path(backup_result.msg, backup_dir)
    if backup_path and Path(backup_path).exists():
        try:
            _create_backup_checksum(Path(backup_path), backup_type.value)
            message = f"{backup_result.msg}\n已生成完整性校验信息"
            return Result(status=Status.BACKUP_SUCCESS, data=backup_path, msg=message)
        
        except Exception as e:
            message = f"{backup_result.msg}\n备份成功，但校验和生成失败: {e}"
            return Result(status=Status.BACKUP_SUCCESS, data=backup_path, msg=message)
            
    return Result(status=Status.BACKUP_SUCCESS, data=backup_path, msg=backup_result.msg)

def list_backups_with_integrity() -> Result:
    """
    列出所有备份目录，包含完整性验证信息
    
    Returns:
        result (Result): 备份列表结果，成功时添加完整性验证结果
    """
    backups = list_backups()
    if not backups.is_success:
        return Result(status=backups.status, data=[], msg=backups.msg)

    for backup in backups.data:
        # 验证备份完整性
        verify_result = verify_backup_integrity(backup["path"])

        backup["integrity_valid"] = verify_result.is_success
        backup["integrity_message"] = verify_result.msg
        backup["checksum_data"] = verify_result.data

        # 在备份名称中添加完整性标记
        if verify_result.is_success:
            backup["display_name"] = f"✓ {backup["name"]}"
        else:
            backup["display_name"] = f"⚠ {backup["name"]}"

    return backups

def verify_backup_integrity(backup_dir: Path) -> Result:
    """
    验证备份完整性
    
    Args:
        backup_dir (Path): 备份目录路径
        
    Returns:
        verify_result (Result): 完整性验证结果，验证通过时包含是否有效、结果消息以及校验和数据字典
    """
    if not backup_dir.exists():
        return Result(status=Status.NO_BACKUP_FILE, data={}, msg="备份目录不存在")

    checksum_file = backup_dir / _CHECKSUM_FILE

    if not checksum_file.exists():
        return Result(status=Status.BACKUP_VERIFY_FAILED, data={}, msg="备份缺少完整性校验信息")

    try:
        # 读取校验和信息
        with open(checksum_file, "r", encoding="utf-8") as f:
            checksum_data = load(f)

        # 验证备份类型
        backup_type = checksum_data.get("backup_type", "unknown")
        stored_checksum = checksum_data.get("checksum", "")
        file_count = checksum_data.get("file_count", 0)
        total_size = checksum_data.get("total_size", 0)

        # 计算当前备份的校验和
        current_checksum, current_file_count, current_total_size = _calculate_backup_checksum(backup_dir)
        message: str = ""

        # 验证校验和
        if stored_checksum != current_checksum:
            message += "备份完整性验证失败：\n校验和不匹配"

        # 验证文件数量
        if file_count != current_file_count:
            message += f"\n文件数量不匹配（应有{file_count}个，实有{current_file_count}个）"

        # 验证文件大小
        if total_size != current_total_size:
            message += f"\n文件大小不匹配（应有{total_size}字节，实有{current_total_size}字节）"
            return Result(status=Status.BACKUP_VERIFY_FAILED, data=checksum_data, msg=message)

        message = f"备份完整性验证通过（{backup_type}，{file_count}个文件，{_utils.format_size(total_size)}）"
        return Result(status=Status.BACKUP_VERIFY_SUCCESS, data=checksum_data, msg=message)
    
    except Exception as e:
        return Result(status=Status.BACKUP_VERIFY_FAILED, data={}, msg=f"备份完整性验证失败：{e}")

def list_backups() -> Result:
    """
    列出所有备份目录
    
    Returns:
        result (Result): 备份列表结果，成功时包含备份信息列表，每项包含名称、路径、创建时间和大小
    """
    backups: list[dict[str, Any]] = []
    current_dir = Path.cwd()

    try:
        for item in current_dir.iterdir():
            if not item.is_dir() or not any(pattern in item.name for pattern in [_BACKUP_]):
                continue

            try:
                backup_info = {
                    "name": item.name,
                    "path": item,
                    "created_time": datetime.fromtimestamp(item.stat().st_birthtime),
                    "size": _get_directory_size(item)
                }
                backups.append(backup_info)
            except Exception as e:
                warning(f"无法访问备份目录 {item}: {e}")
                continue

        backups.sort(key=lambda x: x["created_time"], reverse=True)
        return Result(status=Status.SUCCESS, data=backups)

    except FileNotFoundError:
        return Result(status=Status.NO_BACKUP_FILE, data=[], msg="没有找到备份目录")
    
    except PermissionError:
        return Result(status=Status.PERMISSION_DENIED, data=[], msg="权限不足，无法访问备份目录")
    
    except Exception as e:
        return Result(status=Status.FAILED, data=[], msg=f"列出备份时发生错误: {e}")

def restore_backup(backup_dir: Path, overwrite: bool = False, backup_type: DirType | None = None) -> Result:
    """
    从备份恢复数据
    
    Args:
        backup_dir (Path): 备份数据路径
        overwrite (bool): 是否覆写原数据
        backup_type (DirType | None): 备份数据类型
        
    Raises:
        system_error (Exception): 系统错误
        
    Returns:
        restore_result (Result): 恢复结果
    """
    if not backup_dir.exists():
        return Result(status=Status.DIR_NOT_FOUND, msg=f"备份目录不存在: {backup_dir}")
        
    # 自动检测备份类型
    if backup_type is None:
        backup_type = _detect_backup_type(backup_dir)
        
    if backup_type == DirType.UNKNOWN:
        return Result(status=Status.PARAM_EMPTY, msg="无法检测备份类型")
        
    # 执行恢复
    operation = _RESTORE_OPERATIONS.get(backup_type)
    if not operation:
        return Result(status=Status.PARAM_EMPTY, msg=f"不支持的备份类型: {backup_type.value}")
        
    try:
        if backup_type == DirType.FULL:
            restore_result = operation(backup_dir, Path(_utils.get_path(DirType.FULL)), overwrite)
        else:
            restore_result = operation(backup_dir, backup_type, overwrite)
        return restore_result
    
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"恢复失败：权限不足: {e}")
        
    except Exception as e:
        raise Exception(f"恢复系统错误: {str(e)}") from e

def delete_backup(backup_name: str) -> Result:
    """
    删除指定的备份

    Args:
        backup_name (str): 备份目录名称
        
    Raises:
        system_error (Exception): 系统错误
        
    Returns:
        delete_result (Result): 删除结果
    """
    try:
        backup_path = Path.cwd() / backup_name
        if not backup_path.exists():
            return Result(status=Status.DIR_NOT_FOUND, msg=f"备份 '{backup_name}' 不存在")
            
        if not backup_path.is_dir() or not any(pattern in backup_name for pattern in [_BACKUP_]):
            return Result(status=Status.PARAM_EMPTY, msg=f"'{backup_name}' 不是有效的备份目录")
            
        shutil.rmtree(backup_path)
        return Result(status=Status.SUCCESS, msg=f"备份 '{backup_name}' 已成功删除")
        
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"删除失败：权限不足: {e}")
        
    except Exception as e:
        raise Exception(f"删除备份系统错误: {str(e)}") from e


"""private methods"""
def _backup_data(data_type: DirType, backup_dir: str | None = None) -> Result:
    """通用备份方法"""
    if backup_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = f"{_DATA if data_type == DirType.FULL else data_type.value}{_BACKUP_}{timestamp}"
        
    data_dir = _utils.get_path(DirType.FULL) if data_type == DirType.FULL else _utils.get_path(data_type)
    if not Path(data_dir).exists():
        return Result(status=Status.DIR_NOT_FOUND, msg=f"数据目录不存在: {data_dir}")
    
    try:
        shutil.copytree(data_dir, backup_dir)
        return Result(
            status=Status.SUCCESS,
            data=backup_dir,
            msg=f"{_DATA_TYPE[data_type]}备份完成: {Path(backup_dir).resolve()}"
        )
        
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"备份失败：权限不足: {e}")
        
    except Exception as e:
        return Result(status=Status.BACKUP_FAILED, msg=f"备份失败: {e}")

def _restore_full_backup(backup_dir: Path, data_dir: Path, overwrite: bool) -> Result:
    """恢复完整备份"""
    # 删除所有现有文件（如果覆盖）
    if overwrite and data_dir.exists():
        shutil.rmtree(data_dir)
   
    try:
        _copy_tree_excluding_checksum(backup_dir, data_dir)
        message = f"完整数据恢复完成: {backup_dir} -> {data_dir}"
        return Result(status=Status.RESTORE_SUCCESS, msg=message)
        
    except Exception as e:
        return Result(status=Status.RESTORE_FAILED, msg=f"完整恢复失败: {e}")

def _restore_partial_backup(backup_dir: Path, data_type: DirType, overwrite: bool) -> Result:
    """恢复部分备份（密钥、文本、签名）"""
    dir = Path(_utils.get_path(data_type))
    dir.mkdir(parents=True, exist_ok=True)
    
    if overwrite:
        for file_name in dir.iterdir():
            try:
                if file_name.is_file():
                    file_name.unlink()
                    
            except Exception as e:
                message = f"清理{_DATA_TYPE[data_type]}目录失败: {e}"
                return Result(status=Status.CLEANUP_FAILED, msg=message)
                
    # 复制文件
    copied_files = []
    for file_name in backup_dir.iterdir():
        file_name = file_name.name
        if file_name == _CHECKSUM_FILE:
            continue
        
        src_path = backup_dir / file_name
        dst_path = dir / file_name
        
        if not src_path.is_file():
            continue
        
        try:
            shutil.copyfile(src_path, dst_path)
            copied_files.append(file_name)
            
        except Exception as e:
            message = f"复制文件 {file_name} 失败: {e}"
            return Result(status=Status.RESTORE_FAILED, msg=message)
        
    message = f"{_DATA_TYPE[data_type]}恢复完成: 复制了 {len(copied_files)} 个文件到 {dir}"
    return Result(status=Status.RESTORE_SUCCESS, data=len(copied_files), msg=message)

def _create_backup_checksum(backup_dir: Path, backup_type: str) -> None:
    """为备份目录创建校验和文件"""
    checksum, file_count, total_size = _calculate_backup_checksum(backup_dir)
    checksum_data = {
        "backup_type": backup_type,
        "checksum": checksum,
        "file_count": file_count,
        "total_size": total_size,
        "created_time": datetime.now().isoformat(),
        "backup_version": "1.0"
    }

    checksum_file = backup_dir / _CHECKSUM_FILE
    with open(checksum_file, "w", encoding="utf-8") as f:
        dump(checksum_data, f, ensure_ascii=False, indent=2)

def _calculate_backup_checksum(backup_dir: Path) -> tuple[str, int, int]:
    """计算备份目录的校验和、文件数量和总大小"""
    hash_sha256 = sha256()
    file_count = 0
    total_size = 0

    # 排除校验文件本身
    excluded_files = [_CHECKSUM_FILE]

    # 遍历备份目录中的所有文件
    for root, _, files in backup_dir.walk():
        # 对文件进行排序，确保顺序一致
        for file_name in sorted(files):
            if file_name in excluded_files:
                continue

            file_path = root / file_name
            relative_path = relpath(file_path, backup_dir)

            # 更新文件计数和大小
            try:
                file_size = file_path.stat().st_size
                file_count += 1
                total_size += file_size

                # 将相对路径和文件大小加入哈希计算
                hash_sha256.update(relative_path.encode("utf-8"))
                hash_sha256.update(str(file_size).encode("utf-8"))

                # 逐块读取文件内容加入哈希计算
                with open(file_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_sha256.update(chunk)
                        
            except Exception as e:
                # 如果某个文件无法读取，继续处理其他文件
                warning(f"警告：无法读取文件 {file_path}: {e}")
                continue

    return hash_sha256.hexdigest(), file_count, total_size

def _detect_backup_type(backup_dir: Path) -> DirType:
    """检测备份类型"""
    backup_name = backup_dir.name
    KEYS, TEXTS, SIGNATURES = _get_dir_type()
    if backup_name.startswith(f"{_DATA}{_BACKUP_}"):
        return DirType.FULL
    elif backup_name.startswith(f"{KEYS}{_BACKUP_}"):
        return DirType.KEYS
    elif backup_name.startswith(f"{TEXTS}{_BACKUP_}"):
        return DirType.TEXTS
    elif backup_name.startswith(f"{SIGNATURES}{_BACKUP_}"):
        return DirType.SIGNATURES
    else:
        return _inferred_type(backup_dir)

def _get_dir_type():
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

def _get_file_type():
    """导出文件类型"""
    return (
        _utils.FileType.KEY.value,
        _utils.FileType.TEXT.value,
        _utils.FileType.SIGNATURE.value
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

def _copy_tree_excluding_checksum(src_dir: Path, dst_dir: Path) -> None:
    """递归复制目录树，排除校验和文件"""
    dst_dir.mkdir(parents=True, exist_ok=True)

    for item in src_dir.iterdir():
        item = item.name
        src_path = src_dir / item
        dst_path = dst_dir / item

        # 跳过校验和文件
        if item == _CHECKSUM_FILE:
            continue

        if src_path.is_dir():
            shutil.copytree(src_path, dst_path)
        else:
            shutil.copyfile(src_path, dst_path)

def _extract_backup_path(result: str, backup_dir: str | None = None) -> str:
    """从结果消息中提取备份路径"""
    if backup_dir:
        return backup_dir

    # 尝试从结果消息中提取路径
    if "备份完成:" in result:
        return result.split("备份完成:")[-1].strip()

    return result.strip()

def _get_directory_size(directory: Path) -> int:
    """计算目录大小"""
    total_size = 0
    for dir_path, _, file_names in directory.walk():
        for file_name in file_names:
            file_path = dir_path / file_name
            if file_path.is_file():
                total_size += file_path.stat().st_size

    return total_size
