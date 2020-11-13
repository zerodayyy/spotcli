import importlib
import os

from spotcli.providers.base import Provider

# Import all providers
for _module in os.listdir(os.path.dirname(__file__)):
    if _module not in ("__init__.py") and _module.endswith(".py"):
        importlib.import_module(f".{_module[:-3]}", __name__)

__all__ = ["Provider"]
