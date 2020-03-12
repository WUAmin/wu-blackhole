#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import shutil
from wublackhole.wbh_item import WBHItem, WBHItemState
from wublackhole.wbh_watcher import get_path_contents
from config import config


class WBHQueue:
    def __init__(self, queue_file, blackhole):
        self.blackhole = blackhole
        self.queue_file = os.path.abspath(queue_file)
        self.items: list = []
        if os.path.exists(self.queue_file):
            self.load()


    def is_item_exist(self, item: WBHItem) -> bool:
        """ return true if item exist in queue list """
        return item in self.items


    def add(self, item: WBHItem):
        """ return true if added item successfully"""
        item.state = WBHItemState.INQUEUE
        self.items.append(item)


    def remove(self, item: WBHItem):
        """ return true if removed item successfully"""
        self.items.remove(item)
        # itm: WatchPathItem
        # for itm in self.items:
        #     if item.Name == itm.Name:


    def save(self):
        """ return true if saved queue successfully to disk"""
        print("🕐 Saving queue to `{}`".format(self.queue_file))
        try:
            with open(self.queue_file, 'w') as f:
                json.dump([o.to_dict() for o in self.items], f, sort_keys=False)
        except Exception as e:
            print("  ❌ ERROR: Can not save queue to `{}`:\n {}".format(self.queue_file, str(e)))
        print("  ✅ Queue saved with {} items".format(len(self.items)))


    def load(self):
        """ return true if loaded queue successfully from disk"""
        print("🕐 Loading queue from `{}`".format(self.queue_file))
        try:
            with open(self.queue_file, 'r') as f:
                data_j = json.load(f)
                for itm in data_j:
                    self.items.append(WBHItem.from_dict(itm))
        except Exception as e:
            print("  ❌ ERROR: Can not load queue from `{}`:\n {}".format(self.queue_file, str(e)))
        print("  ✅ Queue loaded with {} items".format(len(self.items)))


    def process_queue(self, telegram_id: str):
        """ Empty queue by sending items to BlackHole """
        while len(self.items) > 0:
            first_item: WBHItem = self.items[0]
            # Check if item is file or directory
            if first_item.is_dir:
                # Directory
                first_item.children, first_item.total_children = get_path_contents(
                    os.path.join(first_item.root_path, config.core['blackhole_queue_dirname']),
                    parents=[first_item.filename], populate_info=True)
                first_item.state = WBHItemState.UPLOADING
                if config.TelegramBot.send_folder_to_blackhole(first_item, telegram_id):
                    print("✅ Sent `{}` to BlackHole.".format(first_item.filename))
                    # Add to Database
                    config.Database.add_item_folder(first_item, self.blackhole.ID, None)
                    # Remove folder
                    shutil.rmtree(first_item.full_path, ignore_errors=True)
                    self.remove(first_item)
                    print("✅ `{}` removed from queue and disk.".format(first_item.filename))
                    # Save Queue to disk
                    self.save()
                else:
                    print("❌ ERROR: Could not send `{}` to BlackHole.".format(first_item.filename))
            else:
                # File
                first_item.state = WBHItemState.UPLOADING
                if config.TelegramBot.send_file_to_blackhole(first_item, telegram_id):
                    print("✅ Sent `{}` to BlackHole.".format(first_item.filename))
                    # Add to Database
                    config.Database.add_item(first_item, self.blackhole.ID, None)
                    # Remove file
                    os.remove(first_item.full_path)
                    self.remove(first_item)
                    print("✅ `{}` removed from queue and disk.".format(first_item.filename))
                    # Save Queue to disk
                    self.save()
                else:
                    print("❌ ERROR: Could not send `{}` to BlackHole.".format(first_item.filename))

        # exit()
