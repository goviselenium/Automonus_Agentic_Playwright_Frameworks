import re
from typing import Any, Dict, List, Union
from config.settings import settings


class SecurityMasker:
    """
    Masks sensitive values (passwords, tokens, credentials) from prompts, logs, and artifacts.
    """

    @staticmethod
    def mask_text(text: str) -> str:
        if not text or not settings.MASK_SENSITIVE_DATA:
            return text
        
        masked = text
        for key in settings.SENSITIVE_KEYS:
            # Pattern matching key-value pairs like password="secret" or password: secret
            pattern = re.compile(rf'({key}\s*[:=]\s*)(["\']?)([^"\'\s,]+)(["\']?)', re.IGNORECASE)
            masked = pattern.sub(r'\1\2********\4', masked)
        return masked

    @staticmethod
    def mask_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        if not settings.MASK_SENSITIVE_DATA:
            return data
        
        result = {}
        for k, v in data.items():
            is_sensitive = any(sk in k.lower() for sk in settings.SENSITIVE_KEYS)
            if is_sensitive and isinstance(v, str):
                result[k] = "********"
            elif isinstance(v, dict):
                result[k] = SecurityMasker.mask_dict(v)
            elif isinstance(v, list):
                result[k] = [
                    SecurityMasker.mask_dict(item) if isinstance(item, dict)
                    else (SecurityMasker.mask_text(str(item)) if isinstance(item, str) else item)
                    for item in v
                ]
            else:
                result[k] = v
        return result
