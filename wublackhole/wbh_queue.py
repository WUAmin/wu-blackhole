#!/usr/bin/python3
# -*- coding: utf-8 -*-
import json
import os
import shutil
from datetime import datetime
import time

from common.helper import ChecksumType, EncryptionType, chacha20poly1305_encrypt_data, compress_bytes_to_string_b64zlib, \
    get_checksum_sha256_file, get_checksum_sha256_folder
from config import config
from wublackhole.wbh_item import QueueState, WBHChunk, WBHItem


class WBHQueue:
    def __init__(self, queue_file, blackhole):
        self.blackhole = blackhole
        self.queue_file = os.path.abspath(queue_file)
        self.items: list = []
        if os.path.exists(self.queue_file):
            self.load()


    def is_item_exist_list(self, item: WBHItem, items: list) -> WBHItem:
        """ return true if item exist in given list, Recursively """
        if item in items:
            return True
        else:
            itm2: WBHItem
            for itm2 in items:
                if itm2.is_dir:
                    if self.is_item_exist_list(item, itm2.children):
                        return True
        return False


    def is_item_exist(self, item: WBHItem) -> bool:
        """ return true if item exist in queue list, Recursively """
        return self.is_item_exist_list(item, self.items)


    def get_item_by_qid_list(self, qid: int, items: list) -> WBHItem:
        """ return WBHItem if item exist with qid in given list, Recursively """
        item: WBHItem
        for item in items:
            if item.qid == qid:
                return item
            elif item.is_dir:
                sub_item = self.get_item_by_qid_list(qid, item.children)
                if sub_item:
                    return sub_item
        return None


    def get_item_by_qid(self, qid: int) -> WBHItem:
        """ return WBHItem if item exist with qid in queue list, Recursively """
        return self.get_item_by_qid_list(qid, self.items)


    def add(self, item: WBHItem):
        """ return true if added item successfully"""
        item.state = QueueState.INQUEUE
        self.items.append(item)


    def _remove_recursively(self, item: WBHItem, items: list):
        """ return true if removed item successfully"""
        itm: WBHItem
        for itm in items:
            if item.qid == itm.qid:  # Found

                items.remove(itm)
                return True
            elif itm.children:  # Try children
                if self._remove_recursively(item, itm.children):
                    # found in children
                    return True
        return False


    def remove(self, item: WBHItem):
        """ return true if removed item successfully (Recursive)"""
        return self._remove_recursively(item, self.items)


    def save(self):
        """ return true if saved queue successfully to disk"""
        config.logger_core.debug("Saving queue to `{}`".format(self.queue_file))
        try:
            with open(self.queue_file, 'w') as f:
                json.dump([o.to_dict() for o in self.items], f, sort_keys=False)
        except Exception as e:
            config.logger_core.error("  ERROR: Can not save queue to `{}`:\n {}".format(self.queue_file, str(e)))
        config.logger_core.debug("  Queue saved with {} items".format(len(self.items)))


    def load(self):
        """ return true if loaded queue successfully from disk"""
        config.logger_core.debug("Loading queue from `{}`".format(self.queue_file))
        try:
            with open(self.queue_file, 'r') as f:
                data_j = json.load(f)
                for itm in data_j:
                    self.items.append(WBHItem.from_dict(itm))
        except Exception as e:
            config.logger_core.error("  ERROR: Can not load queue from `{}`:\n {}".format(self.queue_file, str(e)))
        config.logger_core.debug("  Queue loaded with {} items".format(len(self.items)))


    @staticmethod
    def backup_database(blackhole):
        config.logger_core.debug("Sending database backup to blackhole...")
        try:
            db_root_path, db_filename = os.path.split(config.Database.get_db_filepath())
            # Create a new WBHItem for database backup
            db_wbhi: WBHItem = WBHItem(size=os.stat(config.Database.get_db_filepath()).st_size,
                                       full_path=config.Database.get_db_filepath(),
                                       root_path=db_root_path,
                                       filename=db_filename,
                                       is_dir=False,
                                       state=QueueState.UPLOADING,
                                       modified_at=os.path.getmtime(config.Database.get_db_filepath()),
                                       created_at=os.path.getctime(config.Database.get_db_filepath()),
                                       checksum=get_checksum_sha256_file(config.Database.get_db_filepath()),
                                       checksum_type=ChecksumType.SHA256)
            # Send Database backup to blackhole
            if config.TelegramBot.send_file(item_wbhi=db_wbhi,
                                            blackhole=blackhole,
                                            chunk_size=config.core['chunk_size'],
                                            temp_dir=config.core['temp_dir'],
                                            encryption_type=EncryptionType.ChaCha20Poly1305,
                                            encryption_secret=config.core['backup_pass']):
                # combine all chunks checksum,encryption and file_id to string
                db_chunks = []
                db_c: WBHChunk
                for db_c in db_wbhi.chunks:
                    db_chunks.append(';'.join(
                        [db_c.encryption.name, db_c.encryption_data, db_c.checksum_type.name, db_c.checksum,
                         db_c.file_id]))
                raw_db_backup_data = '^'.join(db_chunks).encode()
                # Encrypt raw_db_backup_data with backup_pass in blackhole section of config
                encrypted_data, key, nonce = chacha20poly1305_encrypt_data(data=raw_db_backup_data,
                                                                           secret=config.core['backup_pass'].encode())
                # Combine encrpyted data with key and nonce of chacha20poly1305
                backup_string = compress_bytes_to_string_b64zlib(key + nonce + encrypted_data)
                # limit sending string to 4000 characters
                str_parts = [backup_string[i:i + 4000] for i in range(0, len(backup_string), 4000)]
                for sp in str_parts:
                    # Send backup_string as a normal message with #WBHBackup tag
                    config.TelegramBot.send_msg(chat_id=blackhole.telegram_id,
                                                text="{}\nb64zlib\n```{}```\n#WBHBackup"
                                                .format(datetime.today().strftime('%Y-%m-%d %H:%M:%S'), sp))
                return str_parts
            else:
                config.logger_core.error("ERROR: Could send encrypted database backup  to BlackHole!!!")
        except Exception as e:
            config.logger_core.error(
                "ERROR: Could send encrypted database backup  to BlackHole: ", str(e))
        return None


    def process_queue_list(self, telegram_id: str, items: list, parent: WBHItem = None):
        """ Empty queue by sending items to BlackHole. Return True if there was nothing to do """
        everything_is_done = True
        item: WBHItem
        for item in items:
            config.need_backup = True
            # Check if item is file or directory
            if item.is_dir:
                # == Directory ==
                try:
                    if item.state == QueueState.INQUEUE:
                        everything_is_done = False
                        # Update item state
                        item.state = QueueState.UPLOADING
                        # get item checksum
                        item.checksum = get_checksum_sha256_folder(item.full_path, logger=config.logger_core)
                        item.checksum_type = ChecksumType.SHA256
                        # Add to Database and Update db_id on queue item
                        item.db_id = config.Database.add_item(item_wbhi=item, blackhole_id=self.blackhole.id,
                                                              parent_id=parent.db_id if parent else None)
                        if item.db_id:  # If item added to database
                            # Update item state
                            item.state = QueueState.DONE
                            # Save Queue to disk
                            self.save()
                    # else:
                    #     config.logger_core.debug(
                    #         " `{}` state is {}. Ignore item itself. Checking Children...".format(item.filename,
                    #                                                                                item.state.name))
                    if item.state == QueueState.DONE:
                        # Check children
                        if item.children:
                            if self.process_queue_list(telegram_id, item.children, item):
                                # All children of a root item are in DONE state
                                # Remove folder
                                shutil.rmtree(item.full_path, ignore_errors=True)
                                config.logger_core.debug("`{}` removed from disk.".format(item.filename))
                                item.state = QueueState.DELETED
                                # Save Queue to disk
                                self.save()

                    if item.state == QueueState.DELETED and parent is None:
                        # Remove top level item with DELETED state, that means all chunks are sent
                        self.remove(item)
                        config.logger_core.debug("`{}` removed from queue.".format(item.filename))
                        config.logger_core.info("`{}` has been sent to blackhole.".format(item.filename))
                        # Save Queue to disk
                        self.save()
                except Exception as e:
                    config.logger_core.error("ERROR: Could add item `{}` to BlackHole: {}"
                                             .format(item.filename, str(e)))
            else:
                # == File ==
                if item.state == QueueState.INQUEUE:
                    try:
                        everything_is_done = False
                        # Update item state
                        item.state = QueueState.UPLOADING
                        # get item checksum
                        item.checksum = get_checksum_sha256_file(item.full_path, logger=config.logger_core)
                        item.checksum_type = ChecksumType.SHA256
                        # Add to Database and update db_id on queue
                        item.db_id = config.Database.add_item(item_wbhi=item, blackhole_id=self.blackhole.id,
                                                              parent_id=parent.db_id if parent else None)
                        # Save Queue to disk
                        self.save()
                    except Exception as e:
                        config.logger_core.error("ERROR: Could add item `{}` to Database: {}"
                                                 .format(item.filename, str(e)))
                if item.state == QueueState.UPLOADING:
                    try:
                        everything_is_done = False
                        # Send File to blackhole
                        if config.TelegramBot.send_file(item_wbhi=item, blackhole=self.blackhole,
                                                        chunk_size=config.core['chunk_size'],
                                                        temp_dir=config.core['temp_dir'],
                                                        encryption_type=self.blackhole.encryption_type,
                                                        encryption_secret=self.blackhole.encryption_pass,
                                                        delay_between_chunks=config.core['path_check_interval']):
                            config.logger_core.debug("Sent `{}` to BlackHole.".format(item.filename))
                            # Update item state and db_id
                            item.state = QueueState.DONE
                        else:
                            config.logger_core.error(
                                "ERROR: Could not send `{}` to BlackHole????".format(item.filename))
                        # Save Queue to disk
                        self.save()
                    except Exception as e:
                        config.logger_core.error(
                            "ERROR: Could add item `{}` to BlackHole: ".format(item.filename, str(e)))
                if item.state == QueueState.DONE:
                    everything_is_done = False
                    try:
                        # Check if all chunks are sent
                        all_chunks_done = True
                        chunk: WBHChunk
                        for chunk in item.chunks:
                            if chunk.state == QueueState.UPLOADING:
                                all_chunks_done = False
                                config.TelegramBot.send_chunk_file(chunk=chunk, blackhole=self.blackhole)
                                # Save Queue to disk
                                self.save()
                                self.logger.debug(f"Rest for {config.core['path_check_interval']} secs...")
                                time.sleep(config.core['path_check_interval'])
                        if all_chunks_done:  # If all there is no chunk with UPLOADING state
                            # Add all chunks to Database
                            chunk: WBHChunk
                            for chunk in item.chunks:
                                if chunk.state == QueueState.DONE:
                                    chunk.db_id = config.Database.add_chunk(chunk=chunk, blackhole_id=self.blackhole.id,
                                                                            parent_id=item.db_id)
                                    chunk.state = QueueState.DELETED
                            # Remove file
                            os.remove(item.full_path)
                            item.state = QueueState.DELETED
                            config.logger_core.debug("`{}` removed from disk.".format(item.filename))
                            config.logger_core.info("`{}` has been sent to blackhole.".format(item.filename))
                            # Save Queue to disk
                            self.save()
                            # Update chunks_count
                            config.Database.update_item_chunk_count(item_wbhi=item, chunk_count=len(item.chunks))
                    except Exception as e:
                        config.logger_core.error(
                            "ERROR: Could add item `{}` to BlackHole: ".format(item.filename, str(e)))
                if item.state == QueueState.DELETED and parent is None:
                    # Remove top level item with DELETED state, that means all chunks are sent
                    self.remove(item)
                    config.logger_core.debug("`{}` removed from queue.".format(item.filename))
                    # Save Queue to disk
                    self.save()

        # Backup Database to blackhole
        if len(items) == 0 and config.need_backup:
            config.need_backup = WBHQueue.backup_database(blackhole=self.blackhole) is None
            config.logger_core.info("Queue is empty. Backup database is done.")

        return everything_is_done


    def process_queue(self, telegram_id: str):
        """ Empty queue by sending items to BlackHole """
        return self.process_queue_list(telegram_id, self.items)
