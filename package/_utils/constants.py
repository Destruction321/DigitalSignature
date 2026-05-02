# package/_utils/constants.py
"""自定义常量"""
from pathlib import Path
from typing import Final

from .enums import DirType


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
