import hashlib
import logging
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


def get_checksum_sha256(chunk: bytes, running_hash=None):
    if running_hash is None:
        running_hash = hashlib.sha256()
    running_hash.update(chunk)
    return running_hash.hexdigest()


def get_checksum_sha256_file(filepath: str, block_size: int = 16384, running_hash=None, logger: logging.Logger = None):
    """ return checksum as str if successful, None of error. Default: block of 16K"""
    if logger is None:
        logger = logging.getLogger()
    if running_hash is None:
        running_hash = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            # Read and update hash string value in blocks of 4K
            for byte_block in iter(lambda: f.read(block_size), b""):
                # running_hash.update(byte_block)
                get_checksum_sha256(chunk=byte_block, running_hash=running_hash)
    except Exception as e:
        logger.error(f"  ❌ ERROR: Can not calculate checksum for `{filepath}` :\n {str(e)}")
        return None
    return running_hash.hexdigest()


def get_checksum_sha256_folder(dirpath: str, block_size: int = 16384, running_hash=None, logger: logging.Logger = None):
    """
    return checksum as str if successful, None of error. Default: block of 16K
    :param logger:
    :param dirpath: path of the folder
    :param block_size: block sizes to read. Default is 16k
    :param running_hash: If you want to update a running hash, just pass hashlib object.
    :return: checksum hex as str on success, None of error
    """
    if logger is None:
        logger = logging.getLogger()
    if running_hash is None:
        running_hash = hashlib.sha256()
    try:
        for root, dirs, files in os.walk(dirpath):
            for names in files:
                logger.debug(" 🖩 Hashing `{}`".format(names))
                filepath = os.path.join(root, names)
                get_checksum_sha256_file(filepath=filepath, block_size=block_size, running_hash=running_hash,
                                         logger=logger)
    except Exception as e:
        logger.error(f"  ❌ ERROR: Can not calculate checksum for `{dirpath}` :\n {str(e)}")
        return None
    return running_hash.hexdigest()


def encrypt_file(filepath: str, secret: str):
    pass
