#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os

from wublackhole.wbh_queue import WBHQueue

import settings as settings


class WBHBlackHole:
    def __init__(self, fullpath: str, name: str, telegram_id: str = None, _id: int = -1):
        self.FullPath: str = fullpath
        self.Name = name
        self.TelegramID = telegram_id
        # Create/Load Queue from disk
        self.Queue = WBHQueue(os.path.join(self.FullPath, settings.BlackHoleQueueDirName, 'queue.json'), self)
        # Get/Create BlackHole from/in database
        bh_id = settings.Database.get_blackhole(name)
        if not bh_id:
            bh_id = settings.Database.add_blackhole(name, -1, telegram_id)
        self.ID: int = bh_id.id


    def to_dict(self):
        return {'ID': self.ID,
                'FullPath': self.FullPath,
                'Name': self.Name,
                'TelegramID': self.TelegramID}


    @staticmethod
    def from_dict(_dict):
        return WBHBlackHole(_id=_dict['ID'],
                            fullpath=_dict['FullPath'],
                            name=_dict['Name'],
                            telegram_id=_dict['TelegramID'])


    def save(self):
        """ return true if saved successfully to disk"""
        bh_config_path = os.path.join(self.FullPath, settings.BlackHoleConfigFilename)
        print("🕐 Saving BlackHole config to `{}`".format(bh_config_path))
        try:
            with open(bh_config_path, 'w') as f:
                json.dump(self.to_dict(), f, sort_keys=False)
        except Exception as e:
            print("  ❌ ERROR: Can not save BlackHole to `{}`:\n {}".format(bh_config_path, str(e)))
        print("  ✅ BlackHole saved with {} items")


    @staticmethod
    def load(bh_config_path: str):
        """ return true if loaded successfully from disk. """
        print("🕐 Loading BlackHole from `{}`".format(bh_config_path))
        bh = None
        try:
            with open(bh_config_path, 'r') as f:
                data_j = json.load(f)
                bh = WBHBlackHole.from_dict(data_j)
        except Exception as e:
            print("  ❌ ERROR: Can not load BlackHole from `{}`:\n {}".format(bh_config_path, str(e)))
        print("  ✅ BlackHole loaded with {} items")
        return bh
