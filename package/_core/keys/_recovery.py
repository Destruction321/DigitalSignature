# package/_core/keys/_recovery.py
"""密钥恢复管理器"""
from datetime import datetime
from logging import error
from pathlib import Path
from typing import Callable, TYPE_CHECKING

from . import config
from ..._utils.constants import KEYS_CONFIG_FILE
from ..._utils.enums import DirType, FileType, KeyType, PassWord
from ..._utils.result import Status, Result
from ..._utils.tools import get_path

if TYPE_CHECKING:
    from .managers import MultiKeyManager


class KeyRecoveryManager:
    """密钥恢复管理器"""
    def __init__(self, multi_key_manager: MultiKeyManager):
        self.__multi_km: MultiKeyManager = multi_key_manager
        self.__recovery_callback: Callable[[str, PassWord], None] | None = None


    @property
    def recovery_callback(self) -> Callable[[str, PassWord], None] | None:
        return self.__recovery_callback

    @recovery_callback.setter
    def recovery_callback(self, callback: Callable[[str, PassWord], None]) -> None:
        self.__recovery_callback = callback


    """public methods"""
    def try_secure_direct_load(self) -> Result:
        """
        启动刷新列表接口
        
        Returns:
            rebuild_result (Result): 恢复结果
        """
        try:
            return self.__try_secure_direct_load()
        
        except Exception as e:
            return Result(status=Status.SYSTEM_ERROR, msg=f"重建配置失败: {str(e)}")
        
        
    def try_rebuild_from_files(self, click_btn: bool = False) -> Result:
        """
        公共备份恢复接口
        
        Returns:
            rebuild_result (Result): 恢复结果
        """
        try:
            return self.__try_rebuild_from_files(click_btn)
        
        except Exception as e:
            return Result(status=Status.SYSTEM_ERROR, msg=f"重建配置失败: {str(e)}")

    def recover_keys(self) -> bool:
        """
        二重恢复策略
        
        Returns:
            load_status (bool): 恢复结果
        """
        # 第一层：从签名JSON加载
        direct_load_result = self.__try_secure_direct_load()
        if direct_load_result.is_success:
            return True
        
        # 第二层：从文件重建
        rebuild_result = self.__try_rebuild_from_files()
        if rebuild_result.is_success:
            return True
        
        # 恢复失败：重置配置
        self.__multi_km.key_pairs = {}
        self.__multi_km.current_key_id = ""
        return False


    """private methods"""
    def __try_secure_direct_load(self) -> Result:
        """第一层：从签名JSON文件安全加载"""
        try:
            config_file_path = Path(self.__multi_km.config_file)
            
            # 检查配置文件是否存在
            if not config_file_path.exists():
                # 尝试迁移旧配置
                migrated = config.migrate_config(old_path=KEYS_CONFIG_FILE, new_path=self.__multi_km.config_file)
                if not migrated.is_success or not config_file_path.exists():
                    return Result(status=Status.FILE_NOT_FOUND, msg="配置文件不存在，迁移旧配置失败")
                    
            # 安全加载配置
            load_config_result = config.load_config(self.__multi_km.config_file, verify_integrity=True)
            if not load_config_result.is_success:
                return load_config_result
            
            config_data = load_config_result.data
            
            # 验证配置结构
            validate_result = config.validate_config_structure(config_data)
            if not validate_result.is_success:
                return validate_result
            
            # 解析配置
            self.__multi_km.key_pairs = config_data.get("key_pairs", {})
            current_key = config_data.get("current_key_id")
            self.__multi_km.current_key_id = current_key if isinstance(current_key, str) else ""
            
            # 验证配置完整性（文件存在性）
            config_integrity_result = self.__validate_config_integrity()
            return config_integrity_result
        
        except Exception as e:
            return Result(status=Status.SYSTEM_ERROR, msg=f"配置加载系统错误: {str(e)}")

    def __try_rebuild_from_files(self, click_btn: bool = False) -> Result:
        """第二层：从本地密钥文件重建配置"""
        try:
            keys_dir = Path(get_path(DirType.KEYS))

            # 检查密钥目录是否存在
            if not keys_dir.exists():
                return Result(status=Status.DIR_NOT_FOUND, msg="密钥目录不存在，无法重建配置")
            
            # 扫描密钥目录并重建配置
            rebuilt_config = {}
            recovered_encrypted_keys = []
            for file_name in keys_dir.iterdir():
                result = self.__parse_key_information(file_name.name, keys_dir)
                if result is None:
                    continue

                key_id, key_info = result

                if not Path(key_info["public_key_path"]).exists():
                    continue

                rebuilt_config[key_id] = dict(key_info)

                if key_info["is_encrypted"]:
                    recovered_encrypted_keys.append(key_id)
                    
            # 无可用密钥文件
            if not rebuilt_config:
                return Result(status=Status.KEY_FILE_MISSING)
            
            # 更新配置并保存
            self.__multi_km.key_pairs = rebuilt_config
            self.__multi_km.current_key_id = next(iter(rebuilt_config.keys()))  # 默认选中第一个
            save_result = self.__multi_km.save_keys_config()
            if not save_result.is_success:
                return save_result
            
            # 通知UI加密密钥已恢复
            if click_btn and recovered_encrypted_keys and self.__recovery_callback:
                for key_id in recovered_encrypted_keys:
                    self.__recovery_callback(key_id, PassWord.RECOVERY)
                    
            # 恢复成功
            message = f"从本地文件重建配置成功，恢复 {len(rebuilt_config)} 个密钥对"
            return Result(status=Status.SUCCESS, msg=message)
        
        except Exception as e:
            return Result(status=Status.SYSTEM_ERROR, msg=f"配置重建系统错误: {str(e)}")

    def __validate_config_integrity(self) -> Result:
        """验证配置完整性"""
        # 校验key_pairs类型
        if not isinstance(self.__multi_km.key_pairs, dict):
            return Result(status=Status.CONFIG_CORRUPT, msg="key_pairs字段必须为字典类型")
            
        # 空配置视为有效（无密钥场景）
        if not self.__multi_km.key_pairs:
            return Result(status=Status.SUCCESS)
        
        # 校验每个密钥的文件存在性
        for key_id, key_info in self.__multi_km.key_pairs.items():
            private_path = key_info.get("private_key_path", "")
            public_path = key_info.get("public_key_path", "")
            
            # 缺少路径字段
            if not private_path or not public_path:
                return Result(status=Status.CONFIG_CORRUPT, msg=f"密钥 '{key_id}' 缺少私钥/公钥路径")
                
            # 文件不存在
            if not Path(private_path).exists() or not Path(public_path).exists():
                return Result(status=Status.KEY_FILE_MISSING, msg=f"密钥 '{key_id}' 的私钥/公钥文件缺失")
            
        return Result(status=Status.SUCCESS)

    def __parse_key_information(self, file_name: str, keys_dir: Path) -> tuple[str, config.KeyPairInfo] | None:
        """从文件名解析密钥信息，返回 (key_id, key_info)"""
        try:
            PUBLIC = KeyType.PUBLIC.value
            KEY = FileType.KEY.value
            result = config.parse_key_filename(file_name)
            if result is None or not result[3]:
                return None

            key_id, key_size, is_encrypted, _ = result
            private_path = (keys_dir / file_name).resolve().as_posix()
            public_path = (keys_dir / f"{PUBLIC}_{key_id}_{key_size}{KEY}").resolve().as_posix()
            
            key_info = config.KeyPairInfo(
                private_key_path=private_path,
                public_key_path=public_path,
                key_size=key_size,
                created_time=datetime.now().isoformat(),
                is_encrypted=is_encrypted,
            )
            return key_id, key_info

        except Exception as e:
            error("密钥解析失败", f"{file_name}: {e}")
            return None
