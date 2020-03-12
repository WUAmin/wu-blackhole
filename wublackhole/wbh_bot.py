#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import os
import telegram  # pip install python-telegram-bot --upgrade
from datetime import datetime
from telegram.ext import Updater
from config import config
from wublackhole.wbh_item import WBHChunk, WBHItem


class WBHTelegramBot:
    def __init__(self, log_level=logging.ERROR):
        self.updater = Updater(token=config.core['bot']['api'], request_kwargs=config.core['bot']['proxy'],
                               use_context=True)
        # dispatcher = self.updater.dispatcher

        # Setup Log
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=log_level)
        # level = logging.INFO)

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


    # def start_bot(self):
    #     # Start BOT
    #     self.updater.start_polling()

    # def check_auth(self, chat_id):
    #     for a_id in config.core['bot']['chat_ids']['admins']:
    #         if chat_id == a_id:
    #             return AuthLevel.ADMIN
    #     for m_id in config.core['bot']['chat_ids']['mods']:
    #         if chat_id == m_id:
    #             return AuthLevel.MOD
    #     for m_id in config.core['bot']['chat_ids']['users']:
    #         if chat_id == m_id:
    #             return AuthLevel.USER
    #     return AuthLevel.UNAUTHORIZED

    # def log_update_simple(self, update):
    #     logging.info("Title: {} | Username: {} | ID: {} | Date: {} | Text: {}".format(
    #         update.effective_message.chat.title,
    #         update.effective_message.chat.username,
    #         update.effective_chat.id,
    #         update.effective_message.date,
    #         update.effective_message.text))

    # def cmd_start(self, update, context):
    #     try:
    #         auth_level = self.check_auth(update.effective_chat.id)
    #         # ------------ ADMIN_LEVEL -------------
    #         if auth_level >= settings.ADMIN_LEVEL:
    #             context.bot.send_message(chat_id=update.effective_chat.id, text="{}x Hello".format(auth_level))
    #         # ------------ GROUPS_LEVEL ------------
    #         elif auth_level >= settings.GROUPS_LEVEL:
    #             context.bot.send_message(chat_id=update.effective_chat.id, text="{}x Hello".format(auth_level))
    #         # ------------ USERS_LEVEL -------------
    #         elif auth_level >= settings.USERS_LEVEL:
    #             context.bot.send_message(chat_id=update.effective_chat.id, text="{}x Hello".format(auth_level))
    #         # --------- UNAUTHORIZED_LEVEL ---------
    #     except Exception as e:
    #         print("Error: %s" % str(e))

    # def cmd_id(self, update, context):
    #     try:
    #         # ------------ ADMIN_LEVEL -------------
    #         # ------------ GROUPS_LEVEL ------------
    #         # ------------ USERS_LEVEL -------------
    #         # --------- UNAUTHORIZED_LEVEL ---------
    #         # context.bot.send_message(chat_id=update.effective_chat.id,
    #         #                          reply_to_message_id=update.message.message_id,
    #         #                          # text="Your User ID: `{}`\nYour Message ID: `{}`"
    #         #                          text="Your User ID: `{}`"
    #         #                          .format(update.message.chat_id, update.message.message_id),
    #         #                          parse_mode=telegram.ParseMode.MARKDOWN)
    #         pass
    #     except Exception as e:
    #         print("Error: %s" % str(e))

    # def textmsg(update, context):
    #     try:
    #         auth_level = check_auth(update.effective_chat.id)
    #         log_update_simple(update)
    #         # ------------ ADMIN_LEVEL -------------
    #         if auth_level >= settings.ADMIN_LEVEL:
    #             context.bot.send_message(chat_id=update.effective_chat.id,
    #                                      reply_to_message_id=update.message.message_id,
    #                                      text="Your User ID: `{}`\nYour Message ID: `{}`"
    #                                      .format(update.message.chat_id, update.message.message_id),
    #                                      parse_mode = telegram.ParseMode.MARKDOWN)
    #         # ------------ GROUPS_LEVEL ------------
    #         # ------------ USERS_LEVEL -------------
    #         # --------- UNAUTHORIZED_LEVEL ---------
    #     except Exception as e:
    #         print("Error: %s" % str(e))

    # def allmsg(self, update, context):
    #     try:
    #         auth_level = self.check_auth(update.effective_chat.id)
    #         self.log_update_simple(update)
    #         # ------------ ADMIN_LEVEL -------------
    #         if auth_level >= settings.ADMIN_LEVEL:
    #             context.bot.send_message(chat_id=update.effective_chat.id,
    #                                      reply_to_message_id=update.message.message_id,
    #                                      text="Your User ID: `{}`\nYour Message ID: `{}`"
    #                                      .format(update.message.chat_id, update.message.message_id),
    #                                      parse_mode=telegram.ParseMode.MARKDOWN)
    #         # ------------ GROUPS_LEVEL ------------
    #         elif auth_level >= settings.GROUPS_LEVEL:
    #             if update.effective_chat.id == settings.WuMedia2_ID:
    #                 self.add_filename_to_media(update)
    #         # ------------ USERS_LEVEL -------------
    #         # --------- UNAUTHORIZED_LEVEL ---------
    #     except Exception as e:
    #         print("Error: %s" % str(e))


    def send_file_chunk(self, file_open, chunk: WBHChunk, telegram_id):
        return self.send_file(file_open=file_open,
                              filename=chunk.Filename,
                              org_filepath=chunk.OriginalFullPath,
                              org_filename=chunk.OriginalFilename,
                              org_size=chunk.OriginalSize,
                              telegram_id=telegram_id)


    def send_file(self, file_open, filename, org_filepath, org_filename,
                  telegram_id, org_size=None, reply_to_message_id=None, disable_notification=True):
        cap_text = ""
        if org_filename is not None:
            cap_text += f"Original Name: `{org_filename}`\n"
        if org_filepath is not None:
            cap_text += f"Original Path: `{org_filepath}`\n"
        if org_size is not None:
            cap_text += f"Original Size: `{org_size}`\n"
        cap_text += f"Filename: `{filename}`\n"

        try:
            res = self.updater.bot.send_document(chat_id=telegram_id,
                                                 document=file_open,
                                                 filename=filename,
                                                 caption=cap_text,
                                                 reply_to_message_id=reply_to_message_id,
                                                 disable_notification=disable_notification,
                                                 parse_mode=telegram.ParseMode.MARKDOWN)

            cap_text += f"*MSGID_{res.message_id}*\n"
        except Exception as e:
            print("❌ Error: %s" % str(e))
            return None
        self.updater.bot.editMessageCaption(chat_id=telegram_id,
                                            message_id=res.message_id,
                                            caption=cap_text,
                                            timeout=40,
                                            parse_mode=telegram.ParseMode.MARKDOWN)

        return res


    def send_folder_to_blackhole(self, item_wbhi: WBHItem, telegram_id: str):
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
                    self.send_folder_to_blackhole(itm, telegram_id)
                else:
                    # File
                    self.send_file_to_blackhole(itm, telegram_id)
        except Exception as e:
            print(f"  ❌ ERROR: Could not send `{item_wbhi.full_path}` to BlackHole: {str(e)}")
            return False
        return True


    def send_file_to_blackhole(self, item_wbhi: WBHItem, telegram_id: str):
        """ return True on successfully sending all chunks """
        item_wbhi.chunks = []
        # org_filepath_rel = org_filepath[len(config.core['temp_dir']):]
        org_filepath_rel = os.path.join(*item_wbhi.parents, item_wbhi.filename)
        ch_i = 0
        print("🕑 Sending file `{}` in chunks of {:2.3f} MB"
              .format(org_filepath_rel, float(config.core['chunk_size'] / 1024 / 1024)))
        try:
            with open(item_wbhi.full_path, 'rb') as org_file:
                while True:
                    block_bytes = org_file.read(config.core['chunk_size'])
                    tmp_filename = "WBHTF{}.p{:04d}".format(datetime.today().strftime('%Y%m%d%H%M%S%f'), ch_i)
                    tmp_filepath = os.path.join(config.core['temp_dir'], tmp_filename)
                    chunk = WBHChunk(size=len(block_bytes),
                                     filename=tmp_filename,
                                     index=ch_i,
                                     original_filename=os.path.split(item_wbhi.full_path)[1],
                                     original_fullpath=org_filepath_rel,
                                     original_size=os.fstat(org_file.fileno()).st_size)
                    print("  🕑 Read {:2.3f} MB".format(float(chunk.Size / 1024 / 1024)))
                    if block_bytes:
                        with open(tmp_filepath, 'wb') as tmp_file:
                            tmp_file.write(block_bytes)
                        print("  🕒 Wrote {:2.3f} MB to `{}` file"
                              .format(float(len(block_bytes) / 1024 / 1024), tmp_filename))
                        print(f"  🕕 Sending `{tmp_filename}` file to BlackHole")
                        with open(tmp_filepath, 'rb') as tmp_file:
                            res = self.send_file_chunk(file_open=tmp_file, chunk=chunk, telegram_id=telegram_id)
                            if res is not None:
                                chunk.MessageID = res.message_id
                                print(f"  ✅ `{tmp_filename}` file sent to BlackHole")
                            else:
                                print(f"  ❌ ERROR: Could not send chunk #{ch_i} `{tmp_filename}` to BlackHole")

                        os.remove(tmp_filepath)
                        print(f"  🕘 `{tmp_filename}` file removed.")
                    else:
                        break
                    ch_i += 1
                    item_wbhi.chunks.append(chunk)
        except Exception as e:
            print(f"  ❌ ERROR: Couldn't send `{item_wbhi.full_path}` to BlackHole: {str(e)}")
            return False
        return True
