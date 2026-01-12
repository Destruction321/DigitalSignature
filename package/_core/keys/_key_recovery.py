# package/_core/keys/_key_recovery.py
"""密钥恢复管理器"""
from datetime import datetime
from pathlib import Path
from tkinter.messagebox import showerror
from typing import Callable, TYPE_CHECKING
from ..._services import config_security
from ...utils import DirType, get_path, KeyType, KEYS_CONFIG_FILE, PASSWORD
from ...utils.constants import Status, Result

if TYPE_CHECKING:
    from .key_manager import MultiKeyManager


class KeyRecoveryManager:
    """密钥恢复管理器"""
    def __init__(self, multi_key_manager: MultiKeyManager):
        self.__multi_km: MultiKeyManager = multi_key_manager
        self.__security_status_callback: Callable[[bool], None] | None = None
        self.__recovery_callback: Callable[[str, PASSWORD], None] | None = None


    @property
    def recovery_callback(self) -> Callable[[str, PASSWORD], None] | None:
        return self.__recovery_callback

    @recovery_callback.setter
    def recovery_callback(self, callback: Callable[[str, PASSWORD], None]) -> None:
        self.__recovery_callback = callback


    """public methods"""
    def try_rebuild_from_files(self) -> Result:
        """
        公共备份恢复接口
        
        Returns:
            rebuild_result (Result): 恢复结果
        """
        try:
            return self.__try_rebuild_from_files()
        
        except Exception as e:
            # 兜底捕获：防止未预料的异常崩溃
            return Result(status=Status.SYSTEM_ERROR, msg=f"重建配置失败: {str(e)}")

    def load_keys_with_recovery(self) -> bool:
        """
        二重恢复策略
        
        Returns:
            load_status (bool): 恢复结果
        """
        # 第一层：从签名JSON加载
        direct_load_result = self.__try_secure_direct_load()
        if direct_load_result.is_success():
            return True
        
        # 第二层：从文件重建
        rebuild_result = self.__try_rebuild_from_files()
        if rebuild_result.is_success():
            return True
        
        # 恢复失败：重置配置
        self.__multi_km.key_pairs = {}
        self.__multi_km.current_key_id = ""
        self.__update_security_status(False)
        return False


    """private methods"""
    def __try_secure_direct_load(self) -> Result:
        """第一层：从签名JSON文件安全加载"""
        try:
            config_file_path = Path(self.__multi_km.config_file)
            
            # 检查配置文件是否存在
            if not config_file_path.exists():
                # 尝试迁移旧配置
                migrated = config_security.migrate_config(KEYS_CONFIG_FILE, self.__multi_km.config_file)
                if not migrated.is_success() or not config_file_path.exists():
                    self.__update_security_status(False)
                    return Result(status=Status.FILE_NOT_FOUND, msg="配置文件不存在，迁移旧配置失败")
                    
            # 安全加载配置
            load_config_result = config_security.load_config(self.__multi_km.config_file, verify_integrity=True)
            if not load_config_result.is_success():
                self.__update_security_status(False)
                return load_config_result
            
            config_data = load_config_result.data
            
            # 验证配置结构
            validate_result = config_security.validate_config_structure(config_data)
            if not validate_result.is_success():
                self.__update_security_status(False)
                return validate_result
            
            # 解析配置
            self.__multi_km.key_pairs = config_data.get("key_pairs", {})
            current_key = config_data.get("current_key_id")
            self.__multi_km.current_key_id = current_key if isinstance(current_key, str) else ""
            
            # 验证配置完整性（文件存在性）
            config_integrity_result = self.__validate_config_integrity()
            self.__update_security_status(config_integrity_result.is_success())
            return config_integrity_result
        
        except Exception as e:
            self.__update_security_status(False)
            return Result(status=Status.SYSTEM_ERROR, msg=f"配置加载系统错误: {str(e)}")

    def __try_rebuild_from_files(self) -> Result:
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
                key_info = self.__parse_key_from_file_name(file_name.name, keys_dir)
                if key_info is None:
                    continue
                
                key_id, key_size, is_encrypted, private_path, public_path = key_info
                
                # 跳过无对应公钥的私钥文件
                if not Path(public_path).exists():
                    continue
                
                # 构建密钥配置信息
                rebuilt_config[key_id] = {
                    "private_key_path": private_path,
                    "public_key_path": public_path,
                    "key_size": key_size,
                    "created_time": datetime.now().isoformat(),
                    "is_encrypted": is_encrypted
                }
                
                # 记录加密密钥（用于后续回调通知）
                if is_encrypted:
                    recovered_encrypted_keys.append(key_id)
                    
            # 无可用密钥文件
            if not rebuilt_config:
                self.__update_security_status(False)
                return Result(status=Status.KEY_FILE_MISSING)
            
            # 更新配置并保存
            self.__multi_km.key_pairs = rebuilt_config
            self.__multi_km.current_key_id = next(iter(rebuilt_config.keys()))  # 默认选中第一个
            save_result = self.__multi_km.save_keys_config()
            if not save_result.is_success():
                self.__update_security_status(False)
                return save_result
            
            # 通知UI加密密钥已恢复
            if recovered_encrypted_keys and self.__recovery_callback:
                for key_id in recovered_encrypted_keys:
                    self.__recovery_callback(key_id, PASSWORD.RECOVERY)
                    
            # 恢复成功
            self.__update_security_status(True)
            message = f"从本地文件重建配置成功，恢复 {len(rebuilt_config)} 个密钥对"
            return Result(status=Status.SUCCESS, msg=message)
        
        except Exception as e:
            self.__update_security_status(False)
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

    def __update_security_status(self, is_secure: bool) -> None:
        """更新安全状态（回调通知）"""
        if self.__security_status_callback:
            self.__security_status_callback(is_secure)

    @staticmethod
    def __parse_key_from_file_name(file_name: str, keys_dir: Path) -> tuple[str, int, bool, str, str] | None:
        """从文件名解析密钥信息"""
        try:
            # 仅处理私钥文件（公钥通过私钥名推导）
            if not file_name.startswith(f"{KeyType.PRIVATE.value}_") or not file_name.endswith(".pem"):
                return None
            
            # 移除前缀和后缀
            base_name = file_name.replace(f"{KeyType.PRIVATE.value}_", "").replace(".pem", "")
            parts = base_name.split("_")
            
            # 至少需要 key_id + key_size
            if len(parts) < 2:
                return None
            
            # 解析加密状态和密钥信息
            if parts[-1] == KeyType.ENCRYPTED.value:
                is_encrypted = True
                key_size = int(parts[-2])
                key_id = "_".join(parts[:-2])
                
            else:
                is_encrypted = False
                key_size = int(parts[-1])
                key_id = "_".join(parts[:-1])
                
            # key_id不能为空
            if not key_id:
                return None
            
            # 构建文件路径
            private_path = str(keys_dir / file_name)
            public_file_name = f"{KeyType.PUBLIC.value}_{key_id}_{key_size}.pem"
            public_path = str(keys_dir / public_file_name)
            return key_id, key_size, is_encrypted, private_path, public_path
        
        except Exception as e:
            showerror("密钥解析失败", f"{file_name}: {e}")
            return None
