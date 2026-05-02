# package/_utils/result_type.py
"""自定义返回类型"""
from dataclasses import dataclass
from enum import Enum, unique
from typing import Any


@unique
class Status(Enum):
    """系统状态枚举,包含状态码、描述和是否成功的标志"""
    # 通用状态
    SUCCESS = ("SUCCESS", "操作成功", True)
    FAILED = ("FAILED", "操作失败", False)
    PARAM_EMPTY = ("PARAM_EMPTY", "关键参数为空", False)
    FILE_NOT_FOUND = ("FILE_NOT_FOUND", "文件不存在", False)
    DIR_NOT_FOUND = ("DIR_NOT_FOUND", "目录不存在", False)
    PERMISSION_DENIED = ("PERMISSION_DENIED", "权限不足", False)
    SYSTEM_ERROR = ("SYSTEM_ERROR", "系统错误", False)

    # 密钥相关
    KEY_NOT_FOUND = ("KEY_NOT_FOUND", "密钥不存在", False)
    KEY_FILE_MISSING = ("KEY_FILE_MISSING", "密钥文件缺失", False)
    KEY_FILE_CORRUPT = ("KEY_FILE_CORRUPT", "密钥文件损坏", False)
    NO_PASSWORD = ("NO_PASSWORD", "启用加密存储时需要设置密码", False)
    CANCEL_INPUT = ("CANCEL_INPUT", "密码输入已取消", False)
    NEED_PASSWORD = ("NEED_PASSWORD", "密钥已加密，需输入密码", False)
    PASSWORD_ERROR = ("PASSWORD_ERROR", "密码错误", False)
    PASSWORD_TOO_SHORT = ("PASSWORD_TOO_SHORT", "密码长度至少6位", False)
    OLD_PASSWORD_ERROR = ("OLD_PASSWORD_ERROR", "旧密码验证失败", False)
    KEY_ID_DUPLICATE = ("KEY_ID_DUPLICATE", "密钥ID已存在", False)
    CURRENT_KEY_CANNOT_DELETE = ("CURRENT_KEY_CANNOT_DELETE", "当前使用的密钥无法直接删除", False)
    KEY_SIZE_ERROR = ("KEY_SIZE_ERROR", "无效的密钥长度", False)
    
    # 配置相关
    CONFIG_SAVE_FAILED = ("CONFIG_SAVE_FAILED", "配置保存失败", False)
    CONFIG_CORRUPT = ("CONFIG_CORRUPT", "配置文件损坏", False)
    CONFIG_VERIFY_FAILED = ("CONFIG_VERIFY_FAILED", "配置完整性校验失败", False)
    
    # 备份相关
    BACKUP_SUCCESS = ("BACKUP_SUCCESS", "备份成功", True)
    BACKUP_FAILED = ("BACKUP_FAILED", "备份失败", False)
    RESTORE_SUCCESS = ("RESTORE_SUCCESS", "恢复成功", True)
    RESTORE_FAILED = ("RESTORE_FAILED", "恢复失败", False)
    NO_BACKUP_FILE = ("NO_BACKUP_FILE", "无可用备份文件", False)
    BACKUP_VERIFY_SUCCESS = ("BACKUP_VERIFY_SUCCESS", "备份文件校验通过", True)
    BACKUP_VERIFY_FAILED = ("BACKUP_VERIFY_FAILED", "备份文件校验失败", False)
    
    # 清理相关
    CLEANUP_SUCCESS = ("CLEANUP_SUCCESS", "清理成功", True)
    CLEANUP_FAILED = ("CLEANUP_FAILED", "清理失败", False)
    
    # 签名相关
    SIGN_SUCCESS = ("SIGN_SUCCESS", "签名成功", True)
    SIGN_FAILED = ("SIGN_FAILED", "签名失败", False)
    VERIFY_SUCCESS = ("VERIFY_SUCCESS", "验证成功", True)
    VERIFY_FAILED = ("VERIFY_FAILED", "验证失败", False)
    SIGNATURE_FILE_MISSING = ("SIGNATURE_FILE_MISSING", "签名文件缺失", False)

    def __init__(self, code: str, desc: str, is_success: bool):
        self.code = code
        self.desc = desc
        self.is_success = is_success


@dataclass
class Result:
    """全系统通用操作结果结构体"""
    status: Status
    data: Any = None
    msg: str = ""
    is_success: bool = False
        
    def __post_init__(self):
        if self.msg == "":
            self.msg = self.status.desc
        
        self.is_success = self.status.is_success
