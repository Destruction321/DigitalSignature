# package/_utils/constants.py
from enum import Enum, unique
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Any


@unique
class PASSWORD(Enum):
    CHANGE = "change"
    RECOVERY = "recovery"

@unique
class DirType(Enum):
    FULL = "full"
    KEYS = "keys"
    TEXTS = "texts"
    SIGNATURES = "signatures"
    TEMP = "temp"
    UNKNOWN = "unknown"
    
@unique
class KeyType(Enum):
    PRIVATE = "private"
    PUBLIC = "public"
    ENCRYPTED = "encrypted"
    
@unique
class Status(Enum):
    # 通用状态
    SUCCESS = ("SUCCESS", "操作成功")
    PARAM_EMPTY = ("PARAM_EMPTY", "关键参数为空")
    FILE_NOT_FOUND = ("FILE_NOT_FOUND", "文件不存在")
    DIR_NOT_FOUND = ("DIR_NOT_FOUND", "目录不存在")
    PERMISSION_DENIED = ("PERMISSION_DENIED", "权限不足")
    SYSTEM_ERROR = ("SYSTEM_ERROR", "系统错误")
    
    # 密钥相关
    KEY_NOT_FOUND = ("KEY_NOT_FOUND", "密钥不存在")
    KEY_FILE_MISSING = ("KEY_FILE_MISSING", "密钥文件缺失")
    KEY_FILE_CORRUPT = ("KEY_FILE_CORRUPT", "密钥文件损坏")
    NO_PASSWORD = ("NO_PASSWORD", "启用加密存储时需要设置密码")
    NEED_PASSWORD = ("NEED_PASSWORD", "密钥已加密，需输入密码")
    REMOVE_PASSWORD= ("REMOVE_PASSWORD", "移除加密")
    PASSWORD_ERROR = ("PASSWORD_ERROR", "密码错误")
    PASSWORD_TOO_SHORT = ("PASSWORD_TOO_SHORT", "密码长度至少6位")
    OLD_PASSWORD_ERROR = ("OLD_PASSWORD_ERROR", "旧密码验证失败")
    KEY_ID_DUPLICATE = ("KEY_ID_DUPLICATE", "密钥ID已存在")
    CURRENT_KEY_CANNOT_DELETE = ("CURRENT_KEY_CANNOT_DELETE", "当前使用的密钥无法直接删除")
    KEY_SIZE_ERROR = ("KEY_SIZE_ERROR", "无效的密钥长度")
    
    # 配置相关
    CONFIG_SAVE_FAILED = ("CONFIG_SAVE_FAILED", "配置保存失败")
    CONFIG_CORRUPT = ("CONFIG_CORRUPT", "配置文件损坏")
    CONFIG_VERIFY_FAILED = ("CONFIG_VERIFY_FAILED", "配置完整性校验失败")
    
    # 备份相关
    BACKUP_SUCCESS = ("BACKUP_SUCCESS", "备份成功")
    BACKUP_FAILED = ("BACKUP_FAILED", "备份失败")
    RESTORE_SUCCESS = ("RESTORE_SUCCESS", "恢复成功")
    RESTORE_FAILED = ("RESTORE_FAILED", "恢复失败")
    NO_BACKUP_FILE = ("NO_BACKUP_FILE", "无可用备份文件")
    BACKUP_VERIFY_SUCCESS = ("BACKUP_VERIFY_SUCCESS", "备份文件校验通过")
    BACKUP_VERIFY_FAILED = ("BACKUP_VERIFY_FAILED", "备份文件校验失败")
    
    # 清理相关
    CLEANUP_SUCCESS = ("CLEANUP_SUCCESS", "清理成功")
    CLEANUP_FAILED = ("CLEANUP_FAILED", "清理失败")
    
    # 签名相关
    SIGN_SUCCESS = ("SIGN_SUCCESS", "签名成功")
    SIGN_FAILED = ("SIGN_FAILED", "签名失败")
    VERIFY_SUCCESS = ("VERIFY_SUCCESS", "验证成功")
    VERIFY_FAILED = ("VERIFY_FAILED", "验证失败")
    SIGNATURE_FILE_MISSING = ("SIGNATURE_FILE_MISSING", "签名文件缺失")
    
    def __init__(self, code: str, desc: str):
        self.code = code
        self.desc = desc


@dataclass
class Result:
    """全系统通用操作结果结构体"""
    status: Status
    data: Any = None
    msg: str = ""
    
    
    def __post_init__(self):
        if self.msg == "":
            self.msg = self.status.desc
            
    def is_success(self) -> bool:
        """
        成功结果判断
        
        Returns:
            success (bool): 返回状态是否是成功状态中的一个
        """
        return self.status in [
            Status.SUCCESS,
            Status.BACKUP_SUCCESS,
            Status.BACKUP_VERIFY_SUCCESS,
            Status.RESTORE_SUCCESS,
            Status.CLEANUP_SUCCESS,
            Status.SIGN_SUCCESS,
            Status.VERIFY_SUCCESS
        ]
        
        
"""const"""
ENCRYPTED = "已加密"

# 数据文件夹路径
_BASE_DIR: Final[Path] = Path.cwd() / "data"

# 对外暴露的数据文件夹路径
BASE_DIR: Final[str] = str(_BASE_DIR)
    
# 目录类型
DIRS: Final[dict[DirType, Path]] = {
    DirType.FULL: _BASE_DIR,
    DirType.KEYS: _BASE_DIR / DirType.KEYS.value,
    DirType.TEXTS: _BASE_DIR / DirType.TEXTS.value,
    DirType.SIGNATURES: _BASE_DIR / DirType.SIGNATURES.value,
    DirType.TEMP: _BASE_DIR / DirType.TEMP.value
}

# 密钥配置文件名
KEYS_CONFIG_FILE: Final[str] = "keys_config.json"

# 密码最大验证次数
MAX_PASSWORD_ATTEMPTS: Final[int] = 3
