#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import tempfile

from dotenv import load_dotenv  # pip install python-dotenv


# from wublackhole.wbh_bot import WBHTelegramBot
# from wublackhole.wbh_db import WBHDatabase


def str_list_to_int_list(lst):
    for i in range(0, len(lst)):
        if len(lst[i]) > 0:
            lst[i] = int(lst[i])
    return lst


# Load .env.WuBlackhole
load_dotenv(os.path.join(os.path.dirname(__file__), '.env.WuBlackhole'))
version = 0.1
if os.name == 'nt':
    TelegramCli_Path = ''
else:
    TelegramCli_Path = 'telegram-cli'
DataDir = os.path.join(os.path.split(os.path.realpath(__file__))[0], "WuBlackhole_Data")
BlackHoles = []
BlackHoleConfigFilename = ".__WBH__.json"
BlackHoleQueueDirName = os.environ.get("WBH_QUEUE_DIR_NAME")
TempDir = os.path.join(tempfile.gettempdir(), "WBH-temp")
api_token = os.environ.get("API_TOKEN")
# TelegramBot: WBHTelegramBot = None
TelegramBot = None
DefaultChatID = os.environ.get("DEFAULT_CHAT_ID")
ChunkSize = int(os.environ.get("CHUNK_SIZE"))
DbPath = os.path.join(DataDir, "wbh.db")
# Database: WBHDatabase = None
Database = None
# paths = []
# TempDir = os.path.split(os.path.realpath(__file__))[0] + os.sep + '.temp'
# DefaultPeer = "$05000000f70b0b5635bd6d1bd72386ad"
DefaultPeer = 'WU-BlackHole'
# Queue = WBHQueue(os.path.join(WBH_Data_Dir, 'queue.json'))
# Queue: WBHQueue = None

WBH_OWNER_ID = os.environ.get("WBH_OWNER_ID")
FILE_CHECK_INTERVAL = int(os.environ.get("FILE_CHECK_INTERVAL"))
ADMIN_CHAT_IDs = str_list_to_int_list(os.environ.get("ADMIN_CHAT_IDs").split(','))
GROUPS_CHAT_IDs = str_list_to_int_list(os.environ.get("GROUPS_CHAT_IDs").split(','))
USERS_CHAT_IDs = str_list_to_int_list(os.environ.get("USERS_CHAT_IDs").split(','))

ADMIN_LEVEL = 100
GROUPS_LEVEL = 50
USERS_LEVEL = 20
UNAUTHORIZED_LEVEL = -1
