import json
import logging
import os
import tempfile
from enum import Enum

import wublackhole


class Config:

    def __init__(self):
        # Versioning: [Major, Minor, Patch]
        self.version: list = [1, 2, 1]  # TODO: Check version difference between config.json and config.py, major/minor

        # Load from config.json
        self.core: dict = {
            "temp_dir": os.path.join(tempfile.gettempdir(), "WBH-temp"),
            "db_filepath": "config/wbh.db",
            "backup_pass": os.urandom(16).hex(),
            "blackhole_config_filename": ".__WBH__.json",
            "blackhole_queue_dirname": ".WBH_QUEUE",
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
            "chunk_size": 18874368,
            "path_check_interval": 3,
            "log": {
                "filepath": "config/blackhole.log",
                "core_level": 10,
                "bot_level": 20
            }
        }

        self.logger_core = logging.getLogger('core')
        self.logger_bot = logging.getLogger('bot')

        # Variables to keep on runtime
        self.Database = None
        self.BlackHoles: list = []
        self.TelegramBot = None
        self.config_filepath = None
        self.need_backup: bool = False

        # self.config_filepath = config_filepath
        self.init_config()

        # Load config.json if exist
        # if os.path.exists(self.config_filepath):
        #     self.load()


    def init_config(self):
        """ Generating some of config based on config.json """

        # Update log config
        # create logger with 'blackhole_core'
        console = logging.StreamHandler()
        if os.path.exists(os.path.dirname(self.core['log']['filepath'])):
            file_handler = logging.FileHandler(self.core['log']['filepath'], "wt")
            # noinspection PyArgumentList
            logging.basicConfig(level=self.core['log']['core_level'],
                                format='%(asctime)-15s: %(name)-4s: %(levelname)-7s %(message)s',
                                handlers=[file_handler, console])
        else:
            # noinspection PyArgumentList
            logging.basicConfig(level=self.core['log']['core_level'],
                                format='%(asctime)-15s: %(name)-4s: %(levelname)-7s %(message)s',
                                handlers=[console])
        self.logger_core.setLevel(self.core['log']['core_level'])
        self.logger_bot.setLevel(self.core['log']['bot_level'])


    def save(self):
        """ return true if saved config successfully to disk"""
        self.logger_core.debug("Saving config to `{}`".format(self.config_filepath))
        try:
            with open(self.config_filepath, 'w') as f:
                json.dump({
                    "version": self.version,
                    "blackholes" : [b.to_dict() for b in self.BlackHoles],
                    "core": self.core,
                }, f, sort_keys=False, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger_core.error("  ERROR: Can not save config to `{}`:\n {}".format(self.config_filepath, str(e)))
            return False
        self.logger_core.debug("  config `{}` saved.".format(self.config_filepath))
        return True


    def load(self):
        """ return true if loaded config successfully from disk"""
        # self.logger_core.debug("🕐 Loading config from `{}`".format(self.config_filepath))
        try:
            with open(self.config_filepath, 'r') as f:
                data_j = json.load(f)
                self.version = data_j['version']
                self.core = data_j['core']

                # Check BlackHoles
                self.BlackHoles = list()
                for blackhole in data_j['blackholes']:
                    self.BlackHoles.append(wublackhole.wbh_blackhole.WBHBlackHole.from_dict(blackhole))
                self.init_config()
        except Exception as e:
            self.logger_core.error(
                "  ERROR: Can not load config from `{}`:\n {}".format(self.config_filepath, str(e)))
            return False
        self.logger_core.debug("  config `{}` loaded.".format(self.config_filepath))
        return True


    def version_str(self):
        return f"{self.version[0]}.{self.version[1]}.{self.version[2]}"


class AuthLevel(Enum):
    ADMIN = 100
    MOD = 50
    USER = 20
    UNAUTHORIZED = -1


config: Config = Config()
