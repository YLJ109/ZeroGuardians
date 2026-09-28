"""资源子包。"""
from .manager import ResourceManager
from .manifest import LICENSE_WHITELIST, UNKNOWN_LICENSE, license_of, is_licensed

__all__ = ["ResourceManager", "LICENSE_WHITELIST", "UNKNOWN_LICENSE", "license_of", "is_licensed"]
