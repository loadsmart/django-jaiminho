from importlib import import_module


def format_func_path(fn, default=None):
    return f"{fn.__module__}.{fn.__name__}" if fn else default


def load_func_from_path(fn_path):
    path, method = fn_path.rsplit(".", 1)
    mod = import_module(path)
    return getattr(mod, method)
