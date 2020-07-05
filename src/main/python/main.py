from fbs_runtime.application_context.PySide2 import ApplicationContext
from PySide2 import QtXml  # Forcefully import QtXml so pyinstaller will know that this lib must be included
# from PySide2.QtWidgets import QMainWindow, QApplication
import argparse
import os
import shutil
import sys

from main_window import MainWindow
from settings import settings


def setup_client():
    if os.path.exists(settings.config_filepath):  # Check if config file exist
        settings.load()  # load config
    else:
        settings.init_config()
    # Setup Database
    settings.init_database()
    # Setup Bot
    # settings.init_bot(client.client['bot']['api'], client.client['bot']['proxy'])


def parse_args():
    # Parse application arguments
    parser = argparse.ArgumentParser(description='Send everything to WU-BlackHole using Telegram Bot')
    parser.add_argument('--config', '-c',
                        help='Specify path to configuration file. (Use config.json.example as template)')
    args = parser.parse_args()
    if args.config is not None:
        # Config path is specified externally
        settings.config_filepath = os.path.abspath(args.config)
    else:
        # Default config file path
        settings.config_filepath = os.path.join(os.path.abspath(os.path.dirname(sys.argv[0])), "config.ini")


if __name__ == '__main__':
    appctxt = ApplicationContext()  # 1. Instantiate ApplicationContext

    # app = QApplication(sys.argv)
    parse_args()
    setup_client()

    # window = QMainWindow()
    # window.resize(250, 150)
    # window.show()

    main_window = MainWindow(appctxt.get_resource("main_window.ui"))
    # Show Window
    main_window.window.show()

    exit_code = appctxt.app.exec_()  # 2. Invoke appctxt.app.exec_()
    # # sys.exit(app.exec_())
    # # Start the event loop.
    # app.exec_()

    # clean up
    if os.path.exists(settings.config['general']['tempdir']):
        shutil.rmtree(settings.config['general']['tempdir'],  ignore_errors=True)

    sys.exit(exit_code)
