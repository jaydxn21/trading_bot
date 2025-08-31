# strategies/__init__.py
import pkgutil
import importlib

__all__ = []

# Dynamically import all strategy modules in this folder
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    module = importlib.import_module(f"{__name__}.{module_name}")
    globals()[module_name] = module
    __all__.append(module_name)
