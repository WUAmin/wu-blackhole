import base64
import os
import time

from wublackhole.helper import chacha20poly1305_encrypt_file, create_random_content_file, get_checksum_sha256_file, \
    sizeof_fmt, chacha20poly1305_decrypt_file


# Config
test_filename = "checksum_file.tmp"
test_filepath = os.path.join(os.path.split(__file__)[0], test_filename)
test_file_size = 48 * 1024 * 1024  # 48MB
password_provided = "8mwHncKVXalaBAIe"  # This is input in the form of a string
password = password_provided.encode()  # Convert to type bytes

# Create Test file
start_t = time.process_time()
create_random_content_file(test_filepath, test_file_size)
elapsed_t = time.process_time() - start_t
print("Create a {} test file in {:06f} secs...".format(sizeof_fmt(test_file_size), elapsed_t))
test_file_checksum = get_checksum_sha256_file(test_filename)






# ====  hazmat/Fernet ====
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


encrypted_test_filepath = test_filename + ".hazmat-fernet"
decrypted_test_filepath = test_filename + ".hazmat-fernet.decrypt"
# salt = b'salt_' # CHANGE THIS - recommend using a key from os.urandom(16), must be of type bytes
salt = os.urandom(16)
kdf = PBKDF2HMAC(
    algorithm=hashes.SHA256(),
    length=32,
    salt=salt,
    iterations=100000,
    backend=default_backend()
)
fernet_key = base64.urlsafe_b64encode(kdf.derive(password))  # Can only use kdf once
print("Input Size: {}  ({} MB)".format(os.stat(test_filename).st_size, os.stat(test_filename).st_size / 1024 / 1024))
start_t = time.process_time()
with open(test_filename, 'rb') as f:
    data = f.read()
fernet = Fernet(fernet_key)
encrypted = fernet.encrypt(data)
with open(encrypted_test_filepath, 'wb') as f:
    f.write(encrypted)
elapsed_t = time.process_time() - start_t
print("Encrypt - hazmat/Fernet:     {:06f} secs...".format(elapsed_t))

start_t = time.process_time()
with open(encrypted_test_filepath, 'rb') as f:
    data = f.read()
fernet = Fernet(fernet_key)
encrypted = fernet.decrypt(data)
with open(decrypted_test_filepath, 'wb') as f:
    f.write(encrypted)
elapsed_t = time.process_time() - start_t
print("Decrypt - hazmat/Fernet:     {:06f} secs...".format(elapsed_t))
decrypt_file_checksum = get_checksum_sha256_file(decrypted_test_filepath)
if test_file_checksum == decrypt_file_checksum:
    print("Checksum matches.")
else:
    print("ERROR: Mismatch checksum after encrypt/decrypt.")
os.remove(encrypted_test_filepath)
os.remove(decrypted_test_filepath)
print("\n\n")


# ==== hazmat/ChaCha20Poly1305 implemented on helper.py ====
encrypted_test_filepath = test_filename + ".ChaCha20Poly1305"
decrypted_test_filepath = test_filename + ".ChaCha20Poly1305.decrypt"
start_t = time.process_time()
key, nonce = chacha20poly1305_encrypt_file(raw_filepath=test_filepath,
                                           encrypted_filepath=encrypted_test_filepath,
                                           secret=password_provided.encode())
elapsed_t = time.process_time() - start_t
print("Encrypt - hazmat/ChaCha20Poly1305:     {:06f} secs...".format(elapsed_t))

start_t = time.process_time()
key_str = key.hex()
nonce_str = nonce.hex()
print(key_str, nonce_str)
key2 = bytes.fromhex(key_str)
nonce2 = bytes.fromhex(nonce_str)
chacha20poly1305_decrypt_file(encrypted_filepath=encrypted_test_filepath,
                              decrypted_filepath=decrypted_test_filepath,
                              secret=password_provided.encode(),
                              key=key2,
                              nonce=nonce2)
elapsed_t = time.process_time() - start_t
print("Decrypt - hazmat/ChaCha20Poly1305:     {:06f} secs...".format(elapsed_t))
decrypt_file_checksum = get_checksum_sha256_file(decrypted_test_filepath)
if test_file_checksum == decrypt_file_checksum:
    print("Checksum matches.")
else:
    print("ERROR: Mismatch checksum after encrypt/decrypt.")
os.remove(encrypted_test_filepath)
os.remove(decrypted_test_filepath)
print("\n\n")

# ==== hazmat/ChaCha20Poly1305 ====
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


encrypted_test_filepath = test_filename + ".ChaCha20Poly1305"
decrypted_test_filepath = test_filename + ".ChaCha20Poly1305.decrypt"

key = ChaCha20Poly1305.generate_key()
nonce = os.urandom(12)
start_t = time.process_time()
with open(test_filename, 'rb') as f_i:
    with open(encrypted_test_filepath, 'wb') as f_o:
        data = f_i.read()
        chacha = ChaCha20Poly1305(key)
        encrypted = chacha.encrypt(nonce, data, password)
        f_o.write(encrypted)
        # chacha.decrypt(nonce, encrypted, aad)
elapsed_t = time.process_time() - start_t
print("Encrypt - hazmat/ChaCha20Poly1305:     {:06f} secs...".format(elapsed_t))
print(f"{nonce.hex()},{key.hex()}")

start_t = time.process_time()
with open(encrypted_test_filepath, 'rb') as f_i:
    with open(decrypted_test_filepath, 'wb') as f_o:
        data = f_i.read()
        chacha = ChaCha20Poly1305(key)
        # encrypted = chacha.encrypt(nonce, data, password)
        decrypted = chacha.decrypt(nonce, data, password)
        f_o.write(decrypted)
elapsed_t = time.process_time() - start_t
print("Decrypt - hazmat/ChaCha20Poly1305:     {:06f} secs...".format(elapsed_t))
decrypt_file_checksum = get_checksum_sha256_file(decrypted_test_filepath)
if test_file_checksum == decrypt_file_checksum:
    print("Checksum matches.")
else:
    print("ERROR: Mismatch checksum after encrypt/decrypt.")
os.remove(encrypted_test_filepath)
os.remove(decrypted_test_filepath)
print("\n\n")

# ==== pycrypto - AES ====
from Crypto.Cipher import AES  # pip3 install pycrypto
from Crypto.Hash import SHA256
from Crypto import Random


encrypted_test_filepath = test_filename + ".AES"
decrypted_test_filepath = test_filename + ".AES.decrypt"

hasher = SHA256.new(password_provided.encode('utf-8'))
aes_key = hasher.digest()
start_t = time.process_time()

chunksize = 64 * 1024
filesize = str(os.path.getsize(test_filename)).zfill(16)
IV = Random.new().read(16)
encryptor = AES.new(aes_key, AES.MODE_CBC, IV)
with open(test_filename, 'rb') as infile:
    with open(encrypted_test_filepath, 'wb') as outfile:
        outfile.write(filesize.encode('utf-8'))
        outfile.write(IV)

        while True:
            chunk = infile.read(chunksize)
            if len(chunk) == 0:
                break
            elif len(chunk) % 16 != 0:
                chunk += b' ' * (16 - (len(chunk) % 16))
            outfile.write(encryptor.encrypt(chunk))
elapsed_t = time.process_time() - start_t
print("Encrypt - AES:     {:06f} secs...".format(elapsed_t))
os.remove(encrypted_test_filepath)
# os.remove(decrypted_test_filepath)

os.remove(test_filepath)
