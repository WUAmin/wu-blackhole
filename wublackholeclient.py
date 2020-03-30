# This Python file uses the following encoding: utf-8
import argparse
import os
import shutil
import sys

from PySide2.QtWidgets import QApplication
from appdirs import user_config_dir

from pyclient.client_config import client
from pyclient.main_window import ClientMainWindow


def init_confg_dir():
    # Parse application arguments
    parser = argparse.ArgumentParser(description='Send everything to WU-BlackHole using Telegram Bot')
    parser.add_argument('--config', '-c',
                        help='Specify path to configuration file. (Use config.json.example as template)')
    args = parser.parse_args()
    if args.config is not None:
        # Config path is specified externally
        client.config_filepath = os.path.abspath(args.config)
    else:
        # Default config file path
        client.config_filepath = os.path.join("config", "client_config.json")
        os.makedirs("config", exist_ok=True)

    if os.path.exists(client.config_filepath):  # Check if config file exist
        client.load()  # load config
    else:
        client.init_config()
    # Setup Database
    client.init_database()
    # Setup Bot
    client.init_bot(client.client['bot']['api'], client.client['bot']['proxy'])







if __name__ == "__main__":
    app = QApplication(sys.argv)
    init_confg_dir()
    main_window = ClientMainWindow()
    # Show Window
    main_window.window.show()

    # sys.exit(app.exec_())
    # Start the event loop.
    app.exec_()

    # clean up
    shutil.rmtree(client.tempdir)

    sys.exit()
