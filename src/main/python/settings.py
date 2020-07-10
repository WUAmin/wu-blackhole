import configparser
import logging
import os
import shutil
import sys
import tempfile
# from appdirs import user_config_dir
from pathlib import Path

from wbh_bot import WBHTelegramBot
from wbh_db import WBHDatabase


class WBHSettings:
    def __init__(self):
        # initialize a ConfigParser object
        self.TelegramBot = None
        self.config = configparser.ConfigParser()

        app_dir = os.path.abspath(os.path.dirname(sys.argv[0]))

        # Variables to keep on runtime
        self.Database: WBHDatabase = None
        # self.BlackHoles: list = []
        self.TelegramBot: WBHTelegramBot = None
        self.config_filepath = os.path.join(app_dir, "config.ini")
        # self.tempdir = tempfile.mkdtemp('.wbhclient')
        self.password: str = None
        self.need_backup: bool = False

        # initial config values
        self.config['general'] = {
            "version": "2.0.0",  # Versioning: [Major, Minor, Patch]
            "tempdir": "",
            "log_level": "10",
            "db_filepath": os.path.join(app_dir, "wbh.db"),
            "keep_db_backup": "4",
            "max_download_retry": "3"
        }
        self.config['server'] = {
            "blackhole_path": "",
            "backup_pass": os.urandom(16).hex(),
            "blackhole_queue_dirname": ".WBH_QUEUE",
            "chunk_size": "18",
            "path_check_interval": "6",
            "upload_delay": "8",
        }
        self.config['telegram'] = {
            "api": "",
            "log_level": "20",
            "proxy": "",
        }

        # create logger with 'blackhole_core'
        console = logging.StreamHandler()
        file_handler = logging.FileHandler("client.log", "w")
        # noinspection PyArgumentList
        logging.basicConfig(level=self.config['telegram'].getint('log_level'),
                            format='%(asctime)-15s: %(name)-4s: %(levelname)-7s %(message)s',
                            handlers=[file_handler, console])
        self.logger_core = logging.getLogger('client')
        self.logger_bot = logging.getLogger('bot')

        # self.init_config()

        # Load config.json if exist
        # if os.path.exists(self.config_filepath):
        #     self.load()


    def init_config(self):
        """ Generating some of config based on config.json """

        # Update log config
        # # create logger with 'blackhole_core'
        # console = logging.StreamHandler()
        # if len(self.core['log']['filepath']) > 0 and os.path.exists(os.path.dirname(self.core['log']['filepath'])):
        #     file_handler = logging.FileHandler(self.core['log']['filepath'], "wt")
        #     # noinspection PyArgumentList
        #     logging.basicConfig(level=self.core['log']['core_level'],
        #                         format='%(asctime)-15s: %(name)-4s: %(levelname)-7s %(message)s',
        #                         handlers=[file_handler, console])
        # else:
        #     # noinspection PyArgumentList
        #     logging.basicConfig(level=self.core['log']['core_level'],
        #                         format='%(asctime)-15s: %(name)-4s: %(levelname)-7s %(message)s',
        #                         handlers=[console])
        self.logger_core.setLevel(self.config['general'].getint('log_level'))
        self.logger_bot.setLevel(self.config['telegram'].getint('log_level'))

        # Initial temp directory
        if self.config['general']["tempdir"] == "":
            # Create a random name temp directory on system's default temp location
            self.config['general']["tempdir"] = str(tempfile.mkdtemp('.wbhclient'))
            settings.logger_core.debug('Tempdir `{}` created.'.format(self.config['general']["tempdir"]))
        else:
            # Making sure specified temp dir exist
            try:
                Path(self.config['general']["tempdir"]).mkdir(parents=True, exist_ok=False)
                settings.logger_core.debug('Tempdir `{}` created.'.format(self.config['general']["tempdir"]))
            except FileExistsError:
                settings.logger_core.debug('Tempdir `{}` exist.'.format(self.config['general']["tempdir"]))

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
        self.logger_core.debug("Saving config to `{}`".format(self.config_filepath))
        try:
            with open(self.config_filepath, 'w') as configfile:
                # with open(self.config_filepath, 'w') as f:
                #     json.dump({
                #         "version": self.version,
                #         "client": self.client
                #     }, f, sort_keys=False, indent=2, ensure_ascii=False)
                self.config.write(configfile)
        except Exception as e:
            self.logger_core.error(
                "  ERROR: Can not save config to `{}`:\n {}".format(self.config_filepath, str(e)))
            return False
        self.logger_core.debug("  config `{}` saved.".format(self.config_filepath))
        return True


    def load(self):
        """ return true if loaded config successfully from disk"""
        # self.logger_client.debug(" Loading config from `{}`".format(self.config_filepath))
        try:
            # with open(self.config_filepath, 'r') as f:
            #     data_j = json.load(f)
            #     self.version = data_j['version']
            #     self.client = data_j['client']
            #
            #     # Older config compatibility
            #     if "max_download_retry" not in self.client:
            #         self.client["max_download_retry"] = 3
            self.config.read(self.config_filepath)
            self.init_config()
        except Exception as e:
            self.logger_core.error(
                "  ERROR: Can not load config from `{}`:\n {}".format(self.config_filepath, str(e)))
            return False
        self.logger_core.debug("  config `{}` loaded.".format(self.config_filepath))
        return True


    def init_database(self):
        if os.path.exists(settings.config['general']['db_filepath']):
            self.Database = WBHDatabase(db_path=settings.config['general']['db_filepath'], logger=self.logger_core,
                                        echo=False)
        else:
            self.Database = None


    def init_bot(self, api, proxy=None):
        if api:
            self.TelegramBot = WBHTelegramBot(api=api, logger=self.logger_bot,
                                              proxy=(proxy if len(proxy) > 0 else None),
                                              log_level=self.config['telegram'].getint('log_level'))
        else:
            self.TelegramBot = None


    def __del__(self):
        if os.path.exists(self.config['general']['tempdir']):
            shutil.rmtree(self.config['general']['tempdir'], ignore_errors=True)


settings: WBHSettings = WBHSettings()
