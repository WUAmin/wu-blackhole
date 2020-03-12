#!/usr/bin/python3
# -*- coding: utf-8 -*-
import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
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
        filename = Column(String)
        size = Column(BigInteger)
        index = Column(BigInteger)
        uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)
        # blackhole - One To Many
        blackhole_id = Column(BigInteger, ForeignKey('blackholes.id'))
        parent_blackhole = relationship('WBHDbBlackHoles')
        # item - One To Many
        items_id = Column(BigInteger, ForeignKey('items.id'))
        parent_item = relationship('WBHDbItems', back_populates="chunks")


        def __repr__(self):
            return f'WBHDbChunks {self.filename}'


    def __init__(self, db_path, echo=False):
        # self.db_path = db_path

        # Check existance of db variable
        if 'engine' not in locals():
            # initialize a database
            self.engine = create_engine('sqlite:///' + db_path, echo=echo)
            self.conn = self.engine.connect()
            self.Session = sessionmaker(bind=self.engine)
            self.Base.metadata.create_all(self.engine)

        print("INIT")


    def get_blackhole(self, name: str):
        session = self.Session()
        return session.query(self.WBHDbBlackHoles).filter_by(name=name).first()


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
            print("  ❌ ERROR: Can not add folder `{}` to database:\n {}".format(item.full_path, str(e)))


    def add_item(self, item_wbhi: WBHItem, blackhole_id, parent_id):
        new_item = None
        try:
            session = self.Session()
            new_item = self.WBHDbItems(filename=item_wbhi.filename,
                                       is_dir=item_wbhi.is_dir,
                                       size=item_wbhi.size,
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
                new_item.chunks_count = len(item_wbhi.chunks)
            # Add/Commit item to database
            session.add(new_item)
            session.commit()
        except Exception as e:
            print("  ❌ ERROR: Can not add item `{}` to database:\n {}".format(item_wbhi.full_path, str(e)))

        if not item_wbhi.is_dir:
            # Add all chunks to Database
            ch: WBHChunk
            try:
                session = self.Session()
                for ch in item_wbhi.chunks:
                    new_ch = self.WBHDbChunks(msg_id=ch.MessageID,
                                              filename=ch.Filename,
                                              size=ch.Size,
                                              index=ch.Index,
                                              blackhole_id=blackhole_id,
                                              items_id=new_item.id)
                    # Add/Commit item to database
                    session.add(new_ch)
                session.commit()
            except Exception as e:
                print("  ❌ ERROR: Can not add chunks of `{}` to database:\n {}".format(item_wbhi.full_path, str(e)))
        return new_item


    def __exit__(self, exc_type, exc_value, traceback):
        pass
        # Check existance of db variable
        # if 'db' not in locals():
        #     # Close database
        #     self.db.close()
