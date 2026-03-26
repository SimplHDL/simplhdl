try:
    from importlib.resources import files as resources_files
except ImportError:
    from importlib_resources import files as resources_files

__all__ = ["resources_files"]
