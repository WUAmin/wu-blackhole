#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import os
from datetime import datetime

import telegram  # pip install python-telegram-bot --upgrade
from telegram.ext import Updater

from config import config
from wublackhole.helper import sizeof_fmt
from wublackhole.wbh_blackhole import WBHBlackHole
from wublackhole.wbh_db import WBHDatabase
from wublackhole.wbh_item import ChecksumType, EncryptionType, QueueState, WBHChunk, WBHItem
from wublackhole.wbh_watcher import get_checksum_sha256


class WBHTelegramBot:
    def __init__(self):
        logging.getLogger('telegram.bot').setLevel(config.core['log']['bot']['level'])
        logging.getLogger('telegram.ext.dispatcher').setLevel(config.core['log']['bot']['level'])
        logging.getLogger('telegram.vendor.ptb_urllib3.urllib3.connectionpool').setLevel(logging.ERROR)
        logging.getLogger('telegram.vendor.ptb_urllib3.urllib3.util.retry').setLevel(logging.ERROR)

        self.updater = Updater(token=config.core['bot']['api'], request_kwargs=config.core['bot']['proxy'],
                               use_context=True)
        # dispatcher = self.updater.dispatcher

        # Register /start
        # cmd_start_handler = CommandHandler('start', self.cmd_start)
        # dispatcher.add_handler(cmd_start_handler)

        # Register /start
        # cmd_id_handler = CommandHandler('id', self.cmd_id)
        # dispatcher.add_handler(cmd_id_handler)

        # Register all messages
        # textmsg_handler = MessageHandler(Filters.text, textmsg, message_updates=True, channel_post_updates=False)
        # dispatcher.add_handler(textmsg_handler)

        # Register all messages
        # allmsg_handler = MessageHandler(Filters.all, self.allmsg, message_updates=True, channel_post_updates=True)
        # allmsg_handler = MessageHandler(Filters.all, self.allmsg)
        # dispatcher.add_handler(allmsg_handler)


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
        if org_filename is not None:
            cap_text += f"Original Name: `{org_filename}`\n"
        if org_filepath is not None:
            cap_text += f"Original Path: `{org_filepath}`\n"
        if org_size is not None:
            cap_text += "Original Size: `{}` (`{}`)\n".format(org_size, sizeof_fmt(org_size))
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
            config.logger_bot.error("❌ Error  _send_chunk : %s" % str(e))
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
                config.logger_bot.debug(f"  ✅ `{chunk.filename}` file sent to BlackHole")
                # Save queue
                blackhole.queue.save()
                # Remove chunk file
                os.remove(chunk.org_fullpath)
                config.logger_bot.debug(f"  🕘 `{chunk.filename}` file removed.")
            else:
                # == There was a problem ==
                config.logger_bot.error(
                    "  ❌ ERROR: failed to send chunk#{} `{}` to BlackHole. res".format(chunk.index, chunk.filename))


    def send_folder(self, item_wbhi: WBHItem, blackhole: WBHBlackHole):
        """ return True on successfully sending all chunks of all items in the directory"""
        # org_filepath_rel = org_filepath[len(config.core['temp_dir']):]
        org_filepath_rel = os.path.join(*item_wbhi.parents, item_wbhi.filename)
        print(f"🕑 Sending directory `{org_filepath_rel}`...")
        try:
            # Send all items in the directory
            itm: WBHItem
            for itm in item_wbhi.children:
                if itm.is_dir:
                    # Directory
                    self.send_folder(itm, blackhole)
                else:
                    # File
                    self.send_file(itm, blackhole)
        except Exception as e:
            print(f"  ❌ ERROR: Could not send `{item_wbhi.full_path}` to BlackHole: {str(e)}")
            return False
        return True


    def send_file(self, item_wbhi: WBHItem, blackhole: WBHBlackHole) -> bool:
        """ return True if all chunks sent successfully """
        is_all_successful = True
        if item_wbhi.chunks is None:
            # New list if there is no chunk yet
            item_wbhi.chunks = []
        # Prepare original filename
        org_fullpath = os.path.join(*item_wbhi.parents, item_wbhi.filename)
        chunk_i = len(item_wbhi.chunks)
        config.logger_bot.debug("🕑 Sending file `{}` in chunks of {}"
                                .format(org_fullpath, sizeof_fmt(config.core['chunk_size'])))
        try:
            # Open Original File
            with open(item_wbhi.full_path, 'rb') as org_file:
                # Seek to the start position of last existing chunk if exist.
                org_file.seek(chunk_i * config.core['chunk_size'])
                while True:
                    # Read a chunk
                    chunk_bytes = org_file.read(config.core['chunk_size'])
                    chunk_filename = "WBHTF{}.p{:04d}".format(datetime.today().strftime('%Y%m%d%H%M%S%f'), chunk_i)
                    chunk = WBHChunk(size=len(chunk_bytes),
                                     filename=chunk_filename,
                                     index=chunk_i,
                                     org_filename=os.path.split(item_wbhi.full_path)[1],
                                     org_fullpath=os.path.join(config.core['temp_dir'], chunk_filename),
                                     org_size=os.fstat(org_file.fileno()).st_size,
                                     msg_id=None,
                                     state=QueueState.UPLOADING,
                                     checksum=get_checksum_sha256(chunk_bytes),
                                     checksum_type=ChecksumType.SHA256,
                                     encryption=EncryptionType.NONE,
                                     encryption_data=None,
                                     parent_qid=item_wbhi.parent_qid,
                                     parent_db_id=item_wbhi.db_id)
                    config.logger_bot.debug("  🕑 Read {}".format(sizeof_fmt(chunk.size)))
                    if chunk_bytes:
                        try:
                            # Open chunk file to write
                            with open(chunk.org_fullpath, 'wb') as chunk_file_w:
                                # write to chunk file
                                chunk_file_w.write(chunk_bytes)
                                config.logger_bot.debug("  🕒 Wrote {} to `{}` file"
                                                        .format(sizeof_fmt(len(chunk_bytes)), chunk.filename))
                            config.logger_bot.debug(f"  🕕 Sending `{chunk.filename}` file to BlackHole")
                            # Send chunk file to blackhole
                            self.send_chunk_file(chunk=chunk, blackhole=blackhole)
                            # Add to chunks list
                            item_wbhi.chunks.append(chunk)
                        except Exception as e:
                            is_all_successful = False
                            config.logger_bot.error(
                                f"  ❌ ERROR: Could not send chunk#{chunk_i} `{chunk_filename}` to BlackHole: {str(e)}")
                    else:
                        break
                    chunk_i += 1
        except Exception as e:
            is_all_successful = False
            config.logger_bot.error(f"  ❌ ERROR: Could not send `{item_wbhi.full_path}` to BlackHole: {str(e)}")
        return is_all_successful


    def get_chunk(self, chunk: WBHDatabase.WBHDbChunks, path_to_save: str):
        try:
            chunk_file = self.updater.bot.get_file(chunk.file_id)
            chunk_file.download(path_to_save)
        except Exception as e:
            config.logger_bot.error("  ❌ ERROR: Could not download chunk#{} by name of `{}` from BlackHole: {}"
                                    .format(chunk.index, chunk.filename, str(e)))
