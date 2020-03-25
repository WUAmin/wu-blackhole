# This Python file uses the following encoding: utf-8
import os
import sys

from PySide2.QtWidgets import QApplication
from appdirs import user_config_dir

from wublackholeclient5.client_config import client
from wublackholeclient5.main_window import WUBlackHoleClient


def init_confg_dir():
    # Set config directory and file
    client.config_dirpath = user_config_dir("wublackhole")
    client.config_filepath = os.path.join(client.config_dirpath, 'client_config.json')

    if os.path.exists(client.config_dirpath):  # Check if config dir exist
        if os.path.exists(client.config_filepath):  # Check if config file exist
            client.load()  # load config
        else:
            client.init_config()
        # Setup Database
        client.init_database()
    else:
        client.logger_client.warning("Config directory does not exist `{}`".format(client.config_dirpath))
        os.mkdir(client.config_dirpath)
        client.init_config()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_confg_dir()
    main_window = WUBlackHoleClient()
    # main_window.show()

    # sys.exit(app.exec_())
    # Start the event loop.
    app.exec_()

    sys.exit()
