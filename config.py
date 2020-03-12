import json
import os
import tempfile
from enum import Enum


class Config:

    def __init__(self):
        # Versioning: [Major, Minor, Patch]
        # Change on Minor version might need config manual config check...
        self.version: list = [0, 5, 0]

        # Load from config.json
        self.core: dict = {
            "temp_dir": os.path.join(tempfile.gettempdir(), "WBH-temp"),
            "db_filename": "wbh.db",
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
            "chunk_size": 48000000,
            "path_check_interval": 3
        }

        # Variables to keep on runtime
        self.Database = None
        self.BlackHoles: list = []
        self.TelegramBot = None

        # Generating config based on config.json
        self.DataDir = os.path.join(os.path.split(os.path.realpath(__file__))[0], "config")
        self.config_file = None
        self.init_config()

        # Load config.json if exist
        if os.path.exists(self.config_file):
            self.load()


    def init_config(self):
        """ Generating some of config based on config.json """
        self.config_file = os.path.join(self.DataDir, "config.json")
        # TODO: Use list of admins insted of one ID
        self.DefaultChatID = self.core['bot']['chat_ids']['admins'][0]['id']


    def save(self):
        """ return true if saved config successfully to disk"""
        print("🕐 Saving config to `{}`".format(self.config_file))
        try:
            with open(self.config_file, 'w') as f:
                json.dump({
                    "version": self.version,
                    "core": self.core
                }, f, sort_keys=False, indent=2, ensure_ascii=False)
        except Exception as e:
            print("  ❌ ERROR: Can not save config to `{}`:\n {}".format(self.config_file, str(e)))
            return False
        print("  ✅ config saved.")
        return True


    def load(self):
        """ return true if loaded config successfully from disk"""
        print("🕐 Loading config from `{}`".format(self.config_file))
        try:
            with open(self.config_file, 'r') as f:
                data_j = json.load(f)
                self.version = data_j['version']
                self.core = data_j['core']
                self.init_config()
        except Exception as e:
            print("  ❌ ERROR: Can not load config from `{}`:\n {}".format(self.config_file, str(e)))
            return False
        print("  ✅ config loaded.")
        return True


    def version_str(self):
        return f"{self.version[0]}.{self.version[1]}.{self.version[2]}"


class AuthLevel(Enum):
    ADMIN = 100
    MOD = 50
    USER = 20
    UNAUTHORIZED = -1


config: Config = Config()
