# package/_utils/constants.py
"""自定义常量"""
from pathlib import Path
from typing import Final

from .enums import DirType


ENCRYPTED = "已加密"
UNENCRYPTED = "未加密"

# 项目根文件夹路径
ROOT_DIR: Final[Path] = Path.cwd()

# 数据文件夹路径
_BASE_DIR: Final[Path] = (ROOT_DIR / "data").resolve()

# 对外暴露的数据文件夹路径
BASE_DIR: Final[str] = _BASE_DIR.as_posix()

# 日志文件夹
LOG_DIR: Final[str] = (_BASE_DIR / "logs").as_posix()

# 备份文件夹
BACKUP_DIR: Final[Path] = _BASE_DIR / "backups"

# 目录类型
DIRS: Final[dict[DirType, Path]] = {
    DirType.DATA: _BASE_DIR,
    DirType.KEYS: _BASE_DIR / DirType.KEYS.value,
    DirType.TEXTS: _BASE_DIR / DirType.TEXTS.value,
    DirType.SIGNATURES: _BASE_DIR / DirType.SIGNATURES.value,
    DirType.TEMP: _BASE_DIR / DirType.TEMP.value
}

# 密钥配置文件名
KEYS_CONFIG_FILE: Final[str] = "keys_config.json"

# 密码最大验证次数
MAX_PASSWORD_ATTEMPTS: Final[int] = 3

