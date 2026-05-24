# package/_backups/backup_list_type.py
"""备份列表类型定义"""
from typing import NotRequired, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


class _ChecksumData(TypedDict):
    """备份校验和数据类型"""
    backup_type: str
    checksum: str
    file_count: int
    total_size: int
    created_time: str
    backup_version: str

class BackupItem(TypedDict):
    """
    备份条目类型
    
    Attributes:
        name (str): 备份名称
        path (Path): 备份路径
        created_time (datetime): 创建时间
        size (int): 备份大小
    
        integrity_valid (bool, optional): 完整性验证结果
        integrity_message (str, optional): 完整性验证消息
        checksum_data (_ChecksumData, optional): 校验和数据
    """
    name: str
    path: Path
    created_time: datetime
    size: int
    integrity_valid: NotRequired[bool]
    integrity_message: NotRequired[str]
    checksum_data: NotRequired[_ChecksumData]
    
type BackupList = list[BackupItem]
