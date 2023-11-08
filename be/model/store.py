# import logging
# import os
# from pymongo import MongoClient
#
#
# class Store:
#
#     def __init__(self, db_uri, db_name):
#         # db_uri = 'mongodb://localhost:27017'
#         # self.user_col = None
#         # self.user_store_col = None
#         # self.store_col = None
#         # self.new_order_col = None
#         # self.new_order_detail_col = None
#         self.client = MongoClient(db_uri)
#         # db_name = 'bookstoredb'
#         self.db = self.client[db_name]
#         self.init_tables()
#
#     def init_tables(self):
#         try:
#             self.user_col = self.db['user']
#             self.user_store_col = self.db['user_store']
#             self.store_col = self.db['store']
#             self.new_order_col = self.db['new_order']
#             self.new_order_detail_col = self.db['new_order_detail']
#
#         except Exception as e:
#             print(e)
#
#
# database_instance: Store = None
#
#
# def init_database(db_uri, db_name):
#     global database_instance
#     database_instance = Store(db_uri, db_name)
#
#
# def get_db_conn():
#     global database_instance
#     return database_instance

import os
import pymongo


class Store:
    def __init__(self, db_url, db_name):
        self.client = pymongo.MongoClient(db_url)
        self.db = self.client.get_database(db_name)
        self.user_col = self.db['user']
        self.user_store_col = self.db['user_store']
        self.store_col = self.db['store']
        self.new_order_col = self.db['new_order']
        self.new_order_detail_col = self.db['new_order_detail']

    def init_collections(self):
        self.db.user.create_index([("user_id", pymongo.ASCENDING)], unique=True)
        self.db.user_store.create_index([("user_id", pymongo.ASCENDING), ("store_id", pymongo.ASCENDING)], unique=True)
        self.db.store.create_index([("store_id", pymongo.ASCENDING), ("book_id", pymongo.ASCENDING)], unique=True)
        self.db.new_order.create_index([("order_id", pymongo.ASCENDING)], unique=True)
        self.db.new_order_detail.create_index([("order_id", pymongo.ASCENDING), ("book_id", pymongo.ASCENDING)],
                                              unique=True)


database_instance: Store = None


def init_database(db_url, db_name):
    global database_instance
    database_instance = Store(db_url, db_name)
    database_instance.init_collections()


def get_db_conn():
    global database_instance
    return database_instance


# 示例用法：
# 初始化数据库
init_database("mongodb://localhost:27017", "bookstoredb")  # 用您的MongoDB连接URL和数据库名称替换
db_conn = get_db_conn()

