#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os

from helper import EncryptionType
from wbh_queue import WBHQueue


class WBHBlackHole:
    def __init__(self, dirpath: str, name: str, telegram_id: int = None, _id: int = None,
                 encryption_type: EncryptionType = EncryptionType.NONE, encryption_pass: str = None):
        self.dirpath: str = dirpath
        self.name = name
        self.telegram_id = telegram_id
        self.encryption_type = encryption_type
        self.encryption_pass = encryption_pass
        # Create/Load Queue from disk
        from settings import settings
        self.queue = WBHQueue(
            os.path.join(self.dirpath, settings.config['general']['blackhole_queue_dirname'], 'queue.json'), self)
        self.id: int = _id


    def init_id(self):
        from settings import settings
        # Get/Create BlackHole from/in database
        bh_id = settings.Database.get_blackhole_by_name(self.name)
        if not bh_id:
            bh_id = settings.Database.add_blackhole(self.name, -1, self.telegram_id)
        self.id: int = bh_id.id


    def to_dict(self):
        return {'id': self.id,
                'dirpath': self.dirpath,
                'name': self.name,
                'telegram_id': self.telegram_id,
                'encryption_type': self.encryption_type.name,
                'encryption_pass': self.encryption_pass}


    @staticmethod
    def from_dict(_dict):
        return WBHBlackHole(_id=_dict['id'],
                            dirpath=_dict['dirpath'],
                            name=_dict['name'],
                            telegram_id=_dict['telegram_id'],
                            encryption_type=EncryptionType[_dict['encryption_type']],
                            encryption_pass=_dict['encryption_pass'])


    # def save(self):
    #     """ return true if saved successfully to disk"""
    #     bh_config_path = os.path.join(self.dirpath, config.core['blackhole_config_filename'])
    #     config.logger_core.debug(" Saving BlackHole config to `{}`".format(bh_config_path))
    #     try:
    #         with open(bh_config_path, 'w') as f:
    #             json.dump(self.to_dict(), f, sort_keys=False)
    #     except Exception as e:
    #         config.logger_core.error("   ERROR: Can not save BlackHole to `{}`:\n {}".format(bh_config_path, str(e)))
    #     config.logger_core.debug("  BlackHole saved with {} items")


    @staticmethod
    def load(bh_config_path: str):
        from settings import settings
        """ return true if loaded successfully from disk. """
        settings.logger_core.debug(" Loading BlackHole from `{}`".format(bh_config_path))
        bh = None
        try:
            with open(bh_config_path, 'r') as f:
                data_j = json.load(f)
                bh = WBHBlackHole.from_dict(data_j)
        except Exception as e:
            settings.logger_core.error(
                "   ERROR: Can not load BlackHole from `{}`:\n {}".format(bh_config_path, str(e)))
        settings.logger_core.debug("  BlackHole loaded with {} items")
        return bh
