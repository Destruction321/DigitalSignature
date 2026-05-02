# package/_utils/enums.py
"""自定义枚举"""
from enum import Enum, unique


@unique
class DirType(Enum):
    """目录类型枚举"""
    FULL = "full"
    KEYS = "keys"
    TEXTS = "texts"
    SIGNATURES = "signatures"
    TEMP = "temp"
    BACKUP = "_backup_"
    UNKNOWN = "unknown"
    
@unique
class FileType(Enum):
    """文件类型枚举"""
    KEY = ".pem"
    TEXT = ".txt"
    SIGNATURE = ".sig"

@unique
class KeyType(Enum):
    """密钥类型枚举"""
    PRIVATE = "private"
    PUBLIC = "public"
    ENCRYPTED = "encrypted"

@unique
class PassWord(Enum):
    """需要密码的操作枚举"""
    CHANGE = "change"
    RECOVERY = "recovery"   
