# package/_utils/enums.py
"""自定义枚举"""
from enum import Enum, unique


@unique
class DirType(Enum):
    """
    目录类型枚举
    
    Attributes:
        DATA: 存放完整数据目录
        KEYS: 存放密钥的目录
        TEXTS: 存放文本文件的目录
        SIGNATURES: 存放签名文件的目录
        TEMP: 存放临时文件的目录
        UNKNOWN: 未知目录类型
    """
    DATA = "data"
    KEYS = "keys"
    TEXTS = "txts"
    SIGNATURES = "sigs"
    TEMP = "temp"
    UNKNOWN = "unknown"
    
@unique
class FileType(Enum):
    """
    文件类型枚举
    
    Attributes:
        KEY: 密钥文件
        TEXT: 文本文件
        SIGNATURE: 签名文件
    """
    KEY = ".pem"
    TEXT = ".txt"
    SIGNATURE = ".sig"

@unique
class KeyType(Enum):
    """
    密钥类型枚举
    
    Attributes:
        PRIVATE: 私有密钥
        PUBLIC: 公开密钥
        ENCRYPTED: 加密密钥
    """
    PRIVATE = "private"
    PUBLIC = "public"
    ENCRYPTED = "encrypted"

@unique
class PassWord(Enum):
    """
    需要密码的操作枚举

    Attributes:
        CHANGE: 修改密码
        RECOVERY: 恢复密码
    """
    CHANGE = "change"
    RECOVERY = "recovery"   

@unique
class Level(Enum):
    """
    日志级别枚举

    Attributes:
        DEBUG: 调试级别
        INFO: 信息级别
        WARNING: 警告级别
        ERROR: 错误级别
        CRITICAL: 严重错误级别
    """
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    