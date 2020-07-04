import os
import shutil
import sys
import tempfile
import unittest

from PySide2.QtWidgets import QApplication

from WuBlackHole import setup_app
from common.helper import EncryptionType, create_random_content_file, json_value_escape_string, \
    get_checksum_sha256_file, get_checksum_sha256_folder, get_path_size
from common.wbh_db import WBHDbItems
from config import config
from pyclient.client_config import client
from pyclient.main_window import ClientMainWindow
from pyclient.restore_backup_window import RestoreBackupDialog
from wublackhole.wbh_blackhole import WBHBlackHole
from wublackhole.wbh_queue import WBHQueue
from wublackhole.wbh_watcher import start_watch
from wublackholeclient import setup_client


class TestItemRetrieval(unittest.TestCase):
    config.test_id = os.urandom(2).hex().upper()
    config.test_dir = tempfile.mkdtemp(prefix='wbh-test-{}_'.format(config.test_id))
    client.dl_dir = os.path.join(config.test_dir, "download")
    config.tf_ue = []
    config.tf_e = []
    config.tf_d = []


    def test_000_generate_config(self):
        # Generate config from config.json.example
        with open(os.path.join('config', 'config.json.example'), 'rt') as cje_f:
            cj = cje_f.read()
            cj = cj.replace('"BLACKHOLE-DIRECTORY-PATH"',
                            '"{}"'.format(json_value_escape_string(
                                os.path.join(config.test_dir, 'test-{}'.format(config.test_id)))))
            cj = cj.replace('"BLACKHOLE-NAME"', '"test-{}"'.format(config.test_id))
            cj = cj.replace('"NONE or ChaCha20Poly1305"', '"NONE"')
            cj = cj.replace('"PASSWORD-TO-RECOVER-YOUR-FILES"', 'null')
            cj = cj.replace('"000000"', '"{}"'.format(os.environ['WBHTESTTID']))
            cj = cj.replace('".temp"',
                            '"{}"'.format(json_value_escape_string(
                                os.path.join(config.test_dir, 'test-{}-temp'.format(config.test_id)))))
            cj = cj.replace('"config/wbh.db"',
                            '"{}"'.format(json_value_escape_string(
                                os.path.join(config.test_dir, 'wbh-{}.db'.format(config.test_id)))))
            cj = cj.replace('"PASSWORD-TO-RECOVER-DATABASE-FILE-BLACKHOLE"', '"{}"'.format(config.test_id))
            cj = cj.replace('"YOUR-BOT-API"', '"{}"'.format(os.environ['WBHTESTTAPI']))
            cj = cj.replace('"proxy_url": null', '"proxy_url": null')
            cj = cj.replace(': 6', ': 1')
            cj = cj.replace(': 20', ': 40')
            cj = cj.replace(': 30', ': 40')
            with open(os.path.join(config.test_dir, 'test-{}-config.json'.format(config.test_id)), 'wt') as cj_f:
                cj_f.write(cj)


    def test_010_load_config(self):
        # Load new config file
        config.config_filepath = os.path.join(config.test_dir, 'test-{}-config.json'.format(config.test_id))
        config.load()
        self.assertEqual(config.core['bot']['api'], os.environ['WBHTESTTAPI'],
                         "API didn't match with WBHTESTTAPI environment variable value")
        self.assertEqual(config.BlackHoles[0].telegram_id, os.environ['WBHTESTTID'],
                         "telegram_id of first blackhole didn't match with WBHTESTTID environment variable value")


    def test_020_add_encrypted_blackhole(self):
        cloned_bh: WBHBlackHole = WBHBlackHole.from_dict(config.BlackHoles[0].to_dict())
        cloned_bh.encryption_type = EncryptionType.ChaCha20Poly1305
        cloned_bh.encryption_pass = '{0}{0}'.format(config.test_id)
        cloned_bh.name = 'test-{}_{}'.format(config.test_id, cloned_bh.encryption_type.name)
        cloned_bh.dirpath = os.path.join(config.test_dir,
                                         'test-{}_{}'.format(config.test_id, cloned_bh.encryption_type.name))
        config.BlackHoles.append(cloned_bh)
        self.assertEqual(len(config.BlackHoles), 2, "Config should have 2 blackholes")

    def test_030_save_config(self):
        # Load new config file
        config.save()

    def test_040_setup_app(self):
        try:
            setup_app()
        # except ExpectedException:
        #     pass
        except Exception as e:
            self.fail('unexpected exception raised on setup_app()')
        # else:
        #     self.fail('ExpectedException not raised')


    def test_050_bot(self):
        bh: WBHBlackHole
        for bh in config.BlackHoles:
            config.TelegramBot.send_msg(chat_id=bh.telegram_id,
                                        text="Test {}\nBlackhole: *{}*".format(config.test_id, bh.name))


    def test_060_upload_to_unencrypted_blackhole(self):
        # mkdir /dirname1
        dirname1 = os.path.join(config.BlackHoles[0].dirpath, "D-1")
        # mkdir /dirname2
        dirname2 = os.path.join(config.BlackHoles[0].dirpath, "D-2")
        # mkdir /dirname2/dirname3
        dirname3 = os.path.join(dirname2, "D-3")
        os.makedirs(dirname1, exist_ok=True)
        os.makedirs(dirname2, exist_ok=True)
        os.makedirs(dirname3, exist_ok=True)
        config.tf_ue = [
            [os.path.join(config.BlackHoles[0].dirpath, "F-{}_256KB".format(os.urandom(2).hex())), 256 * 1024, None],
            [os.path.join(config.BlackHoles[0].dirpath, "F-{}_24MB".format(os.urandom(2).hex())), 24 * 1024 * 1024,
             None],
            [os.path.join(dirname1, "F-{}_512KB".format(os.urandom(2).hex())), 512 * 1024, None],
            [os.path.join(dirname2, "F-{}_768KB".format(os.urandom(2).hex())), 768 * 1024, None],
            [os.path.join(dirname3, "F-{}_1MB".format(os.urandom(2).hex())), 1024 * 1024, None],
        ]
        # Create files
        for test_file in config.tf_ue:
            create_random_content_file(test_file[0], test_file[1])
        # copy first file for later duplicate check
        config.tf_d.append([os.path.join(config.test_dir, os.path.split(config.tf_ue[0][0])[1]), 256 * 1024, None])
        config.tf_d.append([os.path.join(config.test_dir, os.path.split(config.tf_ue[0][0])[1]), 256 * 1024, None])
        shutil.copy(config.tf_ue[0][0], config.tf_d[0][0])
        # process blackhole 0
        start_watch(config.BlackHoles[0])
        start_watch(config.BlackHoles[0])  # Another round to trigger upload db backup

        # Check database for items and their file_id
        for tf in config.tf_ue:
            tf[2] = config.Database.get_items_by_filename(blackhole_id=config.BlackHoles[0].id,
                                                          filename=os.path.split(tf[0])[1])

        for tf in config.tf_ue:
            self.assertEqual(os.path.split(tf[0])[1], tf[2][0].filename, "item filename does not match with db")
            self.assertEqual(tf[1], tf[2][0].size, "item size does not match with db")

    def test_070_upload_to_encrypted_blackhole(self):
        config.tf_e.append(
            [os.path.join(config.BlackHoles[1].dirpath, "FE-{}_1MB".format(os.urandom(2).hex())), 256 * 1024, None])
        config.tf_e.append(
            [os.path.join(config.BlackHoles[1].dirpath, "FE-{}_24MB".format(os.urandom(2).hex())), 24 * 1024 * 1024,
             None])

        # Create files
        for test_file in config.tf_e:
            create_random_content_file(test_file[0], test_file[1])

        # process blackhole 1
        start_watch(config.BlackHoles[1])
        start_watch(config.BlackHoles[1])  # Another round to trigger upload db backup

        # Check database for items and their file_id
        for tf in config.tf_e:
            tf[2] = config.Database.get_items_by_filename(blackhole_id=config.BlackHoles[1].id,
                                                          filename=os.path.split(tf[0])[1])

        for tf in config.tf_e:
            self.assertEqual(os.path.split(tf[0])[1], tf[2][0].filename, "item filename does not match with db")
            self.assertEqual(tf[1], tf[2][0].size, "item size does not match with db")


    def test_100_load_client(self):
        QApplication(sys.argv)
        # init client
        client.mw: ClientMainWindow = ClientMainWindow()
        # Set password
        client.config_filepath = os.path.join(config.test_dir, "client_config.json")
        client.client['bot']['api'] = os.environ['WBHTESTTAPI']
        client.client['log']['client_level'] = 40
        client.client['log']['bot_level'] = 40
        client.save()
        setup_client()
        # client.password = config.BlackHoles[0].encryption_pass
        # Create download directory
        os.makedirs(client.dl_dir, exist_ok=True)



    def test_110_backup_restore_db_from_blackhole(self):
        dbb = WBHQueue.backup_database(blackhole=config.BlackHoles[0])
        self.assertGreater(len(dbb), 0, "Problem on database backup")

        rb_window = RestoreBackupDialog(db_code=''.join(dbb), no_gui=True, password=config.core['backup_pass'])
        # Close database file to avoid file lock on windows
        client.Database.Session.close_all()
        client.Database.conn.close()
        res = rb_window.restore_pb_clicked()
        self.assertEqual(res, True, "Problem on database restoration")


    def test_120_get_blackholes(self):
        # get all blackholes
        bhs = config.Database.get_blackholes()
        self.assertEqual(len(bhs), 2, "There should be 2 blackholes")


    def test_130_download_from_unencrypted_blackhole(self):
        # Get items from unencrypted blackhole
        db_items = config.Database.get_items_by_parent_id(blackhole_id=config.BlackHoles[0].id,
                                                          items_parent=None)

        itm: WBHDbItems
        for itm in db_items:
            db_itm = config.Database.get_item_by_id(blackhole_id=config.BlackHoles[0].id,
                                                    item_id=itm.id)
            if itm.is_dir:
                # Folder
                dir_path = os.path.join(client.dl_dir, itm.filename)
                client.mw.download_folder(item_id=itm.id,
                                          blackhole_id=config.BlackHoles[0].id,
                                          save_to=dir_path,
                                          ask_rewrite=False,
                                          use_msg_box=False)
                self.assertEqual(itm.checksum, get_checksum_sha256_folder(dirpath=dir_path), "Checksum did not match")
                self.assertEqual(itm.size, get_path_size(dir_path), "Size did not match")
            else:
                # File
                file_path = os.path.join(client.dl_dir, itm.filename)
                client.mw.download_file(item_id=itm.id,
                                        blackhole_id=config.BlackHoles[0].id,
                                        save_to=file_path,
                                        ask_rewrite=False,
                                        use_msg_box=False)
                self.assertEqual(itm.checksum, get_checksum_sha256_file(filepath=file_path), "Checksum did not match")
                self.assertEqual(itm.size, get_path_size(file_path), "Size did not match")


    def test_130_download_from_encrypted_blackhole(self):
        # Get items from unencrypted blackhole
        db_items = config.Database.get_items_by_parent_id(blackhole_id=config.BlackHoles[1].id,
                                                          items_parent=None)
        # blackhole encryption password
        client.password = config.BlackHoles[1].encryption_pass
        itm: WBHDbItems
        for itm in db_items:
            db_itm = config.Database.get_item_by_id(blackhole_id=config.BlackHoles[1].id,
                                                    item_id=itm.id)
            if itm.is_dir:
                # Folder
                pass
                dir_path = os.path.join(client.dl_dir, itm.filename)
                client.mw.download_folder(item_id=itm.id,
                                          blackhole_id=config.BlackHoles[1].id,
                                          save_to=dir_path,
                                          ask_rewrite=False)
                self.assertEqual(itm.checksum, get_checksum_sha256_folder(dirpath=dir_path), "Checksum did not match")
                self.assertEqual(itm.size, get_path_size(dir_path), "Size did not match")
            else:
                # File
                file_path = os.path.join(client.dl_dir, itm.filename)
                client.mw.download_file(item_id=itm.id,
                                        blackhole_id=config.BlackHoles[1].id,
                                        save_to=file_path,
                                        ask_rewrite=False,
                                        use_msg_box=False)
                self.assertEqual(itm.checksum, get_checksum_sha256_file(filepath=file_path), "Checksum did not match")
                self.assertEqual(itm.size, get_path_size(file_path), "Size did not match")


    def test_999_delete_test_file(self):
        shutil.rmtree(config.test_dir, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
    print("Everything passed")
