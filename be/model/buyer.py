import sqlite3 as sqlite
import uuid
import json
import logging
from be.model import db_conn
from be.model import error
import pymongo.errors


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
            self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            for book_id, count in id_and_count:

                row = self.conn.store_col.find_one({"book_id": book_id, "store_id": store_id},
                                                   {"book_id": 1, "stock_level": 1, "book_price": 1})
                if row is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = row["stock_level"]
                # book_info = row["book_info"]
                # book_info_json = json.loads(book_info)
                # price = book_info_json.get("price")
                price = row["book_price"]

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                result = self.conn.store_col.update_one(
                    {"store_id": store_id, "book_id": book_id, "stock_level": {"$gte": count}},
                    {"$inc": {"stock_level": -count}})

                if result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)

                self.conn.new_order_detail_col.insert_one(
                    {"order_id": uid, "book_id": book_id, "count": count, "price": price})

            self.conn.new_order_col.insert_one({"order_id": uid, "store_id": store_id, "user_id": user_id})
            order_id = uid

        except BaseException as e:
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        conn = self.conn
        try:

            row = conn.new_order_col.find_one({"order_id": order_id}, {"order_id": 1, "user_id": 1, "store_id": 1})
            if row is None:
                return error.error_invalid_order_id(order_id)

            order_id = row["order_id"]
            buyer_id = row["user_id"]
            store_id = row["store_id"]

            if buyer_id != user_id:
                return error.error_authorization_fail()

            result = conn.user_col.find_one({"user_id": buyer_id}, {"balance": 1, "password": 1})
            if result is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = result["balance"]
            if password != result["password"]:
                return error.error_authorization_fail()

            result = conn.user_store_col.find_one({"store_id": store_id}, {"store_id": 1, "user_id": 1})
            if result is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = result["user_id"]

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            result = conn.new_order_detail_col.find({"order_id": order_id}, {"book_id": 1, "count": 1, "price": 1})
            total_price = 0
            for row in result:
                count = row["count"]
                price = row["price"]
                total_price = total_price + price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            result = conn.user_col.update_one({"user_id": user_id, "balance": {"$gte": total_price}},
                                              {"$inc": {"balance": -total_price}})

            if result.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            result = conn.user_col.update_one({"user_id": buyer_id}, {"$inc": {"balance": total_price}})
            if result.modified_count == 0:
                return error.error_non_exist_user_id(buyer_id)

            result = conn.new_order_col.delete_one({"order_id": order_id})
            if result.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

            result = conn.new_order_detail_col.delete_one({"order_id": order_id})
            if result.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

        except pymongo.errors.PyMongoError as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:

            row = self.conn.user_col.find_one({"user_id": user_id}, {"password": 1})
            if row is None:
                return error.error_authorization_fail()

            if row.get("password") != password:
                return error.error_authorization_fail()

            result = self.conn.user_col.update_one({"user_id": user_id}, {"$inc": {"balance": add_value}})
            if result.modified_count == 0:
                return error.error_non_exist_user_id(user_id)

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def book_search(self, store_id, book_id, book_title, book_tags, book_author):
        try:
            # if not self.store_id_exist(store_id):
            #     return error.error_non_exist_store_id(store_id)
            query_conditions = {}
            if store_id:
                query_conditions["store_id"] = store_id
            if book_id:
                query_conditions["book_id"] = book_id
            if book_title:
                query_conditions["book_title"] = book_title
            if book_tags:
                query_conditions["book_tags"] = book_tags
            if book_author:
                query_conditions["book_author"] = book_author

            result = self.conn.store_col.find(query_conditions, {})

            if result is None:
                return error.error_non_exist_book_id(book_id)
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"
