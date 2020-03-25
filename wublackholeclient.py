# This Python file uses the following encoding: utf-8
import os
import shutil
import sys

from PySide2.QtWidgets import QApplication
from appdirs import user_config_dir

from pyclient.client_config import client
from pyclient.main_window import WUBlackHoleClient


def init_confg_dir():
    if os.path.exists(client.config_dirpath):  # Check if config dir exist
        if os.path.exists(client.config_filepath):  # Check if config file exist
            client.load()  # load config
        else:
            client.init_config()
        # Setup Database
        client.init_database()
        # Setup Bot
        client.init_bot(client.client['bot']['api'], client.client['bot']['proxy'])
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

    # clean up
    shutil.rmtree(client.tempdir)

    sys.exit()
