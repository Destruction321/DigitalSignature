# package/_backups/_backup_utils/ops.py
"""统一备份服务"""
from shutil import rmtree
from json import load
from pathlib import Path
from typing import Any, Callable, Final

from . import _internal
from ..._utils.enums import DirType
from ..._utils.result import Status, Result
from ..._utils.tools import format_size, get_path


"""操作映射"""
_BACKUP_OPERATIONS: Final[dict[DirType, Callable[[str | None], Result]]] = {
    DirType.FULL: lambda backup_dir=None: _internal.backup_data(DirType.FULL, backup_dir),
    DirType.KEYS: lambda backup_dir=None: _internal.backup_data(DirType.KEYS, backup_dir),
    DirType.TEXTS: lambda backup_dir=None: _internal.backup_data(DirType.TEXTS, backup_dir),
    DirType.SIGNATURES: lambda backup_dir=None: _internal.backup_data(DirType.SIGNATURES, backup_dir)
}

_RESTORE_OPERATIONS: Final[dict[DirType, Callable[[Path, Any, bool], Result]]] = {
    DirType.FULL: lambda bd, dd, ov: _internal.restore_full_backup(bd, dd, ov),
    DirType.KEYS: lambda bd, dd, ov: _internal.restore_partial_backup(bd, dd, ov),
    DirType.TEXTS: lambda bd, dd, ov: _internal.restore_partial_backup(bd, dd, ov),
    DirType.SIGNATURES: lambda bd, dd, ov: _internal.restore_partial_backup(bd, dd, ov)
}


"""methods"""
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
    backup_path = _internal.extract_backup_path(backup_result.msg, backup_dir)
    if backup_path and Path(backup_path).exists():
        try:
            _internal.create_backup_checksum(Path(backup_path), backup_type.value)
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
        return backups

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

    checksum_file = backup_dir / _internal.CHECKSUM_FILE

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
        current_checksum, current_file_count, current_total_size = _internal.calculate_backup_checksum(backup_dir)
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

        message = f"备份完整性验证通过（{backup_type}，{file_count}个文件，{format_size(total_size)}）"
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
        _internal.get_backups(backups, current_dir)
        backups.sort(key=lambda x: x["created_time"], reverse=True)
        return Result(status=Status.SUCCESS, data=backups)

    except FileNotFoundError:
        return Result(status=Status.NO_BACKUP_FILE, data=[], msg="没有找到备份目录")
    
    except PermissionError:
        return Result(status=Status.PERMISSION_DENIED, data=[], msg="权限不足，无法访问备份目录")
    
    except Exception as e:
        return Result(status=Status.FAILED, data=[], msg=f"列出备份时发生错误: {e}")

def restore_backup(backup_dir: Path, overwrite: bool = False) -> Result:
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
    backup_type = _internal.detect_backup_type(backup_dir)
        
    if backup_type == DirType.UNKNOWN:
        return Result(status=Status.PARAM_EMPTY, msg="无法检测备份类型")
        
    # 执行恢复
    operation = _RESTORE_OPERATIONS.get(backup_type)
    if not operation:
        return Result(status=Status.PARAM_EMPTY, msg=f"不支持的备份类型: {backup_type.value}")
        
    try:
        if backup_type == DirType.FULL:
            restore_result = operation(backup_dir, Path(get_path(DirType.FULL)), overwrite)
        else:
            restore_result = operation(backup_dir, backup_type, overwrite)
        return restore_result
    
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"恢复失败：权限不足: {e}")
        
    except Exception as e:
        return Result(status=Status.SYSTEM_ERROR, msg=f"恢复系统错误: {e}")

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
            
        if not backup_path.is_dir() or not any(pattern in backup_name for pattern in [_internal.BACKUP]):
            return Result(status=Status.PARAM_EMPTY, msg=f"'{backup_name}' 不是有效的备份目录")
            
        rmtree(backup_path)
        return Result(status=Status.SUCCESS, msg=f"备份 '{backup_name}' 已成功删除")
        
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"删除失败：权限不足: {e}")
        
    except Exception as e:
        return Result(status=Status.SYSTEM_ERROR, msg=f"删除备份系统错误: {e}")
