# package/_core/keys/_encryption.py
"""私钥加密组件"""
from base64 import b64encode, b64decode
from secrets import token_bytes

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CFB
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


"""自定义加密与解密异常类"""
class EncryptError(Exception):
    """加密失败"""
    ...

class DecryptError(Exception):
    """解密失败基类"""
    ...

class PasswordError(DecryptError):
    """密码错误"""
    ...

class InvalidKeyError(DecryptError):
    """解密后数据不是有效的RSA私钥"""
    ...


def encrypt_private_key(private_key: RSAPrivateKey, password: str) -> str:
    """
    加密私钥
    
    Args:
        private_key (RSAPrivateKey): 要加密的RSAPrivateKey对象
        password (str): 用于加密的密码
        
    Raises:
        Error (EncryptError): 如果加密失败，抛出异常
    
    Returns:
        encrypted_private_key (str): 加密后的私钥字符串
    """
    try:
        salt = token_bytes(16)
        iv = token_bytes(16)

        key = _derive_key(password, salt)

        private_key_bytes = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        cipher = Cipher(AES(key), CFB(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        encrypted_data = encryptor.update(private_key_bytes) + encryptor.finalize()

        combined_data = salt + iv + encrypted_data

        return b64encode(combined_data).decode("utf-8")
    
    except Exception as e:
        raise EncryptError("私钥加密失败" + str(e)) from e


def decrypt_private_key(encrypted_private_key: str, password: str) -> RSAPrivateKey:
    """
    解密私钥
    
    Args:
        encrypted_private_key (str): 加密的私钥字符串
        password (str): 用于解密的密码
    
    Raises:
        PasswordError (PasswordError): 密码错误或数据损坏
        DecryptError (DecryptError): 其他异常
    
    Returns:
        decrypted_private_key (RSAPrivateKey): 解密后的RSAPrivateKey对象
    """
    try:
        combined_data = b64decode(encrypted_private_key)
        
        salt = combined_data[:16]
        iv = combined_data[16:32]
        encrypted_data = combined_data[32:]
        
        key = _derive_key(password, salt)
        
        cipher = Cipher(AES(key), CFB(iv), backend=default_backend())
        decryptor = cipher.decryptor()
        private_key_bytes = decryptor.update(encrypted_data) + decryptor.finalize()
        
        private_key = serialization.load_pem_private_key(
            private_key_bytes,
            password=None,
            backend=default_backend()
        )
        if not isinstance(private_key, RSAPrivateKey):
            raise InvalidKeyError("解密后的数据不是有效的RSA私钥")

    except ValueError as e:
        raise PasswordError("密码错误或数据损坏") from e

    except Exception as e:
        raise DecryptError("解密过程发生未知错误：" + str(e)) from e

    return private_key


def _derive_key(password: str, salt: bytes) -> bytes:
    """从密码派生加密密钥"""
    kdf = PBKDF2HMAC(
        algorithm=SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode("utf-8"))
