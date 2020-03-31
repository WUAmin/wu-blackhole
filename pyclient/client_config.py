import json
import logging
import os
import shutil
import tempfile

from appdirs import user_config_dir

from common.wbh_bot import WBHTelegramBot
# import sys
# sys.path.append('..')
from common.wbh_db import WBHDatabase


class ClientConfig:

    def __init__(self):
        # Versioning: [Major, Minor, Patch]
        # Change on Minor version might need config manual config check...
        self.version: list = [1, 3, 0]

        # Variables to keep on runtime
        self.Database: WBHDatabase = None
        self.BlackHoles: list = []
        self.TelegramBot: WBHTelegramBot = None
        self.config_filepath = os.path.join("config", "client_config.json")
        self.tempdir = tempfile.mkdtemp('.wbhclient')
        self.password: str = None

        # initial config values
        self.client: dict = {
            "db_filepath": os.path.join("config", "wbh_client.db"),
            "keep_db_backup": 4,
            "bot": {
                "api": "",
                "proxy": None,
                "chat_ids": {
                    "admins": [
                        {
                            "id": -1,
                            "name": ""
                        }
                    ],
                    "mods": [],
                    "users": []
                },
            },
            "log": {
                "client_level": 10,
                "bot_level": 20
            }
        }

        # create logger with 'blackhole_core'
        console = logging.StreamHandler()
        file_handler = logging.FileHandler("client.log", "w")
        # noinspection PyArgumentList
        logging.basicConfig(level=self.client['log']['client_level'],
                            format='%(asctime)-15s: %(name)-4s: %(levelname)-7s %(message)s',
                            handlers=[file_handler, console])
        self.logger_client = logging.getLogger('client')
        self.logger_bot = logging.getLogger('bot')

        self.init_config()

        # Load config.json if exist
        # if os.path.exists(self.config_filepath):
        #     self.load()


    def init_config(self):
        """ Generating some of config based on config.json """
        # Update log config
        self.logger_client.setLevel(self.client['log']['client_level'])
        self.logger_bot.setLevel(self.client['log']['bot_level'])

        # # Database
        # print(self.config_dirpath)
        # if self.config_dirpath:
        #     print(os.path.join(self.config_dirpath, self.client["db_filename"]))
        #     self.Database: WBHDatabase = WBHDatabase(db_path=os.path.join(self.config_dirpath,
        #                                                                   self.client["db_filename"]),
        #                                              logger=self.logger_client,
        #                                              echo=True)


    def save(self):
        """ return true if saved config successfully to disk"""
        self.logger_client.debug("Saving config to `{}`".format(self.config_filepath))
        try:
            with open(self.config_filepath, 'w') as f:
                json.dump({
                    "version": self.version,
                    "client": self.client
                }, f, sort_keys=False, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger_client.error(
                "  ERROR: Can not save config to `{}`:\n {}".format(self.config_filepath, str(e)))
            return False
        self.logger_client.debug("  config `{}` saved.".format(self.config_filepath))
        return True


    def load(self):
        """ return true if loaded config successfully from disk"""
        # self.logger_client.debug("🕐 Loading config from `{}`".format(self.config_filepath))
        try:
            with open(self.config_filepath, 'r') as f:
                data_j = json.load(f)
                self.version = data_j['version']
                self.client = data_j['client']
                self.init_config()
        except Exception as e:
            self.logger_client.error(
                "  ERROR: Can not load config from `{}`:\n {}".format(self.config_filepath, str(e)))
            return False
        self.logger_client.debug("  config `{}` loaded.".format(self.config_filepath))
        return True


    def version_str(self):
        return f"{self.version[0]}.{self.version[1]}.{self.version[2]}"


    def init_database(self):
        if os.path.exists(client.client['db_filepath']):
            self.Database = WBHDatabase(db_path=client.client['db_filepath'], logger=self.logger_client, echo=False)
        else:
            self.Database = None


    def init_bot(self, api, proxy=None):
        if api:
            self.TelegramBot = WBHTelegramBot(api=api, logger=self.logger_bot, proxy=proxy,
                                              log_level=self.client['log']['bot_level'])
        else:
            self.TelegramBot = None

    def __del__(self):
        shutil.rmtree(self.tempdir, ignore_errors=True)

client: ClientConfig = ClientConfig()
