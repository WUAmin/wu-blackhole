#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
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

# def run_command(command):
#     my_env = os.environ.copy()
#     my_env["HOME"] = config.DataDir
#     p = subprocess.Popen(command,
#                          env=my_env,
#                          stdout=subprocess.PIPE,
#                          stderr=subprocess.STDOUT)
#     return iter(p.stdout.readline, b'')

#
# def run_telegram_cli(tg_cmd, is_json=False):
#     # env HOME=$PWD/WuBlackhole_Data bash -c 'echo $HOME'
#     # env HOME="/mnt/D-WuDisk1/DEV/wu-telegram/WuBlackhole_Data" "telegram-cli" -W -e "msg @WUAmin \"sgsh\""
#     # Add Enviroment variables
#     cmd = f'env HOME={config.DataDir}'
#     # Add telegram-cli path
#     cmd += f' {settings.TelegramCli_Path}'
#     # Add '-W    send dialog_list query and wait for answer before reading input'
#     cmd += f' -W'
#     # Add '-D    disable output'
#     # cmd += f' -D'
#     # Add --json to output json
#     if is_json:
#         cmd += f' --json'
#     # Add telegram-cli command
#     cmd += f" -e '{tg_cmd}'"
#     print(f'Exec: {cmd}')
#     p = os.popen(cmd)
#     return p.read()

#
# def tg_Message(peer, msg):
#     return run_telegram_cli(f'msg {peer} "{msg}"', is_json=True)


# def tg_LastMessageID(peer):
#     #  | grep print_name | sed -e 's/.*\"id\": \"\([0-9a-zA-Z]\+\)\".*/\1/g' |  head -n 1'
#     return run_telegram_cli(f'history {peer} 1', is_json=True)


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

    # os.makedirs(os.path.join(config.core['temp_dir'], 'qeue'))
    pass


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
    config.Database = WBHDatabase(os.path.join(config.DataDir, config.core['db_filename']), False)

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

    config.TelegramBot = WBHTelegramBot()
    # config.TelegramBot.start_bot()


# def parse_args(args):
#     # Check input: -t, --tempdir    Temp Directory
#     # if 'tempdir' in args:
#     #     config.core['temp_dir'] = args.tempdir.strip()
#     #     if not os.path.exists(config.core['temp_dir']):
#     #         print(f"⚠️ TempDir `{config.core['temp_dir']}` does not exist.")
#     #         os.makedirs(config.core['temp_dir'])
#     #         print(f"✅ Created TempDir at `{config.core['temp_dir']}`")
#
#     # Check input: paths    paths to watch
#     if len(args.paths) <= 0:
#         config.logger_core.fatal(
#             "❌ Error: you have to specify paths as your last argument",
#             " for application to be able to file files to throw in the blackhole")
#         exit(0)
#     else:
#         config.logger_core.debug(f'{len(args.paths)} paths:')
#         i_p = 0
#         is_error = False
#         for bh_path in args.paths:
#             if os.path.exists(bh_path):
#                 if os.path.isdir(bh_path):
#                     # config.logger.debug(' 📂 {:03d}: `{}`'.format(i_p, bh_path))
#                     # contents, t = get_path_contents(bh_path)
#                     # print_path_contents(contents=contents, line_pre_txt='   ')
#
#                     # Check/Create .__WBH__.conf Path
#                     bh_config_path = os.path.join(bh_path, config.core['blackhole_config_filename'])
#                     if not os.path.exists(bh_config_path):
#                         config.logger_core.warning(
#                             f"⚠️ `{config.core['blackhole_config_filename']}` file does not exist in `{bh_path}`")
#                         bh = create_config_on_blackhole_dir(bh_config_path, bh_path)
#                         config.BlackHoles.append(bh)
#                     else:
#                         config.logger_core.debug(f"⏳️ Loading BlackHole config file in `{bh_path}`")
#                         bh = WBHBlackHole.load(os.path.join(bh_path, config.core['blackhole_config_filename']))
#                         config.BlackHoles.append(bh)
#                 else:
#                     config.logger_core.error(' ❌ {:03d}: `{}` should be a folder.'.format(i_p, bh_path))
#             else:
#                 config.logger_core.fatal(' ❌ {:03d}: `{}` does not exist.'.format(i_p, bh_path))
#                 is_error = True
#         i_p += 1
#         if is_error:
#             exit(1)
#
#
# def init_args():
#     """ Return ArgumentParser on successful initialization """
#     # parser = argparse.ArgumentParser(description='')
#     parser = argparse.ArgumentParser()
#
#     parser.add_argument('-t', '--tempdir', type=str,
#                         help="Specify temp directory to split files if needed. \n"
#                              f"Default: [{config.core['temp_dir']}]")
#
#     parser.add_argument('paths', nargs='+',
#                         help='Paths to watch')
#
#     return parser.parse_args()


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
