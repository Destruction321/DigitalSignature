# package/_core/keys/managers/_multi_key_manager.py
"""多密钥对管理模块"""
from pathlib import Path
from typing import Callable, cast, TYPE_CHECKING, TypedDict

from ._single_key_manager import SingleKeyManager
from .._config import save_config
from .._encryption import DecryptError
from .._recovery import KeyRecoveryManager
from ...._utils.constants import ENCRYPTED, KEYS_CONFIG_FILE
from ...._utils.enums import DirType, KeyType, FileType
from ...._utils.result import Status, Result
from ...._utils.tools import get_path

if TYPE_CHECKING:
    from ...._utils.enums import PassWord


class _KeyPairInfo(TypedDict):
    """密钥对键值类型"""
    private_key_path: str
    public_key_path: str
    key_size: int
    created_time: str # ISO格式
    is_encrypted: bool


class MultiKeyManager:
    """多密钥对管理模块"""
    def __init__(self, config_file: str | None = None) -> None:
        self.__key_pairs: dict[str, _KeyPairInfo] = {}
        self.__current_key_id: str | None = None

        # 加载配置
        self.__config_file: str = self.__get_config_file(config_file)

        # 初始化恢复管理器
        self.__recovery_mgr: KeyRecoveryManager = KeyRecoveryManager(cast(MultiKeyManager, self))

        # 使用恢复策略加载配置
        self.__config_secure = self.__recovery_mgr.load_keys_with_recovery()

    def __str__(self) -> str:
        """提供有意义的字符串表示"""
        key_count = len(self.__key_pairs)
        current_key = self.__current_key_id or "无"
        return f"MultiKeyManager(密钥数量: {key_count}, 当前密钥: {current_key})"

    def __repr__(self) -> str:
        return self.__str__()
    
    
    @property
    def config_secure(self) -> bool:
        return self.__config_secure

    @config_secure.setter
    def config_secure(self, value: bool) -> None:
        self.__config_secure = value

    @property
    def key_pairs(self) -> dict[str, _KeyPairInfo]:
        return self.__key_pairs

    @key_pairs.setter
    def key_pairs(self, key_pairs: dict[str, _KeyPairInfo]) -> None:
        self.__key_pairs = key_pairs

    @property
    def config_file(self) -> str:
        return self.__config_file

    @property
    def current_key_id(self) -> str | None:
        return self.__current_key_id

    @current_key_id.setter
    def current_key_id(self, value: str | None) -> None:
        self.__current_key_id = value
    
    @property
    def recovery_mgr(self) -> KeyRecoveryManager:
        return self.__recovery_mgr

    @property
    def recovery_callback(self) -> Callable[[str, PassWord], None] | None:
        return self.__recovery_mgr.recovery_callback

    @recovery_callback.setter
    def recovery_callback(self, callback: Callable[[str, PassWord], None]) -> None:
        self.__recovery_mgr.recovery_callback = callback


    """initialization helper"""
    def __get_config_file(self, config_file: str | None) -> str:
        """获取配置文件路径"""
        if config_file is not None:
            return config_file
        else:
            return get_path(DirType.KEYS, KEYS_CONFIG_FILE)


    """public methods"""
    def save_keys_config(self) -> Result:
        """
        保存密钥配置
        
        Returns:
            save_result (Result): 保存结果
        """
        config = {"key_pairs": self.__key_pairs, "current_key_id": self.__current_key_id}
        success = save_config(config, self.__config_file, sign=True)
        
        if success:
            self.__config_secure = True
            return Result(status=Status.SUCCESS)
        
        return success

    def load_key_pair(self, key_id: str, password: str | None = None) -> Result:
        """
        加载指定的密钥对
        
        Args:
            key_id (str): 密钥ID
            password (str | None): 用于解密私钥的密码（如果私钥已加密）

        Returns:
            load_result (Result): 加载结果，成功时返回当前密钥对的管理器
        """
        no_key_id = self.__no_key(key_id)
        if no_key_id:
            return no_key_id
        
        try:
            key_info = self.__key_pairs[key_id]
            l_km = SingleKeyManager(key_info["key_size"], key_id)
            
            if not Path(key_info["private_key_path"]).exists():
                message = f"私钥文件缺失: {key_info["private_key_path"]}"
                return Result(status=Status.KEY_FILE_MISSING, msg=message)
                
            if not Path(key_info["public_key_path"]).exists():
                message = f"公钥文件缺失: {key_info["public_key_path"]}"
                return Result(status=Status.KEY_FILE_MISSING, msg=message)
                
            is_encrypted = key_info.get("is_encrypted", False)
            if is_encrypted and password is None:
                return Result(status=Status.NEED_PASSWORD)
            
            load_private_result = l_km.load_private_key(key_info["private_key_path"], is_encrypted, password)
            if not load_private_result.is_success:
                return load_private_result
            
            load_public_result = l_km.load_public_key(key_info["public_key_path"])
            if not load_public_result.is_success:
                return load_public_result
            
            if self.__current_key_id != key_id:
                self.__current_key_id = key_id
                config_result = self.save_keys_config()
                if not config_result.is_success:
                    return config_result
                
            return Result(status=Status.SUCCESS, data=l_km, msg=f"密钥对 '{key_id}' 加载成功")

        except DecryptError:
            return Result(status=Status.PASSWORD_ERROR)

        except ValueError as e:
            return Result(status=Status.KEY_FILE_CORRUPT, msg=f"加载密钥失败: {str(e)}")

        except Exception as e:
            return Result(status=Status.SYSTEM_ERROR, msg=f"加载密钥系统错误: {str(e)}")

    def delete_key_pair(self, key_id: str) -> Result:
        """
        删除指定的密钥对
        
        Args:
            key_id (str): 密钥ID
            
        Returns:
            delete_result (Result): 删除结果
        """
        no_key_id = self.__no_key(key_id)
        if no_key_id:
            return no_key_id
        
        if self.__current_key_id == key_id:
            message = "当前使用的密钥无法删除，请先切换其他密钥"
            return Result(status=Status.CURRENT_KEY_CANNOT_DELETE, msg=message)
            
        try:
            key_info = self.__key_pairs[key_id]
            private_key_path = Path(key_info["private_key_path"])
            public_key_path = Path(key_info["public_key_path"])
            
            if private_key_path.exists():
                private_key_path.unlink()
            if public_key_path.exists():
                public_key_path.unlink()
                
            del self.__key_pairs[key_id]
            
            config_result = self.save_keys_config()
            if not config_result.is_success:
                return config_result
            
            return Result(status=Status.SUCCESS, msg=f"密钥对 '{key_id}' 已删除")
            
        except Exception as e:
            return Result(status=Status.KEY_FILE_CORRUPT, msg=f"删除密钥失败: {str(e)}")
            
    def change_key_password(self, key_id: str, old_password: str | None, new_password: str | None) -> Result:
        """
        更改密钥的加密密码

        Args:
            key_id (str): 密钥ID
            old_password (str | None): 旧密码（如果密钥已加密）
            new_password (str | None): 新密码（如果密钥将被加密）

        Returns:
            change_result (Result): 修改结果
        """
        no_key_id = self.__no_key(key_id)
        if no_key_id:
            return no_key_id
        
        try:
            # 加载原有密钥（验证旧密码）
            load_result = self.load_key_pair(key_id, old_password)
            if not load_result.is_success:
                # 旧密码错误单独处理
                if load_result.status == Status.PASSWORD_ERROR:
                    return Result(status=Status.OLD_PASSWORD_ERROR)
                
                return load_result
            
            key_manager = cast(SingleKeyManager, load_result.data)
            key_info = self.__key_pairs[key_id]
            private_path = Path(key_info["private_key_path"])
            public_path = Path(key_info["public_key_path"])
            key_size = key_info["key_size"]

            # 生成新路径
            new_private_path, new_public_path = self.get_key_paths(
                key_id, key_size, new_password is not None
            )
            
            # 重新保存密钥
            save_result = key_manager.save_keys(new_private_path, new_public_path, new_password)
            if not save_result.is_success:
                return save_result
            
            # 删除旧文件
            if str(private_path) != new_private_path and private_path.exists():
                private_path.unlink()
            if str(public_path) != new_public_path and public_path.exists():
                public_path.unlink()
                
            # 更新配置
            self.__key_pairs[key_id]["private_key_path"] = new_private_path
            self.__key_pairs[key_id]["public_key_path"] = new_public_path
            self.__key_pairs[key_id]["is_encrypted"] = new_password is not None
            
            # 重新加载当前密钥
            if self.__current_key_id == key_id:
                loading_result = self.load_key_pair(key_id, new_password)
                if not loading_result.is_success:
                    return loading_result
                
            # 保存配置
            config_result = self.save_keys_config()
            if not config_result.is_success:
                return config_result
            
            # 验证加密状态
            if new_password is None:
                with open(new_private_path, "r") as f:
                    content = f.read()
                    if "PRIVATE KEY" not in content:
                        message = "移除加密失败：私钥文件仍为加密格式"
                        return Result(status=Status.KEY_FILE_CORRUPT, msg=message)
                        
            status_desc = ENCRYPTED if new_password else "移除加密"
            message = f"密钥 '{key_id}' 密码更改成功（{status_desc}）"
            return Result(status=Status.SUCCESS, msg=message)
            
        except FileNotFoundError as e:
            return Result(status=Status.KEY_FILE_MISSING, msg=f"文件操作失败: {str(e)}")
            
        except PermissionError as e:
            return Result(status=Status.KEY_FILE_CORRUPT, msg=f"权限不足: {str(e)}")
        
        except Exception as e:
            return Result(status=Status.SYSTEM_ERROR, msg=f"更改密码系统错误: {str(e)}")

    def get_key_encryption_status(self, key_id: str) -> Result:
        """
        获取密钥的加密状态
        
        Args:
            key_id (str): 密钥ID
        
        Returns:
            encryption_status_result (Result): 成功状态和加密状态描述
        """
        no_key_id = self.__no_key(key_id)
        if no_key_id:
            return no_key_id
        
        is_encrypted = self.__key_pairs[key_id].get("is_encrypted", False)
        status_desc = ENCRYPTED if is_encrypted else "未加密"
        
        return Result(status=Status.SUCCESS, data=is_encrypted, msg=status_desc)

    def get_key_paths(self, key_id: str, key_size: int, is_encrypted: bool = False) -> tuple[str, str]:
        """
        获取指定密钥ID的文件路径
        
        Args:
            key_id (str): 密钥ID
            key_size (int): 密钥长度
            is_encrypted (bool): 私钥是否加密

        Returns:
            (private_key_path, public_key_path) (tuple[str, str]): 私钥和公钥的文件路径
        """
        
        PRIVATE_, PUBLIC_, _ENCRYPTED, _PEM = _get_consts(is_encrypted)
        private_key_file = f"{PRIVATE_}{key_id}_{key_size}{_ENCRYPTED}{_PEM}"
        public_key_file = f"{PUBLIC_}{key_id}_{key_size}{_PEM}"

        keys_dir = get_path(DirType.KEYS)
        return (
            str(Path(keys_dir, private_key_file)),
            str(Path(keys_dir, public_key_file))
        )


    """private methods"""
    def __no_key(self, key_id: str) -> Result | None:
        """检查密钥存在性"""
        if not key_id.strip():
            return Result(status=Status.PARAM_EMPTY)
        if key_id not in self.__key_pairs:
            return Result(status=Status.KEY_NOT_FOUND)
        

def _get_consts(is_encrypted: bool = False) -> tuple[str, str, str, str]:
    """字符串导出"""
    return (
        f"{KeyType.PRIVATE.value}_",
        f"{KeyType.PUBLIC.value}_",
        f"_{KeyType.ENCRYPTED.value}" if is_encrypted else "",
        FileType.KEY.value
    )
