# package/_core/keys/_config.py
"""配置管理模块"""
import hmac, json
from hashlib import sha256
from os import environ
from pathlib import Path
from shutil import move
from typing import Any

from ..._utils.constants import Status, Result

"""public methods"""
def load_config(config_file: str, verify_integrity: bool = True) -> Result:
    """
    加载配置文件
    
    Args:
        config_file (str): 配置文件路径
        verify_integrity (bool): 是否验证配置完整性（默认True）
        
    Returns:
        load_result (Result): 加载结果，包含配置字典（失败时为空）
    """
    config_path = Path(config_file)
    if not config_path.exists():
        return Result(status=Status.FILE_NOT_FOUND, data={}, msg=f"配置文件不存在: {config_file}")
        
    try:
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = json.load(f)
            
        if not verify_integrity:
            return Result(status=Status.SUCCESS, data=config_data, msg="配置文件加载成功（未验证完整性）")
            
        # 验证完整性
        secret_key = _get_secret_key()
        if not _verify_config(config_data, secret_key):
            message = "配置文件完整性校验失败（可能被篡改）"
            return Result(status=Status.CONFIG_VERIFY_FAILED, data={}, msg=message)
            
        return Result(status=Status.SUCCESS, data=config_data, msg="配置文件加载并验证成功")
        
    except json.JSONDecodeError:
        return Result(status=Status.CONFIG_CORRUPT, data={}, msg=f"配置文件损坏：JSON格式错误")
        
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, data={},  msg=f"加载配置失败：权限不足: {e}")
        
    except Exception as e:
        raise Exception(f"加载配置系统错误: {str(e)}") from e

def save_config(config: dict[str, Any], config_file: str, sign: bool = True) -> Result:
    """
    保存配置文件（可带签名）
    
    Args:
        config (dict[str, Any]): 配置数据
        config_file (str): 配置文件路径
        sign (bool): 是否为配置添加数字签名（默认True）

    Returns:
        save_result (Result): 保存结果
    """
    try:
        config_path = Path(config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 签名配置
        config_to_save = config
        if sign:
            secret_key = _get_secret_key()
            config_to_save = _sign_config(secret_key, config)
            
        # 写入文件
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_to_save, f, ensure_ascii=False, indent=2)
            
        return Result(status=Status.SUCCESS, msg=f"配置文件保存成功: {config_file}")
    
    except PermissionError as e:
        return Result(status=Status.PERMISSION_DENIED, msg=f"保存配置失败：权限不足: {e}")
    
    except Exception as e:
        return Result(status=Status.CONFIG_SAVE_FAILED, msg=f"保存配置失败: {str(e)}")


def migrate_config(old_path: str, new_path: str) -> Result:
    """
    迁移配置文件（带完整性检查）
    
    Args:
        old_path (str): 旧配置文件路径
        new_path (str): 新配置文件路径

    Returns:
        migrate_result (Result): 迁移结果
    """
    old_path_obj = Path(old_path)
    new_path_obj = Path(new_path)
    if not old_path_obj.exists() and not new_path_obj.exists():
        return Result(status=Status.FILE_NOT_FOUND, msg=f"旧配置文件和新配置文件均不存在")
    
    try:
        # 加载旧配置
        old_config_result = load_config(old_path, verify_integrity=False)
        if not old_config_result.data:
            return Result(status=Status.CONFIG_CORRUPT, msg="旧配置文件为空或损坏，无法迁移")
        
        # 保存新配置
        save_result = save_config(old_config_result.data, new_path, sign=True)
        if not save_result.is_success():
            return save_result
        
        # 备份旧文件
        backup_path = f"{old_path}.migrated_backup"
        move(old_path, backup_path)
        
        message = f"配置迁移成功：{old_path} -> {new_path}\n旧文件备份为: {backup_path}"
        return Result(status=Status.SUCCESS, msg=message)
    
    except Exception as e:
        return Result(status=Status.CONFIG_SAVE_FAILED, msg=f"配置迁移失败: {str(e)}")


def validate_config_structure(config_data: dict) -> Result:
    """
    验证配置结构完整性
    
    Args:
        config_data (dict): 待验证的配置数据
        
    Returns:
        validate_result (Result): 验证结果
    """
    if not isinstance(config_data, dict):
        return Result(status=Status.CONFIG_CORRUPT, msg="配置必须是字典类型")
    
    # 校验必需字段
    required_fields = ["key_pairs", "current_key_id"]
    for field in required_fields:
        if field not in config_data:
            return Result(status=Status.CONFIG_CORRUPT, msg=f"配置缺少必需字段: {field}")
        
    # 校验key_pairs结构
    key_pairs = config_data.get("key_pairs", {})
    if not isinstance(key_pairs, dict):
        return Result(status=Status.CONFIG_CORRUPT, msg="key_pairs必须是字典类型")
    
    # 校验每个密钥的字段
    for key_id, key_info in key_pairs.items():
        if not isinstance(key_info, dict):
            return Result(status=Status.CONFIG_CORRUPT, msg=f"密钥 '{key_id}' 的信息必须是字典类型")
        
        required_key_fields = [
            "private_key_path",
            "public_key_path",
            "key_size",
            "created_time",
            "is_encrypted"
        ]
        
        for field in required_key_fields:
            if field not in key_info:
                return Result(status=Status.CONFIG_CORRUPT, msg=f"密钥 '{key_id}' 缺少字段: {field}")
            
    return Result(status=Status.SUCCESS, msg="配置结构验证通过")


"""private methods"""
def _get_secret_key() -> bytes:
    """获取密钥"""
    secret_key = environ.get("CONFIG_SECRET_KEY", "").encode()
    return secret_key if secret_key else _generate_default_key()

def _generate_default_key() -> bytes:
    """生成默认密钥（基于应用路径）"""
    app_path = str(Path(__file__).resolve())
    return sha256(app_path.encode()).digest()

def _sign_config(secret_key: bytes, config_data: dict) -> dict:
    """为配置数据添加数字签名"""
    config_hash = _calculate_config_hash(secret_key, config_data)

    signed_config = config_data.copy()
    signed_config["signature"] = config_hash
    signed_config["version"] = "1.0"  # 配置版本

    return signed_config

def _verify_config(config_data: dict, secret_key: bytes) -> bool:
    """验证配置数据的完整性"""
    if "signature" not in config_data:
        return False

    # 提取签名并创建验证用的配置副本
    stored_signature = config_data["signature"]
    config_to_verify = config_data.copy()
    config_to_verify.pop("signature", None)
    config_to_verify.pop("version", None)

    # 计算当前配置的哈希
    calculated_hash = _calculate_config_hash(secret_key, config_to_verify)

    # 使用恒定时间比较来防止时序攻击
    return hmac.compare_digest(stored_signature, calculated_hash)

def _calculate_config_hash(secret_key: bytes, config_data: dict) -> str:
    """计算配置数据的哈希值"""
    normalized_config = config_data.copy() # 规范化配置数据以确保一致的序列化

    # 移除可能变化的字段（如备份信息、临时数据等）
    fields_to_remove = ["backup_info", "_emp_data", "last_modified"]
    for field in fields_to_remove:
        normalized_config.pop(field, None)
        
    config_json = json.dumps(normalized_config, sort_keys=True, separators=(",", ":"))

    # 使用HMAC计算哈希
    hmac_obj = hmac.new(secret_key, config_json.encode("utf-8"), sha256)
    return hmac_obj.hexdigest()
