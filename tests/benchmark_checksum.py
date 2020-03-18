import os
import time

from wublackhole.helper import create_random_content_file, sizeof_fmt
from wublackhole.wbh_watcher import get_checksum_sha256_file


# Config
test_filename = "checksum_file.tmp"
test_filepath = os.path.join(os.path.split(__file__)[0], test_filename)
test_file_size = 50 * 1024 * 1024  # 50MB

# Create Test file
start_t = time.process_time()
create_random_content_file(test_filepath, test_file_size)
elapsed_t = time.process_time() - start_t
print("Create a {} test file in {:06f} secs...".format(sizeof_fmt(test_file_size), elapsed_t))


sha256_tests = [
    [10, 4 * 1024, ],
    [10, 8 * 1024, ],
    [10, 16 * 1024, ],
    [10, 16 * 1024 * 1024, ],
    [10, 48 * 1024 * 1024, ],
]
# ======== Checksum - SHA256 ========
for tst in sha256_tests:
    start_t = time.process_time()
    for i in range(tst[0]):
        get_checksum_sha256_file(filepath=test_filepath, block_size=tst[1])
    elapsed_t = time.process_time() - start_t
    print("Hashed {:2d}x SHA256 Block:{}, Size:{}    {:06f} secs...".format(
        tst[0], sizeof_fmt(tst[1], trailing_zeros=0, separate_prefix=False), sizeof_fmt(test_file_size), elapsed_t))

# =========================================

# Remove test file
os.remove(test_filepath)
print("remove test file `{}`".format(test_filename))
