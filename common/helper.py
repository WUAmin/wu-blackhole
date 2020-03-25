import hashlib
import logging
import os
import zlib
from base64 import b64decode, b64encode
from enum import Enum

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


class ChecksumType(Enum):
    NONE = 0
    # MD5 = 10
    # SHA1 = 20
    SHA256 = 30
    # SHA512 = 40


class EncryptionType(Enum):
    NONE = 0
    ChaCha20Poly1305 = 10
    # FERNET_SHA256 = 20
    # AES_SHA256 = 30


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


def chacha20poly1305_encrypt_data(data: bytes, secret: bytes, key: bytes = None, nonce: bytes = None):
    """
    Encrypt data using secret, key and nonce. key and nonce can be None, in that case they will be generated and
    can be obtained in return.
    :param data:
    :param secret:
    :param key:
    :param nonce:
    :return: tulip of (encrypted_data, key, nonce)
    """
    if key is None:
        key = ChaCha20Poly1305.generate_key()
    if nonce is None:
        nonce = os.urandom(12)
    chacha = ChaCha20Poly1305(key)
    return chacha.encrypt(nonce, data, secret), key, nonce


def chacha20poly1305_encrypt_file(raw_filepath: str, encrypted_filepath: str, secret: bytes, key: bytes = None,
                                  nonce: bytes = None):
    with open(raw_filepath, 'rb') as f_r:
        with open(encrypted_filepath, 'wb') as f_w:
            data = f_r.read()
            encrypted, key, nonce = chacha20poly1305_encrypt_data(data=data, secret=secret, key=key, nonce=nonce)
            f_w.write(encrypted)
            return key, nonce
    return None, None


def chacha20poly1305_decrypt_data(data: bytes, secret: bytes, key: bytes, nonce: bytes):
    chacha = ChaCha20Poly1305(key)
    return chacha.decrypt(nonce, data, secret)


def chacha20poly1305_decrypt_file(encrypted_filepath: str, decrypted_filepath: str, secret: bytes, key: bytes,
                                  nonce: bytes):
    with open(encrypted_filepath, 'rb') as f_r:
        with open(decrypted_filepath, 'wb') as f_w:
            data = f_r.read()
            decrypted = chacha20poly1305_decrypt_data(data=data, secret=secret, key=key, nonce=nonce)
            f_w.write(decrypted)
            return len(decrypted)
    return None


def compress_bytes_to_string_b64zlib(data: bytes) -> str:
    return b64encode(zlib.compress(data)).decode('ascii')


def decompress_bytes_to_string_b64zlib(string: str) -> bytes:
    return zlib.decompress(b64decode(string.encode('ascii')))
