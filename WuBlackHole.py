#!/usr/bin/python3from config import config

# -*- coding: utf-8 -*-
import os

from past.builtins import raw_input

from config import config
# import settings as settings
from wublackhole.wbh_blackhole import WBHBlackHole
from wublackhole.wbh_bot import WBHTelegramBot
from wublackhole.wbh_db import WBHDatabase
from wublackhole.wbh_watcher import start_watch


# TODO: Add Ability to do ChaCha20Poly1305 encryption  (key on db and password by user input)
# TODO: Add Ability to do Fernet encryption (key on db only)
# TODO: ability to retrieve data
# TODO: Flask/Vue.js for GUI

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


def create_config_on_blackhole_dir(bh_config_path: str, bh_path: str):
    """ Create config file in blackhole directory"""
    config.logger_core.info(f"  ℹ Generating `{config.core['blackhole_config_filename']}` in `{bh_path}`...")
    while True:
        # BlackHole Name
        bh_name = os.path.basename(bh_path)
        bh_name = raw_input(f"  ✏️ Enter blackhole name [{bh_name}]:") or bh_name
        # Telegram Chat ID
        bh_telegram_id = config.DefaultChatID
        bh_telegram_id = raw_input(f"  ✏️ Enter Telegram Chat ID [{bh_telegram_id}]:") or bh_telegram_id
        # Verification
        answer: str = 'y'
        print(f"  ℹ BlackHole Name:   {bh_name}")
        print(f"  ℹ Telegram Chat ID: {bh_telegram_id}")
        while True:
            answer = raw_input(f"  ❓️ Are you sure about this? [n/Y] :") or answer
            if answer.lower() == 'y':
                bh = WBHBlackHole(fullpath=os.path.abspath(bh_path),
                                  name=bh_name,
                                  telegram_id=bh_telegram_id)
                bh.save()
                config.logger_core.info(f"✅ Generate `{config.core['blackhole_config_filename']}` in `{bh_path}`")
                return bh
            elif answer.lower() == 'n':
                break
            else:
                print(f"  ⚠️ Enter y or n")


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
    # Load config
    config.config_filepath = os.path.join(config.DataDir, "config.json")
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

#  📄📂📁🗂❌✅❎🔗ℹ️⚠❔❓🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛⏳⌛️⏱
