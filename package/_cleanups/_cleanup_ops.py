# package/_cleanups/_cleanup_ops.py
"""文件清理组件，统一管理所有清理操作"""
from datetime import datetime
from json import load
from logging import error
from pathlib import Path
from typing import cast, Callable

from .._core.keys import config
from .._utils.constants import KEYS_CONFIG_FILE
from .._utils.enums import DirType, FileType, KeyType
from .._utils.result import Status, Result
from .._utils.tools import get_path
from .._utils.ui_state_manager import get_ui_state_manager


"""文件类型导出"""
_PRIVATE = KeyType.PRIVATE.value
_PUBLIC = KeyType.PUBLIC.value


"""public methods for 'CleanUps' to call"""
def cleanup_all_files(days_old: int = 30) -> Result:
    """
    执行完整清理
        
    Args:
        update_status_callback (Callable[[str], None]): 状态更新回调
        update_dir_callback (Callable[[], None]): 目录更新回调
        days_old (int): 旧文件阈值天数,默认30天
    
    Returns:
        cleanup_result (Result): 清理结果
    """
    try:
        temp_result = cleanup_temp_files()
        old_result = cleanup_old_files(days_old)
        orphaned_result = cleanup_orphaned_keys()
        
        total_deleted = 0
        message_parts = ["完整清理结果："]
        
        if temp_result.is_success and old_result.is_success and orphaned_result.is_success:
            total_deleted += temp_result.data
            message_parts.append(f"- 临时文件：清理 {temp_result.data} 个")
            
            total_deleted += old_result.data
            message_parts.append(f"- 旧文件（{days_old}天前）：清理 {old_result.data} 个")
            
            total_deleted += orphaned_result.data
            message_parts.append(f"- 孤立密钥：清理 {orphaned_result.data} 个")

        else:
            message = f"完整清理失败: \n{temp_result.msg}\n{old_result.msg}\n{orphaned_result.msg}"
            return Result(status=Status.CLEANUP_FAILED, msg=message)
        
        get_ui_state_manager().update_status(f"完整清理完成，共清理 {total_deleted} 个文件")
        
        if total_deleted == 0:
            message = "无文件需要清理"
        else:
            message = "\n".join(message_parts) 

        return Result(status=Status.CLEANUP_SUCCESS, data=total_deleted, msg=message)
        
    except Exception as e:
        return Result(status=Status.CLEANUP_FAILED, msg=f"完整清理失败: {str(e)}")

def cleanup_temp_files() -> Result:
    """
    清理临时目录中的所有文件
    
    Returns:
        cleanup_result (Result): 清理结果，成功时包含清理数量
    """
    try:
        temp_dir = Path(get_path(DirType.TEMP))
        deleted_count = _cleanup_files(temp_dir)
        if deleted_count == 0:
            return Result(status=Status.CLEANUP_SUCCESS, data=0, msg="无临时文件需要清理")
            
        message = f"清理临时文件 {deleted_count} 个"
        return Result(status=Status.CLEANUP_SUCCESS, data=deleted_count, msg=message)
        
    except Exception as e:
        return Result(status=Status.CLEANUP_FAILED, msg=f"清理临时文件失败: {str(e)}")

def cleanup_old_files(days_old: int = 30, categories: list[DirType] | None = None) -> Result:
    """
    清理指定天数前的文件
        
    Args:
        days_old (int): 清理指定天数前的文件，默认30天
        categories (list[DirType] | None): 需要清理的文件类别列表（texts, signatures, temp），默认全部类别

    Returns:
        cleanup_result (Result): 清理结果，成功时包含清理数量
    """
    if categories is None:
        categories = [DirType.TEXTS, DirType.SIGNATURES, DirType.TEMP]
         
    cutoff_time = datetime.now().timestamp() - (days_old * 24 * 60 * 60)
    total_deleted = 0
    
    try:
        for category in categories:
            dir_path = Path(get_path(category))
            deleted_count = _cleanup_files(
                dir_path, lambda file_path: Path(file_path).stat().st_mtime < cutoff_time
            )
            total_deleted += deleted_count
            
        if total_deleted == 0:
            message = f"无{days_old}天前的旧文件需要清理"
            return Result(status=Status.CLEANUP_SUCCESS, data=0, msg=message)
            
        message = f"清理{days_old}天前的旧文件 {total_deleted} 个"
        return Result(status=Status.CLEANUP_SUCCESS, data=total_deleted, msg=message)
        
    except Exception as e:
        return Result(status=Status.CLEANUP_FAILED, msg=f"清理旧文件失败: {str(e)}")

def cleanup_orphaned_keys(valid_key_ids: list[str] | None = None) -> Result:
    """
    清理孤立的密钥文件，并同步删除配置文件中的对应条目
    
    Args:
        valid_key_ids (list[str] | None): 需要保留的有效 key_id 列表，默认全部清理
            
    Returns:
        cleanup_result (Result): 清理结果，成功时包含清理数量
    """
    if valid_key_ids is None:
        valid_key_ids = []
        
    keys_dir = Path(get_path(DirType.KEYS))
    if not keys_dir.exists():
        return Result(status=Status.DIR_NOT_FOUND, msg="密钥目录不存在，无需清理")
        
    # 加载配置
    config_path = Path(keys_dir, KEYS_CONFIG_FILE)
    config_data = {}
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = load(f)
        except Exception as e:
            return Result(status=Status.CONFIG_CORRUPT, msg=f"加载配置文件失败: {e}")
            
    # 清理孤立文件
    key_files = _get_orphaned_keys(keys_dir)
    
    orphaned_key_ids, deleted_count = _del_orphaned_keys(key_files, valid_key_ids)
    if isinstance(orphaned_key_ids, Result):
        return orphaned_key_ids
    
    result = _update_config(orphaned_key_ids, config_path, cast(config.ConfigData, config_data))
    if result is not None:
        return result
    
    if deleted_count == 0:
        return Result(status=Status.CLEANUP_SUCCESS, data=0, msg="无孤立密钥文件需要清理")
        
    message = f"清理孤立密钥文件 {deleted_count} 个"
    return Result(status=Status.CLEANUP_SUCCESS, data=deleted_count, msg=message)


"""private methods"""
def _cleanup_files(dir_path: Path, condition_func: Callable[[str], bool] | None = None) -> int:
    """清理目录中的文件"""
    if not dir_path.exists():
        return 0

    deleted_count = 0
    for file_name in dir_path.iterdir():
        file_path = Path(dir_path, file_name)
        if not file_path.is_file():
            continue

        # 如果提供了条件函数，检查条件
        if condition_func and not condition_func(str(file_path)):
            continue

        try:
            file_path.unlink()
            deleted_count += 1
        except Exception as e:
            error(f"删除文件失败, {file_name}: {e}")

    return deleted_count

def _parse_key_id(file_name: str) -> tuple[str | None, bool]:
    """从文件名解析 key_id 以及是否为私钥"""
    result = config.parse_key_filename(file_name)
    if result is None:
        return None, False
    key_id, _, _, is_private = result
    return key_id, is_private


"""Auxiliary methods for 'cleanup_orphaned_keys'"""
def _get_orphaned_keys(keys_dir: Path) -> dict:
    """获取孤立密钥列表"""
    _PEM = FileType.KEY.value
    key_files = {}
    for file_path in keys_dir.iterdir():
        if file_path.suffix != _PEM:
            continue
        
        key_id, is_private = _parse_key_id(file_path.name)
        if key_id is None:
            continue
        
        key_type = _PRIVATE if is_private else _PUBLIC
        if key_id not in key_files:
            key_files[key_id] = {_PRIVATE: None, _PUBLIC: None}
            
        key_files[key_id][key_type] = file_path
        
    return key_files

def _del_orphaned_keys(key_files: dict, valid_key_ids: list[str]) -> tuple[Result | set[str], int]:
    """删除孤立密钥文件"""
    deleted_count = 0
    orphaned_key_ids: set[str] = set()
    
    for key_id, files in key_files.items():
        if key_id in valid_key_ids:
            continue
        
        has_pair = files[_PRIVATE] is not None and files[_PUBLIC] is not None
        if has_pair:
            continue
        
        for key_type in [_PRIVATE, _PUBLIC]:
            file_path = files[key_type]
            if not file_path or not file_path.exists():
                continue

            try:
                file_path.unlink()
                deleted_count += 1
                orphaned_key_ids.add(key_id)
                
            except PermissionError as e:
                message = f"删除文件 {file_path.name} 失败：权限不足"
                return Result(status=Status.PERMISSION_DENIED, msg=message), deleted_count
                
            except Exception as e:
                message = f"删除文件 {file_path.name} 失败: {e}"
                return Result(status=Status.CLEANUP_FAILED, msg=message), deleted_count
                
    return orphaned_key_ids, deleted_count

def _update_config(orphaned_key_ids: set[str], config_path: Path, config_data: config.ConfigData) -> Result | None:
    """更新配置"""
    if not orphaned_key_ids or "key_pairs" not in config_data:
        return
    
    keys_to_remove = [k for k in orphaned_key_ids if k in config_data["key_pairs"]]
    
    for key_id in keys_to_remove:
        if config_data.get("current_key_id") == key_id:
            remaining_keys = [k for k in config_data["key_pairs"].keys() if k != key_id]
            config_data["current_key_id"] = remaining_keys[0] if remaining_keys else None
            
        del config_data["key_pairs"][key_id]
        
    try:
        save_result = config.save_config(config_data, str(config_path))
        if not save_result.is_success:
            return save_result

    except Exception as e:
        return Result(status=Status.CONFIG_SAVE_FAILED, msg=f"更新配置文件失败: {e}")
