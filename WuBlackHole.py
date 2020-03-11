#!/usr/bin/python3
# -*- coding: utf-8 -*-
import argparse
import os
import subprocess

from past.builtins import raw_input
from wublackhole.wbh_blackhole import WBHBlackHole
from wublackhole.wbh_bot import WBHTelegramBot
from wublackhole.wbh_db import WBHDatabase
from wublackhole.wbh_watcher import get_path_contents, print_path_contents, watch_path

import settings as settings


def run_command(command):
    my_env = os.environ.copy()
    my_env["HOME"] = settings.DataDir
    p = subprocess.Popen(command,
                         env=my_env,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
    return iter(p.stdout.readline, b'')


def run_telegram_cli(tg_cmd, is_json=False):
    # env HOME=$PWD/WuBlackhole_Data bash -c 'echo $HOME'
    # env HOME="/mnt/D-WuDisk1/DEV/wu-telegram/WuBlackhole_Data" "telegram-cli" -W -e "msg @WUAmin \"sgsh\""
    # Add Enviroment variables
    cmd = f'env HOME={settings.DataDir}'
    # Add telegram-cli path
    cmd += f' {settings.TelegramCli_Path}'
    # Add '-W    send dialog_list query and wait for answer before reading input'
    cmd += f' -W'
    # Add '-D    disable output'
    # cmd += f' -D'
    # Add --json to output json
    if is_json:
        cmd += f' --json'
    # Add telegram-cli command
    cmd += f" -e '{tg_cmd}'"
    print(f'Exec: {cmd}')
    p = os.popen(cmd)
    return p.read()


def tg_Message(peer, msg):
    return run_telegram_cli(f'msg {peer} "{msg}"', is_json=True)


# def tg_LastMessageID(peer):
#     #  | grep print_name | sed -e 's/.*\"id\": \"\([0-9a-zA-Z]\+\)\".*/\1/g' |  head -n 1'
#     return run_telegram_cli(f'history {peer} 1', is_json=True)


def init_temp():
    # Clear leftover of old temp files
    files = os.listdir(settings.TempDir)
    t_i = 0
    for file in files:
        if file.startswith("WBHTF"):
            ext = os.path.splitext(file)[1]
            if len(ext) == 6 and ext.startswith(".p"):
                try:
                    os.remove(os.path.join(settings.TempDir, file))
                    t_i += 1
                except:
                    print("❌ Error while deleting file : ", os.path.join(settings.TempDir, file))
    if t_i > 0:
        print(f"⚠️ {t_i} old temp files deleted.")

    # os.makedirs(os.path.join(settings.TempDir, 'qeue'))
    pass


def create_config_on_blackhole_dir(bh_config_path: str, bh_path: str):
    """ Create config file in blackhole directory"""
    print(f"  ℹ Generating `{settings.BlackHoleConfigFilename}` in `{bh_path}`...")
    while True:
        # BlackHole Name
        bh_name = os.path.basename(bh_path)
        bh_name = raw_input(f"  ✏️ Enter blackhole name [{bh_name}]:") or bh_name
        # Telegram Chat ID
        bh_telegram_id = settings.DefaultChatID
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
                print(f"✅ Generate `{settings.BlackHoleConfigFilename}` in `{bh_path}`")
                return bh
            elif answer.lower() == 'n':
                break
            else:
                print(f"  ⚠️ Enter y or m")


def init_WBH():
    # Check/Create BlackHole Data Directory
    if not os.path.exists(settings.DataDir):
        os.makedirs(settings.DataDir)

    # BlackHole Paths's QueueDir
    bh: WBHBlackHole
    for bh in settings.BlackHoles:
        queue_dir = os.path.join(bh.FullPath, settings.BlackHoleQueueDirName)
        # Check/Create BlackHole Path
        if not os.path.exists(queue_dir):
            print(f"⚠️ Queue directory `{queue_dir}` does not exist.")
            os.makedirs(queue_dir)
            print(f"✅ Created queue directory at `{queue_dir}`")

    settings.TelegramBot = WBHTelegramBot()
    # settings.TelegramBot.start_bot()


def parse_args(args):
    # Check input: -t, --tempdir    Temp Directory
    if 'tempdir' in args:
        settings.TempDir = args.tempdir.strip()
        if not os.path.exists(settings.TempDir):
            print(f"⚠️ TempDir `{settings.TempDir}` does not exist.")
            os.makedirs(settings.TempDir)
            print(f"✅ Created TempDir at `{settings.TempDir}`")

    # Check input: paths    paths to watch
    if len(args.paths) <= 0:
        print(
            "❌ Error: you have to specify paths as your last argument",
            " for application to be able to file files to throw in the blackhole")
        exit(0)
    else:
        print(f'{len(args.paths)} paths:')
        i_p = 0
        is_error = False
        for bh_path in args.paths:
            if os.path.exists(bh_path):
                if os.path.isdir(bh_path):
                    print(' 📂 {:03d}: `{}`'.format(i_p, bh_path))
                    contents, t = get_path_contents(bh_path)
                    print_path_contents(contents=contents, line_pre_txt='   ')
                    # settings.paths.append(os.path.abspath(p))

                    # Check/Create .__WBH__.conf Path
                    bh_config_path = os.path.join(bh_path, settings.BlackHoleConfigFilename)
                    if not os.path.exists(bh_config_path):
                        print(f"⚠️ `{settings.BlackHoleConfigFilename}` file does not exist in `{bh_path}`")
                        bh = create_config_on_blackhole_dir(bh_config_path, bh_path)
                        settings.BlackHoles.append(bh)
                    else:
                        print(f"⏳️ Loading BlackHole config file in `{bh_path}`")
                        bh = WBHBlackHole.load(os.path.join(bh_path, settings.BlackHoleConfigFilename))
                        settings.BlackHoles.append(bh)
                else:
                    print(' ❌ {:03d}: `{}` should be a folder.'.format(i_p, bh_path))
            else:
                print(' ❌ {:03d}: `{}` does not exist.'.format(i_p, bh_path))
                is_error = True
        i_p += 1
        if is_error:
            exit(1)


def init_args():
    """ Return ArgumentParser on successful initialization """
    # parser = argparse.ArgumentParser(description='')
    parser = argparse.ArgumentParser()

    parser.add_argument('-t', '--tempdir', type=str,
                        help='Specify temp directory to split files if needed. \n'
                             f'Default: [{settings.TempDir}]')

    parser.add_argument('paths', nargs='+',
                        help='Paths to watch')

    return parser.parse_args()


# ============ START =============
if __name__ == "__main__":
    print(f'\nWU-Blackhole {settings.version}\n')

    settings.Database = WBHDatabase(settings.DbPath, True)

    # # Database Test
    # settings.Database = WBHDatabase(settings.DbPath)
    # for i in range(10000000):
    #     start_t = time.process_time()
    #     for j in range(10000):
    #         bh_new = settings.Database.WBHDbBlackHoles(name="BH {}x{}".format(i, j), size=i*j, telegram_id="1")
    #         settings.Database.session.add(bh_new)
    #     settings.Database.session.commit()
    #     elapsed_t = time.process_time() - start_t
    #     print("{}x Insert 100000 item in {:02f} secs".format(i, elapsed_t))

    parse_args(init_args())

    print(f"ℹ️ TelegramCli_Path:     `{settings.TelegramCli_Path}`")
    print(f"ℹ️ WBH_Data_Dir:         `{settings.DataDir}`")
    print(f"ℹ️ TempDir:              `{settings.TempDir}`")
    print(f"ℹ️ DEFAULT_CHANNEL_ID:   `{settings.DefaultChatID}`")

    init_WBH()
    init_temp()

    # Before start to watch the paths
    # Empty the Queue by sending to BlackHole
    for bh in settings.BlackHoles:
        bh.Queue.process_queue(bh.TelegramID)

    # start watchers for paths
    bh: WBHBlackHole
    for bh in settings.BlackHoles:
        watch_path(bh)
        # start_watch(bh_path)

    # send_file('/home/wuamin/Desktop/Desktop_[Win]/WU-BlackHole.temp/test.mkv')

    # while True:
    #     print(f"⌛ Sleep for {settings.FILE_CHECK_INTERVAL} seconds...")
    #     time.sleep(settings.FILE_CHECK_INTERVAL)

    # bot.send_file(filepath='http://mirrors.standaloneinstaller.com/video-sample/small.mp4',
    #               filename='link to file.jpg',
    #               caption='link to file.jpg')

# 📄📂📁🗂❌✅❎🔗ℹ️⚠❔❓
# 🕑🕒🕓🕔🕕🕖🕗🕘🕙🕚🕛⏳⌛️⏱
