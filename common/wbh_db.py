#!/usr/bin/python3
# -*- coding: utf-8 -*-
import datetime
import logging

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.dialects.sqlite import SMALLINT
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import noload, relationship, sessionmaker, lazyload

# from config import config
from wublackhole.wbh_item import WBHChunk, WBHItem


class WBHDatabase:
    TOP_PARENT = 'WBH_ROOT'

    Base = declarative_base()


    class WBHDbBlackHoles(Base):
        __tablename__ = 'blackholes'

        id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
        name = Column(String)
        size = Column(BigInteger)
        telegram_id = Column(String)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        # items - One To Many
        items = relationship("WBHDbItems", back_populates="parent_blackhole")


        def __repr__(self):
            return f'WBHDbBlackHoles {self.name}'


    class WBHDbItems(Base):
        __tablename__ = 'items'

        id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
        filename = Column(String)
        is_dir = Column(Boolean)
        size = Column(BigInteger)
        items_count = Column(BigInteger)
        chunks_count = Column(BigInteger)
        checksum = Column(String)
        checksum_type = Column(SMALLINT)
        root_path = Column(String)
        full_path = Column(String)
        created_at = Column(DateTime, default=datetime.datetime.utcnow)
        modified_at = Column(DateTime, default=datetime.datetime.utcnow)
        uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
        # blackhole - One To Many
        blackhole_id = Column(BigInteger, ForeignKey('blackholes.id'))
        parent_blackhole = relationship('WBHDbBlackHoles', back_populates="items")
        # items - One To Many
        parent_id = Column(BigInteger, ForeignKey('items.id'))
        parent_item = relationship('WBHDbItems')
        items = relationship("WBHDbItems")
        # chunks - One To Many
        chunks = relationship("WBHDbChunks", back_populates="parent_item")


        def __repr__(self):
            return f'WBHDbItems {self.filename}'


    class WBHDbChunks(Base):
        __tablename__ = 'chunks'

        id = Column(Integer, primary_key=True, autoincrement=True, nullable=False)
        msg_id = Column(BigInteger)
        file_id = Column(String)
        filename = Column(String)
        size = Column(BigInteger)
        index = Column(BigInteger)
        checksum = Column(String)
        checksum_type = Column(SMALLINT)
        encryption = Column(SMALLINT)
        encryption_data = Column(String)
        uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
        # blackhole - One To Many
        blackhole_id = Column(BigInteger, ForeignKey('blackholes.id'))
        parent_blackhole = relationship('WBHDbBlackHoles')
        # item - One To Many
        items_id = Column(BigInteger, ForeignKey('items.id'))
        parent_item = relationship('WBHDbItems', back_populates="chunks")


        def __repr__(self):
            return f'WBHDbChunks {self.filename}'


    def __init__(self, db_path, logger: logging.Logger, echo=False):
        self.logger = logger
        self._db_path = db_path

        # Check existance of db variable
        if 'engine' not in locals():
            # initialize a database
            self.engine = create_engine('sqlite:///' + self._db_path, echo=echo)
            self.conn = self.engine.connect()
            self.Session = sessionmaker(bind=self.engine)
            self.Base.metadata.create_all(self.engine)


    def get_db_filepath(self):
        return self._db_path

    def get_blackholes(self):
        session = self.Session()
        return session.query(self.WBHDbBlackHoles) \
            .options(noload(self.WBHDbBlackHoles.items)) \
            .all()

    def get_blackhole_by_name(self, name: str):
        session = self.Session()
        return session.query(self.WBHDbBlackHoles) \
            .options(noload(self.WBHDbBlackHoles.items)) \
            .filter_by(name=name) \
            .first()


    def get_blackhole_by_id(self, _id):
        session = self.Session()
        # return session.query(self.WBHDbBlackHoles).options(noload('items')).filter_by(id=_id).first()
        return session.query(self.WBHDbBlackHoles).options(noload(self.WBHDbBlackHoles.items)).filter_by(id=_id).first()


    def get_items_by_parent_id(self, blackhole_id, items_parent=None):
        session = self.Session()
        return session.query(self.WBHDbItems) \
            .options(noload(self.WBHDbItems.items)) \
            .options(noload(self.WBHDbItems.chunks)) \
            .filter_by(blackhole_id=blackhole_id, parent_id=items_parent) \
            .all()


    def add_blackhole(self, name: str, size: int, telegram_id: str):
        bh_new = self.WBHDbBlackHoles(name=name,
                                      size=size,
                                      telegram_id=telegram_id)
        session = self.Session()
        session.add(bh_new)
        session.commit()
        # print(bh_new)
        return bh_new


    def add_item_folder(self, item: WBHItem, blackhole_id, parent_item):
        try:
            if item.is_dir:
                res = self.add_item(item, blackhole_id, None)
                for child in item.children:
                    self.add_item_folder(child, blackhole_id, res.id)
            else:
                self.add_item(item, blackhole_id, parent_item)
        except Exception as e:
            self.logger.error(
                "  ❌ ERROR: Can not add folder `{}` to database:\n {}".format(item.full_path, str(e)))


    def add_item(self, item_wbhi: WBHItem, blackhole_id, parent_id):
        """ return id of item in database if successful, None on error"""
        new_item = None
        try:
            self.logger.debug("🕐 Adding item `{}` to Database".format(item_wbhi.filename))
            session = self.Session()
            new_item = self.WBHDbItems(filename=item_wbhi.filename,
                                       is_dir=item_wbhi.is_dir,
                                       size=item_wbhi.size,
                                       checksum=item_wbhi.checksum,
                                       checksum_type=item_wbhi.checksum_type.value,
                                       root_path=item_wbhi.root_path,
                                       full_path=item_wbhi.full_path,
                                       blackhole_id=blackhole_id,
                                       parent_id=parent_id,
                                       created_at=datetime.datetime.fromtimestamp(item_wbhi.created_at),
                                       modified_at=datetime.datetime.fromtimestamp(item_wbhi.modified_at))
            if item_wbhi.is_dir:
                # item_counts for directories
                new_item.items_count = item_wbhi.total_children
            else:
                # chunks_count for files
                if item_wbhi.chunks:
                    new_item.chunks_count = len(item_wbhi.chunks)
            # Add/Commit item to database
            session.add(new_item)
            session.commit()
            self.logger.debug("✅ Item `{}` added to Database.".format(item_wbhi.filename))
        except Exception as e:
            self.logger.error(
                "  ❌ ERROR: Can not add item `{}` to database:\n {}".format(item_wbhi.full_path, str(e)))

        # if not item_wbhi.is_dir:
        #     # Add all chunks to Database
        #     ch: WBHChunk
        #     try:
        #         session = self.Session()
        #         for ch in item_wbhi.chunks:
        #             new_ch = self.WBHDbChunks(msg_id=ch.msg_id,
        #                                       filename=ch.filename,
        #                                       size=ch.size,
        #                                       index=ch.index,
        #                                       blackhole_id=blackhole_id,
        #                                       items_id=new_item.id)
        #             # Add/Commit item to database
        #             session.add(new_ch)
        #         session.commit()
        #     except Exception as e:
        #         self.logger.error("  ❌ ERROR: Can not add chunks of `{}` to database:\n {}"
        #                                  .format(item_wbhi.full_path, str(e)))
        return new_item.id if new_item else None


    def add_chunk(self, chunk: WBHChunk, blackhole_id, parent_id):
        """ return id of chunk in database if successful, None on error"""
        new_chunk = None
        try:
            self.logger.debug("🕐 Adding chunk#{} of `{}` to Database".format(chunk.index, chunk.org_filename))
            session = self.Session()
            new_chunk = self.WBHDbChunks(msg_id=chunk.msg_id,
                                         file_id=chunk.file_id,
                                         filename=chunk.filename,
                                         size=chunk.size,
                                         index=chunk.index,
                                         checksum=chunk.checksum,
                                         checksum_type=chunk.checksum_type.value,
                                         encryption=chunk.encryption.value,
                                         encryption_data=chunk.encryption_data,
                                         blackhole_id=blackhole_id,
                                         items_id=parent_id)
            # Add/Commit chunk to database
            session.add(new_chunk)
            session.commit()
            self.logger.debug("✅ chunk#{} of `{}` added to Database.".format(chunk.index, chunk.org_filename))
        except Exception as e:
            self.logger.error(
                "  ❌ ERROR: Can not add  chunk#{} of `{}` to database:\n {}".format(chunk.index, chunk.org_filename, str(e)))
        return new_chunk.id if new_chunk else None


    def update_item_chunk_count(self, item_wbhi: WBHItem, chunk_count):
        try:
            self.logger.debug("🕐 Update chunk_count for item `{}` in database".format(item_wbhi.filename))
            session = self.Session()

            # Add/Commit item to database
            item_db = session.query(self.WBHDbItems) \
                .options(noload(self.WBHDbItems.items)) \
                .options(noload(self.WBHDbItems.chunks)) \
                .filter_by(id=item_wbhi.db_id) \
                .first()
            item_db.chunks_count = chunk_count
            session.commit()
            self.logger.debug(
                "✅ chunk_count for Item `{}` updated in Database to {}.".format(item_wbhi.filename, chunk_count))
        except Exception as e:
            self.logger.error("  ❌ ERROR: Can not update chunk_count for item `{}` on database:\n {}"
                                     .format(item_wbhi.full_path, str(e)))


    def get_item_by_id(self, blackhole_id, item_id) -> WBHDbItems:
        try:
            self.logger.debug("🕐 Get item by id `{}` from database".format(item_id))
            session = self.Session()
            # get item from database
            return session.query(self.WBHDbItems) \
                .filter_by(blackhole_id=blackhole_id, id=item_id) \
                .options(lazyload(self.WBHDbItems.chunks)) \
                .options(lazyload(self.WBHDbItems.items)) \
                .first()
        except Exception as e:
            self.logger.error("  ❌ ERROR: Can not get item by id `{}` from database:\n {}"
                              .format(item_id, str(e)))


    def get_chunks_by_item_id(self, blackhole_id, item_id):
        try:
            self.logger.debug("🕐 Get chunks for item id `{}` from database".format(item_id))
            session = self.Session()
            # get chunks from database
            return session.query(self.WBHDbChunks) \
                .filter_by(blackhole_id=blackhole_id, items_id=item_id) \
                .all()
        except Exception as e:
            self.logger.error("  ❌ ERROR: Can not get chunks for item id `{}` on database:\n {}"
                              .format(item_id, str(e)))


    def __exit__(self, exc_type, exc_value, traceback):
        pass
        # Check existance of db variable
        # if 'db' not in locals():
        #     # Close database
        #     self.db.close()
