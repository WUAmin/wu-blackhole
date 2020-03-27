#!/usr/bin/python3from config import config

# -*- coding: utf-8 -*-
import argparse
import os

from common.wbh_bot import WBHTelegramBot
from common.wbh_db import WBHDatabase
from config import config
from wublackhole.wbh_blackhole import WBHBlackHole
from wublackhole.wbh_watcher import start_watch


def init_temp():
    # Clear leftover of old temp files
    files = os.listdir(config.core['temp_dir'])
    t_i = 0
    for file in files:
        if file.startswith("WBHTF"):
            ext = os.path.splitext(file)[1]
            if len(ext) == 6 and ext.startswith(".p"):
                try:
                    os.remove(os.path.join(config.core['temp_dir'], file))
                    t_i += 1
                except:
                    config.logger_core.error("❌ Error while deleting file : ",
                                             os.path.join(config.core['temp_dir'], file))
    if t_i > 0:
        config.logger_core.debug(f"⚠️ {t_i} old temp files deleted.")


def init_WBH():
    # Check/Create BlackHole Data Directory
    if not os.path.exists(config.DataDir):
        os.makedirs(config.DataDir)

    # Database
    config.Database = WBHDatabase(os.path.join(config.DataDir, config.core['db_filename']), config.logger_core, False)

    # initialize Blackhole IDs
    bh: WBHBlackHole
    for bh in config.BlackHoles:
        if bh.id is None:
            bh.init_id()

    # Check/Create BlackHole Temp Directory
    if not os.path.exists(config.core['temp_dir']):
        config.logger_core.warning(f"⚠️ TempDir `{config.core['temp_dir']}` does not exist.")
        os.makedirs(config.core['temp_dir'])
        config.logger_core.info(f"✅ Created TempDir at `{config.core['temp_dir']}`")

    # BlackHole Paths's QueueDir
    bh: WBHBlackHole
    for bh in config.BlackHoles:
        queue_dir = os.path.join(bh.dirpath, config.core['blackhole_queue_dirname'])
        # Check/Create BlackHole Path
        if not os.path.exists(queue_dir):
            config.logger_core.warning(f"⚠️ Queue directory `{queue_dir}` does not exist.")
            os.makedirs(queue_dir)
            config.logger_core.info(f"✅ Created queue directory at `{queue_dir}`")

    config.TelegramBot = WBHTelegramBot(api=config.core['bot']['api'],
                                        logger=config.logger_bot,
                                        proxy=config.core['bot']['proxy'],
                                        log_level=config.core['log']['bot']['level'])


def main():
    print(f'\nWU-Blackhole {config.version_str()}\n')

    # Parse application arguments
    parser = argparse.ArgumentParser(description='Send everything to WU-BlackHole using Telegram Bot')
    parser.add_argument('--config', '-c',
                        help='Specify path to configuration file. (Use config.json.example as template)')
    args = parser.parse_args()
    if args.config is not None:
        # Config path is specified externally
        config.config_filepath = os.path.abspath(args.config)
    else:
        # Default config file path
        config.config_filepath = os.path.join(config.DataDir, "config.json")
    del parser  # No reason to keep this variable
    del args  # No reason to keep this variable

    # Load config
    config.load()
    config.logger_core.info('')
    config.logger_core.info(f'WU-Blackhole {config.version_str()}')

    # parse_args(init_args())

    init_WBH()
    init_temp()

    # Before start to watch the paths
    # Empty the Queue by sending to BlackHole
    for bh in config.BlackHoles:
        bh.queue.process_queue(bh.telegram_id)

    # start watchers for paths
    bh: WBHBlackHole
    for bh in config.BlackHoles:
        start_watch(bh)
        # start_watch(bh_path)


if __name__ == "__main__":
    main()
