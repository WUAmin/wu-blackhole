import os


def sizeof_fmt(num: int, trailing_zeros: int = 2, suffix: str = 'B', separate_prefix: bool = True) -> str:
    """ Human-Readable file size: https://stackoverflow.com/a/1094933/462606 """
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return f"%3.{trailing_zeros}f{' ' if separate_prefix else ''}%s%s" % (num, unit, suffix)
        num /= 1024.0
    return f"%.{trailing_zeros}f{' ' if separate_prefix else ''}%s%s" % (num, 'Yi', suffix)


def create_random_content_file(path: str, size: int):
    with open(path, 'wb') as f:
        size_remained = size
        while size_remained > 0:
            if size_remained >= 1048576:  # 1MB
                f.write(os.urandom(1048576))
                size_remained -= 1048576
            else:
                f.write(os.urandom(size_remained))
                size_remained -= size_remained
