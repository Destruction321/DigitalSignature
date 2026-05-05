# package/_core/keys/_encryption.py
"""私钥加密组件"""
from base64 import b64encode, b64decode
from secrets import token_bytes
from typing import cast

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.ciphers import Cipher
from cryptography.hazmat.primitives.ciphers.algorithms import AES
from cryptography.hazmat.primitives.ciphers.modes import CFB
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class DecryptError(ValueError):
    """私钥解密失败 -- 密码错误或解密过程异常"""
    ...


def encrypt_private_key(private_key: RSAPrivateKey, password: str) -> str:
    """
    加密私钥
    
    Args:
        private_key (RSAPrivateKey): 要加密的RSAPrivateKey对象
        password (str): 用于加密的密码
        
    Returns:
        encrypted_private_key (str): 加密后的私钥字符串
    """
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


def decrypt_private_key(encrypted_private_key: str, password: str) -> RSAPrivateKey:
    """
    解密私钥
    
    Args:
        encrypted_private_key (str): 加密的私钥字符串
        password (str): 用于解密的密码
    
    Raises:
        Error (DecryptError): 如果解密失败，抛出异常
    
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

        return cast(RSAPrivateKey, private_key)

    except Exception as e:
        raise DecryptError from e


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
