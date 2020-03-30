#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

import telegram  # pip install python-telegram-bot --upgrade
from telegram.ext import Updater

from common.helper import ChecksumType, EncryptionType, chacha20poly1305_encrypt_data, get_checksum_sha256
# from config import config
from common.helper import sizeof_fmt
from common.wbh_db import WBHDbChunks
from wublackhole.wbh_blackhole import WBHBlackHole
from wublackhole.wbh_item import QueueState, WBHChunk, WBHItem


class WBHTelegramBot:
    def __init__(self, api, logger: logging.Logger, proxy=None, log_level=logging.INFO):
        self.logger = logger
        logging.getLogger('telegram.bot').setLevel(log_level)
        logging.getLogger('telegram.ext.dispatcher').setLevel(log_level)
        logging.getLogger('telegram.vendor.ptb_urllib3.urllib3.connectionpool').setLevel(logging.ERROR)
        logging.getLogger('telegram.vendor.ptb_urllib3.urllib3.util.retry').setLevel(logging.ERROR)

        self.updater = Updater(token=api, request_kwargs=proxy, use_context=True)


    def send_chunk(self, file_open, chunk: WBHChunk, telegram_id):
        return self._send_chunk(file_open=file_open,
                                filename=chunk.filename,
                                org_filepath=chunk.org_fullpath,
                                org_filename=chunk.org_filename,
                                org_size=chunk.org_size,
                                telegram_id=telegram_id)


    def _send_chunk(self, file_open, filename, org_filepath, org_filename,
                    telegram_id, org_size=None, reply_to_message_id=None, disable_notification=True):
        cap_text = ""
        # if org_filename is not None:
        #     cap_text += f"Original Name: `{org_filename}`\n"
        # if org_filepath is not None:
        #     cap_text += f"Original Path: `{org_filepath}`\n"
        # if org_size is not None:
        #     cap_text += "Original Size: `{}` (`{}`)\n".format(org_size, sizeof_fmt(org_size))
        cap_text += f"Filename: `{filename}`\n"

        res = None
        try:
            res = self.updater.bot.send_document(chat_id=telegram_id,
                                                 document=file_open,
                                                 filename=filename,
                                                 caption=cap_text,
                                                 reply_to_message_id=reply_to_message_id,
                                                 disable_notification=disable_notification,
                                                 parse_mode=telegram.ParseMode.MARKDOWN)

            cap_text += f"*MSGID_{res.message_id}*\n"
            cap_text += f"*FILEID_{res.document.file_id}*\n"
            self.updater.bot.editMessageCaption(chat_id=telegram_id,
                                                message_id=res.message_id,
                                                caption=cap_text,
                                                timeout=40,
                                                parse_mode=telegram.ParseMode.MARKDOWN)
        except Exception as e:
            self.logger.error("❌ Error  _send_chunk : %s" % str(e))
        return res


    def send_chunk_file(self, chunk: WBHChunk, blackhole: WBHBlackHole):
        """ Read chunk file from disk and send it to blackhole"""
        # Open chunk file to read
        with open(chunk.org_fullpath, 'rb') as chunk_file_r:
            # Read whole chunk file
            res = self.send_chunk(file_open=chunk_file_r, chunk=chunk, telegram_id=blackhole.telegram_id)
        if res is not None:
            # == sent to bot without any problem ==
            chunk.msg_id = res.message_id
            chunk.file_id = res.document.file_id
            chunk.state = QueueState.DONE
            self.logger.debug(f"  ✅ `{chunk.filename}` file sent to BlackHole")
            # Save queue
            blackhole.queue.save()
            # Remove chunk file
            os.remove(chunk.org_fullpath)
            self.logger.debug(f"  🕘 `{chunk.filename}` file removed.")
        else:
            # == There was a problem ==
            self.logger.error(
                "  ❌ ERROR: failed to send chunk#{} `{}` to BlackHole. res".format(chunk.index, chunk.filename))


    def send_file(self, item_wbhi: WBHItem, blackhole: WBHBlackHole, chunk_size: int, temp_dir: str,
                  encryption_type: EncryptionType = EncryptionType.NONE, encryption_secret: str = None) -> bool:
        """ return True if all chunks sent successfully """
        is_all_successful = True
        if item_wbhi.chunks is None:
            # New list if there is no chunk yet
            item_wbhi.chunks = []
        # Prepare original filename
        org_fullpath = os.path.join(*item_wbhi.parents, item_wbhi.filename)
        chunk_i = len(item_wbhi.chunks)
        self.logger.debug("🕑 Sending file `{}` in chunks of {}"
                          .format(org_fullpath, sizeof_fmt(chunk_size)))
        try:
            # Open Original File
            with open(item_wbhi.full_path, 'rb') as org_file:
                # Seek to the start position of last existing chunk if exist.
                org_file.seek(chunk_i * chunk_size)
                while True:
                    # Read a chunk
                    chunk_bytes = org_file.read(chunk_size)
                    if chunk_bytes:
                        # get checksum before encryption
                        checksum = get_checksum_sha256(chunk_bytes)
                        # Check Encryption
                        encryption_data = None
                        if encryption_type == EncryptionType.ChaCha20Poly1305:
                            # Encrypt chunk data
                            self.logger.debug("🕑 Encrypting chunk using ChaCha20Poly1305 ...")
                            chunk_bytes, key, nonce = chacha20poly1305_encrypt_data(data=chunk_bytes,
                                                                                    secret=encryption_secret.encode())
                            encryption_data = '{}O{}'.format(key.hex(), nonce.hex())

                        chunk_filename = "WBHTF{}.p{:04d}".format(datetime.today().strftime('%Y%m%d%H%M%S%f'), chunk_i)
                        chunk = WBHChunk(size=len(chunk_bytes),
                                         filename=chunk_filename,
                                         index=chunk_i,
                                         org_filename=os.path.split(item_wbhi.full_path)[1],
                                         org_fullpath=os.path.join(temp_dir, chunk_filename),
                                         org_size=os.fstat(org_file.fileno()).st_size,
                                         msg_id=None,
                                         state=QueueState.UPLOADING,
                                         checksum=checksum,
                                         checksum_type=ChecksumType.SHA256,
                                         encryption=encryption_type,
                                         encryption_data=encryption_data,
                                         parent_qid=item_wbhi.parent_qid,
                                         parent_db_id=item_wbhi.db_id)
                        self.logger.debug("  🕑 Read {}".format(sizeof_fmt(chunk.size)))
                        try:
                            # Open chunk file to write
                            with open(chunk.org_fullpath, 'wb') as chunk_file_w:
                                # write to chunk file
                                chunk_file_w.write(chunk_bytes)
                                self.logger.debug("  🕒 Wrote {} to `{}` file"
                                                  .format(sizeof_fmt(len(chunk_bytes)), chunk.filename))
                            self.logger.debug(f"  🕕 Sending `{chunk.filename}` file to BlackHole")
                            # Send chunk file to blackhole
                            self.send_chunk_file(chunk=chunk, blackhole=blackhole)
                            # Add to chunks list
                            item_wbhi.chunks.append(chunk)
                        except Exception as e:
                            is_all_successful = False
                            self.logger.error(
                                f"  ❌ ERROR: Could not send chunk#{chunk_i} `{chunk_filename}` to BlackHole: {str(e)}")
                    else:
                        break
                    chunk_i += 1
        except Exception as e:
            is_all_successful = False
            self.logger.error(f"  ❌ ERROR: Could not send `{item_wbhi.full_path}` to BlackHole: {str(e)}")
        return is_all_successful


    def send_msg(self, chat_id, text, parse_mode=telegram.ParseMode.MARKDOWN):
        return self.updater.bot.send_message(chat_id=chat_id,
                                             text=text,
                                             parse_mode=parse_mode)


    def get_file_by_id(self, file_id, path_to_save: str):
        file = self.updater.bot.get_file(file_id)
        return file.download(path_to_save)


    def get_chunk(self, chunk: WBHDbChunks, path_to_save: str):
        try:
            return self.get_file_by_id(chunk.file_id, path_to_save)
        except Exception as e:
            self.logger.error("  ❌ ERROR: Could not download chunk#{} by name of `{}` from BlackHole: {}"
                              .format(chunk.index, chunk.filename, str(e)))
        return None
