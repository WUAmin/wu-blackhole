import os
import random
import shutil
import unittest

from WuBlackHole import init_WBH, init_temp
from config import config
from wublackhole.helper import create_random_content_file
from wublackhole.wbh_db import WBHDatabase
from wublackhole.wbh_watcher import get_checksum_sha256_file, print_contents, start_watch


class TestItemRetrieval(unittest.TestCase):
    # test_filename = "retrieval_test"
    # item_ids = [61, ]

    # def test_sum_tuple(self):
    #     self.assertEqual(sum((1, 2, 2)), 6, "Should be 6")

    def test_01_load_config(self):
        # Load new config file
        config.DataDir = os.path.join(os.path.dirname(__file__), "Test-Data")
        config.config_filepath = os.path.join(os.path.dirname(__file__), "test-config.json")
        config.load()


    def test_01_load_config(self):
        # Load new config file
        config.config_filepath = os.path.join(os.path.dirname(__file__), "test-config.json")
        config.DataDir = os.path.join(os.path.dirname(__file__), "Test-Data")
        config.load()
        # config.BlackHoles.append(WBHBlackHole())


    def test_02_init_blackhole(self):
        init_WBH()
        init_temp()


    def test_03_send_file_to_blackhole(self):
        dir1 = os.path.join(config.BlackHoles[0].dirpath, "dir_{}".format(random.randint(1000, 9999)))
        dir2 = os.path.join(dir1, "dir_{}".format(random.randint(1000, 9999)))
        os.mkdir(dir1)
        os.mkdir(dir2)

        # test file /***
        create_random_content_file(os.path.join(config.BlackHoles[0].dirpath, "retrieval_test_{}"
                                                .format(random.randint(1000, 9999))), 256 * 1024)
        # test file /***
        create_random_content_file(os.path.join(config.BlackHoles[0].dirpath, "retrieval_test_{}"
                                                .format(random.randint(1000, 9999))), 512 * 1024)
        # test file /***/***
        create_random_content_file(os.path.join(dir1, "retrieval_test_{}"
                                                .format(random.randint(1000, 9999))), 1024 * 1024)
        # test file /***/***/***
        create_random_content_file(os.path.join(dir2, "retrieval_test_{}"
                                                .format(random.randint(1000, 9999))), 2 * 1024 * 1024)
        for bh in config.BlackHoles:
            start_watch(bh, 5)


    def test_04_retrieve_file_from_blackhole(self):
        for bh in config.BlackHoles:
            # bh_db = config.Database.get_blackhole_by_id(bh.id)
            items = config.Database.get_items_by_parent_id(blackhole_id=bh.id, items_parent=None)
            # print("")
            # print_contents(items)
            item: WBHDatabase.WBHDbItems
            for item in items:
                if not item.is_dir:
                    # Download file
                    chunks_db = config.Database.get_chunks_by_item_id(blackhole_id=bh.id, item_id=item.id)
                    # open file to write chunks to it
                    item_dl_filepath = os.path.join("BH-TEMP", item.filename)
                    block_size = 16384  # 16k
                    with open(item_dl_filepath, 'wb') as f_dl:
                        # download chunks via Telegram bot
                        chunk_db: WBHDatabase.WBHDbChunks
                        for chunk_db in chunks_db:
                            chunk_dl_filepath = os.path.join("BH-TEMP", chunk_db.filename)
                            config.TelegramBot.get_chunk(chunk=chunk_db, path_to_save=chunk_dl_filepath)
                            chunk_dl_checksum = get_checksum_sha256_file(chunk_dl_filepath)
                            self.assertEqual(chunk_dl_checksum, chunk_db.checksum,
                                             "checksum from db and downloaded chunk should be the same.")
                            # open chunk file to read
                            with open(chunk_dl_filepath, 'rb') as c_dl:
                                for byte_block in iter(lambda: c_dl.read(block_size), b""):
                                    f_dl.write(byte_block)
                        item_dl_checksum = get_checksum_sha256_file(item_dl_filepath)
                        self.assertEqual(item_dl_checksum, item.checksum,
                                         "checksum from db and downloaded item should be the same.")


    def test_99_delete_test_file(self):
        shutil.rmtree(config.core['temp_dir'], ignore_errors=True)
        for bh in config.BlackHoles:
            shutil.rmtree(bh.dirpath, ignore_errors=True)
        shutil.rmtree(os.path.join(config.DataDir, config.core['db_filename']), ignore_errors=True)
        shutil.rmtree(config.DataDir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
    print("Everything passed")
