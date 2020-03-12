#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import shutil
import time
from pathlib import Path

from config import config
from wublackhole.wbh_item import WBHItem, WBHItemState


def get_path_contents(path: str, parents: list = [], populate_info: bool = False) -> tuple:
    """ Return (list of WatchPathItem, TotalChildren) Recursively"""
    items = []
    total = 0
    entities = os.listdir(os.path.join(path, *parents))
    for entity in entities:
        # Ignore WBH_QUEUE_DIR_NAME and WBH_ConfigFilename
        if entity == config.core['blackhole_queue_dirname'] or entity == config.core['blackhole_config_filename']:
            continue
        p = os.path.join(path, *parents, entity)
        if os.path.isdir(p):
            # Directory
            _p = list(parents)
            _p.append(entity)
            children, t = get_path_contents(path=path, parents=_p)
            item_wbhi = WBHItem(filename=entity, full_path=p, root_path=path, is_dir=True, parents=parents,
                                children=children)
            # Get additional info
            if populate_info:
                item_wbhi.state = WBHItemState.INQUEUE
                item_wbhi.size = watch_path_get_dirsize(p)
                item_wbhi.modified_at = os.path.getmtime(p)
                item_wbhi.created_at = os.path.getctime(p)
                item_wbhi.total_children = t
            items.append(item_wbhi)
            total += t
        else:
            # File
            item_wbhi = WBHItem(filename=entity, full_path=p, root_path=path, is_dir=False, parents=parents)
            # Get additional info
            if populate_info:
                item_wbhi.state = WBHItemState.INQUEUE
                item_wbhi.size = os.stat(p).st_size
                item_wbhi.modified_at = os.path.getmtime(p)
                item_wbhi.created_at = os.path.getctime(p)
            items.append(item_wbhi)
            total += 1

    return items, total


def print_path_contents(contents: list, parents: list = [], line_pre_txt=''):
    """ Print content to output """
    depth_space = len(parents) * 2 * ' '
    item: WBHItem
    for item in contents:
        if os.path.isfile(item.full_path):
            print(f"{line_pre_txt}{depth_space}📄 {os.path.join(*parents, item.filename)}")
        elif os.path.isdir(item.full_path):
            print(f"{line_pre_txt}{depth_space}📂 {os.path.join(*parents, item.filename)}")
            print_path_contents(item.children, parents=item.parents, line_pre_txt=line_pre_txt)
        elif os.path.islink(item.full_path):
            print(f"{line_pre_txt}{depth_space}🔗 {os.path.join(*parents, item.filename)}")
        else:
            print(f"{line_pre_txt}{depth_space}O {os.path.join(*parents, item.filename)}")


def watch_is_changed(items: list, filename, size) -> tuple:
    """ Return tuple(WatchCheckSizeState, index as int)  """
    item: WBHItem  # Annotate item type before the loop
    i = 0
    for item in items:
        if item.filename == filename:
            if item.size == size:
                return WBHItemState.UNCHANGED, i
            else:
                return WBHItemState.CHANGED, i
        i += 1
    return WBHItemState.NEW, -1


def watch_path_get_dirsize(dir_path: str):
    """ return total size of the directory in bytes """
    return sum(f.stat().st_size for f in Path(dir_path).glob('**/*') if f.is_file())


def watch_path_move_to_queue(bh, item_wpi: WBHItem):
    """ return true on success """
    print(f"  🕐 Moving `{item_wpi.filename}` to queue directory...")
    if bh.Queue.is_item_exist(item_wpi):
        print(f"    ⚠ IGNORE moving `{item_wpi.filename}` to queue directory, Item exist is queue !!!")
    else:
        try:
            start_t = time.process_time()
            new_path = os.path.join(bh.FullPath, config.core['blackhole_queue_dirname'], item_wpi.filename)
            item_wpi.modified_at = os.path.getmtime(item_wpi.full_path)
            item_wpi.created_at = os.path.getctime(item_wpi.full_path)
            shutil.move(item_wpi.full_path, new_path)
            item_wpi.full_path = new_path
            bh.Queue.add(item_wpi)
            elapsed_t = time.process_time() - start_t
            print("  ✅ `{}` () moved to queue directory in {:02f} secs...".format(item_wpi.filename, elapsed_t))
        except shutil.Error as e:
            # raise OSError(str(e))
            print(f"  ❌ ERROR: Can not move `{item_wpi.filename}` to queue directory:\n {str(e)}")


def watch_path(bh):
    items = []
    while True:
        start_t = time.process_time()
        fns = os.listdir(bh.FullPath)
        for f in fns:
            # Ignore WBH_QUEUE_DIR_NAME and WBH_ConfigFilename
            if f == config.core['blackhole_queue_dirname'] or f == config.core['blackhole_config_filename']:
                continue

            p = os.path.join(bh.FullPath, f)
            if os.path.isdir(p):
                # Directory
                size = watch_path_get_dirsize(p)
                state, i = watch_is_changed(items, f, size)
                if state == WBHItemState.UNCHANGED:
                    items[i].state = state
                    print("  📂 UNCHANGED {: 10d}  > {}".format(items[i].size, items[i].filename))
                elif state == WBHItemState.NEW:
                    items.append(WBHItem(size=size, root_path=bh.FullPath, full_path=p, filename=f, is_dir=True))
                    print("  📂 NEW       {: 10d}  > {}".format(size, f))
                else:
                    items[i].state = state
                    items[i].size = size
                    print("  📂 CHANGING  {: 10d}  > {}".format(items[i].size, items[i].filename))
            else:
                # File
                size = os.stat(p).st_size
                state, i = watch_is_changed(items, f, size)
                if state == WBHItemState.UNCHANGED:
                    items[i].state = state
                    print("  📄 UNCHANGED {: 10d}  > {}".format(items[i].size, items[i].filename))
                elif state == WBHItemState.NEW:
                    items.append(WBHItem(size=size, full_path=p, filename=f, is_dir=False))
                    print("  📄 NEW       {: 10d}  > {}".format(size, f))
                else:
                    items[i].state = state
                    items[i].size = size
                    print("  📄 CHANGING  {: 10d}  > {}".format(items[i].size, items[i].filename))
        elapsed_t = time.process_time() - start_t
        print("ℹ️ Checked {} items in {:02f} secs: {}".format(len(items), elapsed_t, bh.FullPath))

        # Moving UNCHANGED items from BlackHole Path
        item: WBHItem
        for item in items:
            if item.state == WBHItemState.UNCHANGED:
                watch_path_move_to_queue(bh, item)

        # Saving Queue to disk
        bh.Queue.save()

        # Empty the Queue by sending to BlackHole
        bh.Queue.process_queue(bh.TelegramID)

        print(f"⌛ Sleep for {config.core['path_check_interval']} seconds...")
        time.sleep(config.core['path_check_interval'])
