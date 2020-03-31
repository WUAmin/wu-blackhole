#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import shutil
import time
from pathlib import Path

from common.helper import sizeof_fmt, get_path_size
from config import config
from wublackhole.wbh_item import QueueState, WBHItem


def get_contents(path: str, parents: list = [], parent_qid=None, populate_info: bool = False) -> tuple:
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
            item_wbhi = WBHItem(filename=entity, full_path=p, root_path=path, is_dir=True, parents=parents,
                                parent_qid=parent_qid)
            item_wbhi.children, t = get_contents(path=path, parents=_p, parent_qid=item_wbhi.qid,
                                                 populate_info=populate_info)
            # Get additional info
            if populate_info:
                item_wbhi.state = QueueState.INQUEUE
                item_wbhi.size = get_path_size(p)
                item_wbhi.modified_at = os.path.getmtime(p)
                item_wbhi.created_at = os.path.getctime(p)
                item_wbhi.total_children = t
            items.append(item_wbhi)
            total += t
        else:
            # File
            item_wbhi = WBHItem(filename=entity, full_path=p, root_path=path, is_dir=False, parents=parents,
                                parent_qid=parent_qid)
            # Get additional info
            if populate_info:
                item_wbhi.state = QueueState.INQUEUE
                item_wbhi.size = os.stat(p).st_size
                item_wbhi.modified_at = os.path.getmtime(p)
                item_wbhi.created_at = os.path.getctime(p)
            items.append(item_wbhi)
            total += 1

    return items, total


def print_contents(contents: list, parents: list = [], line_pre_txt=''):
    """ Print content to output """
    depth_space = len(parents) * 2 * ' '
    item: WBHItem
    for item in contents:
        if item.is_dir:
            msg = f"{line_pre_txt}{depth_space}📂 {os.path.join(*parents, item.filename)}"
            msg += ", Size: {}".format(sizeof_fmt(item.size))
            if hasattr(item, 'items_count'):
                msg += ", Items: {}".format(item.items_count)
                msg += ", ID: {}".format(item.id)
            print(msg)
            _parents = list(parents)
            _parents.append(item.filename)
            if hasattr(item, 'children'):
                print_contents(item.children, parents=_parents, line_pre_txt=line_pre_txt)
            elif hasattr(item, 'items'):
                print_contents(item.items, parents=_parents, line_pre_txt=line_pre_txt)
        else:
            msg = f"{line_pre_txt}{depth_space}📄 {os.path.join(*parents, item.filename)}"
            msg += ", Size: {}".format(sizeof_fmt(item.size))
            if hasattr(item, 'chunks_count'):
                msg += ", Chunks: {}".format(item.chunks_count)
                msg += ", ID: {}".format(item.id)
            print(msg)



def get_new_item_state(items: list, filename, size) -> tuple:
    """ Return tuple(WatchCheckSizeState, index as int)  """
    item: WBHItem  # Annotate item type before the loop
    i = 0
    for item in items:
        if item.filename == filename:
            if item.size == size:
                return QueueState.UNCHANGED, i
            else:
                return QueueState.CHANGED, i
        i += 1
    return QueueState.NEW, -1


def move_to_queue(bh, item_wpi: WBHItem):
    """ return true on success """
    config.logger_core.debug(f"  🕐 Moving `{item_wpi.filename}` to queue directory...")
    if bh.queue.is_item_exist(item_wpi):
        config.logger_core.warning(
            f"    ⚠ IGNORE moving `{item_wpi.filename}` to queue directory, Item exist is queue !!!")
    else:
        try:
            start_t = time.process_time()
            # Prepare new path
            queue_dir = os.path.join(bh.dirpath, config.core['blackhole_queue_dirname'])
            new_path = os.path.join(queue_dir, item_wpi.filename)
            # get dates of item
            item_wpi.modified_at = os.path.getmtime(item_wpi.full_path)
            item_wpi.created_at = os.path.getctime(item_wpi.full_path)
            # move item
            shutil.move(item_wpi.full_path, new_path)
            # update item's full_path
            item_wpi.root_path = queue_dir
            item_wpi.full_path = new_path
            # Add item to queue
            if item_wpi.is_dir:
                # == Directory ==
                # Add folder itself (as an item)
                bh.queue.add(item_wpi)
                # Looking for content of folder
                children_parents = list(item_wpi.parents)
                children_parents.append(item_wpi.filename)
                item_wpi.children, item_wpi.total_children = get_contents(path=item_wpi.root_path,
                                                                          parents=children_parents,
                                                                          parent_qid=item_wpi.qid,
                                                                          populate_info=True)
            else:
                # == File ==
                bh.queue.add(item_wpi)
            # Saving Queue to disk
            bh.queue.save()
            elapsed_t = time.process_time() - start_t
            config.logger_core.info(
                "  ✅ `{}` () moved to queue directory in {:02f} secs...".format(item_wpi.filename, elapsed_t))
        except shutil.Error as e:
            # raise OSError(str(e))
            config.logger_core.error(f"  ❌ ERROR: Can not move `{item_wpi.filename}` to queue directory:\n {str(e)}")


def start_watch(bh):
    items = []
    while True:
        start_t = time.process_time()
        fns = os.listdir(bh.dirpath)
        for f in fns:
            # Ignore WBH_QUEUE_DIR_NAME and WBH_ConfigFilename
            if f == config.core['blackhole_queue_dirname'] or f == config.core['blackhole_config_filename']:
                continue

            # Prepare full_path
            full_path = os.path.join(bh.dirpath, f)
            # Get file/folder size
            size = get_path_size(full_path)
            # Get state in compare to the item in items
            state, i = get_new_item_state(items, f, size)
            # Update item's state
            if state == QueueState.UNCHANGED:
                items[i].state = state
                config.logger_core.debug("  📂 UNCHANGED {: 10d}  > {}".format(items[i].size, items[i].filename))
            elif state == QueueState.NEW:
                items.append(WBHItem(size=size, root_path=bh.dirpath, full_path=full_path, filename=f,
                                     is_dir=os.path.isdir(full_path)))
                config.logger_core.debug("  📂 NEW       {: 10d}  > {}".format(size, f))
            else:
                items[i].state = state
                items[i].size = size
                config.logger_core.debug("  📂 CHANGING  {: 10d}  > {}".format(items[i].size, items[i].filename))

        elapsed_t = time.process_time() - start_t
        config.logger_core.debug("ℹ️ Checked {} items in {:02f} secs: {}".format(len(items), elapsed_t, bh.dirpath))

        # Moving UNCHANGED items to BlackHole's queue and save queue
        item: WBHItem
        for item in items:
            if item.state == QueueState.UNCHANGED:
                move_to_queue(bh, item)
                items.remove(item)

        # Empty the Queue by sending to BlackHole
        bh.queue.process_queue(bh.telegram_id)

        # if run_counts:
        #     run_counts -= 1
        #     if run_counts <= 0:
        #         break
        # else:
        config.logger_core.debug(f"⌛ Sleep for {config.core['path_check_interval']} seconds...")
        time.sleep(config.core['path_check_interval'])

        # Break the loop if there is items there. Let application process blackholes
        if len(items) <= 0:
            break
