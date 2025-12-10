__all__ = ["find_symbol", "match", "match_file"]


def __getattr__(name):
    if name in __all__:
        from dillm import api
        return getattr(api, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
