# package/_core/keys/managers/_single_key_manager.py
"""单个密钥对管理器"""
from logging import exception

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey

from .. import _encryption
from ...._utils.result import Status, Result


class SingleKeyManager:
    """单个密钥对管理器"""
    def __init__(self, key_size: int = 2048, key_id: str = "") -> None:
        self.__private_key: RSAPrivateKey | None = None
        self.__public_key: RSAPublicKey | None = None
        self.__key_id: str = key_id
        self.__key_size: int = key_size

    def __str__(self) -> str:
        """提供有意义的字符串表示"""
        if self.__key_id:
            return f"SingleKeyManager(密钥ID: {self.__key_id}, 密钥长度: {self.__key_size})"
        else:
            return f"SingleKeyManager(密钥长度: {self.__key_size})"

    def __repr__(self) -> str:
        return self.__str__()


    """getters"""
    @property
    def key_id(self) -> str:
        return self.__key_id

    @property
    def key_size(self) -> int:
        return self.__key_size
    
    @property
    def private_key(self) -> RSAPrivateKey | None:
        return self.__private_key

    @property
    def public_key(self) -> RSAPublicKey | None:
        return self.__public_key

    
    """key setters"""
    @private_key.setter
    def private_key(self, private_key: RSAPrivateKey) -> None:
        self.__private_key = private_key
    
    @public_key.setter
    def public_key(self, public_key: RSAPublicKey) -> None:
        self.__public_key = public_key


    """public methods"""
    def save_keys(self, *, private_key_path: str, public_key_path: str, password: str | None = None) -> Result:
        """
        保存密钥对

        Args:
            private_key_path (str): 私钥文件路径
            public_key_path (str): 公钥文件路径
            password (str | None): 用于加密私钥的密码。Defaults to None.

        Returns:
            save_result (Result): 保存结果，包含状态和消息
        """
        if self.__private_key is None or self.__public_key is None:
            return Result(status=Status.KEY_FILE_CORRUPT, msg="密钥未初始化，无法保存")

        try:
            # 处理私钥
            if password is not None:
                encrypted_key_data = _encryption.encrypt_private_key(self.__private_key, password)
                with open(private_key_path, "w") as f:
                    f.write(encrypted_key_data)
            else:
                with open(private_key_path, "wb") as f:
                    f.write(self.__private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ))

            # 保存公钥
            with open(public_key_path, "wb") as f:
                f.write(self.__public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))

            return Result(status=Status.SUCCESS)

        except _encryption.EncryptError as e:
            return Result(status=Status.KEY_FILE_CORRUPT, msg=str(e))
        
        except PermissionError as e:
            return Result(status=Status.PERMISSION_DENIED, msg=f"权限不足: {e}")
        
        except Exception as e:
            exception("保存密钥对失败")
            return Result(status=Status.SYSTEM_ERROR, msg=str(e))
        
    def load_private_key(self, key_path: str, is_encrypted: bool, password: str | None = None) -> Result:
        """
        从文件加载私钥
        
        Args:
            key_path (str): 私钥文件路径
            password (str | None): 用于解密私钥的密码（如果私钥已加密）

        Returns:
            load_result (Result): 加载结果，成功时更新当前的私钥
        """
        try:
            if not is_encrypted:
                with open(key_path, "rb") as key_file:
                    private_key = serialization.load_pem_private_key(
                        key_file.read(), password=None, backend=default_backend()
                    )
                    
                if not isinstance(private_key, RSAPrivateKey):
                    return Result(status=Status.KEY_FILE_CORRUPT, msg="私钥文件不是RSA格式")
                
                self.__private_key = private_key
                return Result(status=Status.SUCCESS)
                
            if password is None:
                return Result(status=Status.NEED_PASSWORD)
            
            with open(key_path, "r") as key_file:
                encrypted_data = key_file.read().strip()
                
            self.__private_key = _encryption.decrypt_private_key(encrypted_data, password)
            return Result(status=Status.SUCCESS)
        
        except _encryption.PasswordError as e:
            return Result(status=Status.PASSWORD_ERROR)
        
        except _encryption.unexpected_decrypt_errors as e:
            return Result(status=Status.KEY_FILE_CORRUPT, msg=str(e))
        
        except Exception as e:
            exception("加载密钥对失败")
            return Result(status=Status.SYSTEM_ERROR, msg=str(e))

    def load_public_key(self, key_path: str) -> Result:
        """
        从文件加载公钥
        
        Args:
            key_path (str): 公钥文件路径
            
        Returns:
            load_result (Result): 加载结果，成功时更新当前的公钥
        """
        try:
            with open(key_path, "rb") as key_file:
                public_key = serialization.load_pem_public_key(key_file.read(), backend=default_backend())
                
            if not isinstance(public_key, RSAPublicKey):
                return Result(status=Status.KEY_FILE_CORRUPT, msg="公钥文件不是RSA格式")
            
            self.__public_key = public_key
            return Result(status=Status.SUCCESS)
        
        except Exception as e:
            return Result(status=Status.KEY_FILE_CORRUPT, msg=f"加载公钥失败: {str(e)}")
