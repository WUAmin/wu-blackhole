#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import shutil
import time
from pathlib import Path

# from wublackhole.wbh_blackhole import WBHBlackHole
from wublackhole.wbh_item import WBHItem, WBHItemState

import settings as settings


def get_path_contents(path: str, parents: list = [], populate_info: bool = False) -> list:
    """ Return (list of WatchPathItem, TotalChildren) Recursively"""
    items = []
    total = 0
    entities = os.listdir(os.path.join(path, *parents))
    for entity in entities:
        # Ignore WBH_QUEUE_DIR_NAME and WBH_ConfigFilename
        if entity == settings.BlackHoleQueueDirName or entity == settings.BlackHoleConfigFilename:
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
                item_wbhi.State = WBHItemState.INQUEUE
                item_wbhi.Size = watch_path_get_dirsize(p)
                item_wbhi.ModifiedAt = os.path.getmtime(p)
                item_wbhi.CreatedAt = os.path.getctime(p)
                item_wbhi.TotalChildren = t
            items.append(item_wbhi)
            total += t
        else:
            # File
            item_wbhi = WBHItem(filename=entity, full_path=p, root_path=path, is_dir=False, parents=parents)
            # Get additional info
            if populate_info:
                item_wbhi.State = WBHItemState.INQUEUE
                item_wbhi.Size = os.stat(p).st_size
                item_wbhi.ModifiedAt = os.path.getmtime(p)
                item_wbhi.CreatedAt = os.path.getctime(p)
            items.append(item_wbhi)
            total += 1

    return items, total


def print_path_contents(contents: list, parents: list = [], line_pre_txt=''):
    """ Print content to output """
    depth_space = len(parents) * 2 * ' '
    item: WBHItem
    for item in contents:
        if os.path.isfile(item.FullPath):
            print(f"{line_pre_txt}{depth_space}📄 {os.path.join(*parents, item.Filename)}")
        elif os.path.isdir(item.FullPath):
            print(f"{line_pre_txt}{depth_space}📂 {os.path.join(*parents, item.Filename)}")
            print_path_contents(item.Children, parents=item.Parents, line_pre_txt=line_pre_txt)
        elif os.path.islink(item.FullPath):
            print(f"{line_pre_txt}{depth_space}🔗 {os.path.join(*parents, item.Filename)}")
        else:
            print(f"{line_pre_txt}{depth_space}O {os.path.join(*parents, item.Filename)}")


def watch_is_changed(items: list, filename, size) -> tuple:
    """ Return tuple(WatchCheckSizeState, index as int)  """
    item: WBHItem  # Annotate item type before the loop
    i = 0
    for item in items:
        if item.Filename == filename:
            if item.Size == size:
                return WBHItemState.UNCHANGED, i
            else:
                return WBHItemState.CHANGED, i
        i += 1
    return WBHItemState.NEW, -1


def watch_path_get_dirsize(dir: str):
    """ return total size of the directory in bytes """
    return sum(f.stat().st_size for f in Path(dir).glob('**/*') if f.is_file())


def watch_path_move_to_queue(bh, item_wpi):
    """ return true on success """
    print(f"  🕐 Moving `{item_wpi.Filename}` to queue directory...")
    if bh.Queue.is_item_exist(item_wpi):
        print(f"    ⚠ IGNORE moving `{item_wpi.Filename}` to queue directory, Item exist is queue !!!")
    else:
        try:
            start_t = time.process_time()
            new_path = os.path.join(bh.FullPath, settings.BlackHoleQueueDirName, item_wpi.Filename)
            item_wpi.ModifiedAt = os.path.getmtime(item_wpi.FullPath)
            item_wpi.CreatedAt = os.path.getctime(item_wpi.FullPath)
            shutil.move(item_wpi.FullPath, new_path)
            item_wpi.FullPath = new_path
            bh.Queue.add(item_wpi)
            elapsed_t = time.process_time() - start_t
            print("  ✅ `{}` () moved to queue directory in {:02f} secs...".format(item_wpi.Filename, elapsed_t))
        except shutil.Error as e:
            # raise OSError(str(e))
            print(f"  ❌ ERROR: Can not move `{item_wpi.Filename}` to queue directory:\n {str(e)}")


def watch_path(bh):
    items = []
    while True:
        start_t = time.process_time()
        fns = os.listdir(bh.FullPath)
        for f in fns:
            # Ignore WBH_QUEUE_DIR_NAME and WBH_ConfigFilename
            if f == settings.BlackHoleQueueDirName or f == settings.BlackHoleConfigFilename:
                continue

            p = os.path.join(bh.FullPath, f)
            if os.path.isdir(p):
                # Directory
                size = watch_path_get_dirsize(p)
                state, i = watch_is_changed(items, f, size)
                if state == WBHItemState.UNCHANGED:
                    items[i].State = state
                    print("  📂 UNCHANGED {: 10d}  > {}".format(items[i].Size, items[i].Filename))
                elif state == WBHItemState.NEW:
                    items.append(WBHItem(size=size, root_path=bh.FullPath, full_path=p, filename=f, is_dir=True))
                    print("  📂 NEW       {: 10d}  > {}".format(size, f))
                else:
                    items[i].State = state
                    items[i].Size = size
                    print("  📂 CHANGING  {: 10d}  > {}".format(items[i].Size, items[i].Filename))
            else:
                # File
                size = os.stat(p).st_size
                state, i = watch_is_changed(items, f, size)
                if state == WBHItemState.UNCHANGED:
                    items[i].State = state
                    print("  📄 UNCHANGED {: 10d}  > {}".format(items[i].Size, items[i].Filename))
                elif state == WBHItemState.NEW:
                    items.append(WBHItem(size=size, full_path=p, filename=f, is_dir=False))
                    print("  📄 NEW       {: 10d}  > {}".format(size, f))
                else:
                    items[i].State = state
                    items[i].Size = size
                    print("  📄 CHANGING  {: 10d}  > {}".format(items[i].Size, items[i].Filename))
        elapsed_t = time.process_time() - start_t
        print("ℹ️ Checked {} items in {:02f} secs: {}".format(len(items), elapsed_t, bh.FullPath))

        # Moving UNCHANGED items from BlackHole Path
        item: WBHItem
        for item in items:
            if item.State == WBHItemState.UNCHANGED:
                watch_path_move_to_queue(bh, item)

        # Saving Queue to disk
        bh.Queue.save()

        # Empty the Queue by sending to BlackHole
        bh.Queue.process_queue(bh.TelegramID)

        print(f"⌛ Sleep for {settings.FILE_CHECK_INTERVAL} seconds...")
        time.sleep(settings.FILE_CHECK_INTERVAL)
