import base64
import os
import time

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


test_filename = "Test-File-01.mkv"
test_filepath = os.path.join(os.path.split(__file__)[0], test_filename)

password_provided = "8mwHncKVXalaBAIe"  # This is input in the form of a string
password = password_provided.encode()  # Convert to type bytes
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

print("Input Size: {}  ({} MB)".format(os.stat(input_file).st_size, os.stat(input_file).st_size / 1024 / 1024))

# ====  hazmat/Fernet ====
start_t = time.process_time()
with open(input_file, 'rb') as f:
    data = f.read()
fernet = Fernet(fernet_key)
encrypted = fernet.encrypt(data)
with open(input_file + ".hazmat-fernet", 'wb') as f:
    f.write(encrypted)
elapsed_t = time.process_time() - start_t
print("Encrypt - hazmat/Fernet:     {:06f} secs...".format(elapsed_t))

start_t = time.process_time()
with open(input_file + ".hazmat-fernet", 'rb') as f:
    data = f.read()
fernet = Fernet(fernet_key)
encrypted = fernet.decrypt(data)
with open(input_file + ".hazmat-fernet.mkv", 'wb') as f:
    f.write(encrypted)
elapsed_t = time.process_time() - start_t
print("Decrypt - hazmat/Fernet:     {:06f} secs...".format(elapsed_t))

# ==== hazmat/ChaCha20Poly1305 ====
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305


nonce = os.urandom(12)
key = ChaCha20Poly1305.generate_key()

start_t = time.process_time()
with open(input_file, 'rb') as f_i:
    with open(input_file + ".ChaCha20Poly1305", 'wb') as f_o:
        data = f_i.read()
        chacha = ChaCha20Poly1305(key)
        encrypted = chacha.encrypt(nonce, data, password)
        f_o.write(encrypted)
        # chacha.decrypt(nonce, encrypted, aad)
elapsed_t = time.process_time() - start_t
print("Encrypt - hazmat/ChaCha20Poly1305:     {:06f} secs...".format(elapsed_t))
print(f"{nonce.hex()},{key.hex()}")

start_t = time.process_time()
with open(input_file + ".ChaCha20Poly1305", 'rb') as f_i:
    with open(input_file + ".ChaCha20Poly1305.mkv", 'wb') as f_o:
        data = f_i.read()
        chacha = ChaCha20Poly1305(key)
        # encrypted = chacha.encrypt(nonce, data, password)
        decrypted = chacha.decrypt(nonce, data, password)
        f_o.write(decrypted)
elapsed_t = time.process_time() - start_t
print("Decrypt - hazmat/ChaCha20Poly1305:     {:06f} secs...".format(elapsed_t))

# ==== pycrypto - AES ====
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto import Random


hasher = SHA256.new(password_provided.encode('utf-8'))
aes_key = hasher.digest()
start_t = time.process_time()

chunksize = 64 * 1024
filesize = str(os.path.getsize(input_file)).zfill(16)
IV = Random.new().read(16)
encryptor = AES.new(aes_key, AES.MODE_CBC, IV)
with open(input_file, 'rb') as infile:
    with open(input_file + ".AES", 'wb') as outfile:
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
