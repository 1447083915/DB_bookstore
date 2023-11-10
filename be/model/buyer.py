import sqlite3 as sqlite
import uuid
import json
import logging
from be.model import db_conn
from be.model import error
import pymongo.errors
import time


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

            # 获取当前系统时间并计算截止时间
            current_time = int(time.time())
            payment_ddl = current_time + 15
            # 插入该order基础信息与付款截止日期
            self.conn.new_order_col.insert_one({
                "order_id": uid, "store_id": store_id, "user_id": user_id,
                "payment_status": "no_pay", "payment_ddl": payment_ddl
            })
            order_id = uid

        except BaseException as e:
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        conn = self.conn
        try:

            # 查看对应order的支付状态
            order = conn.new_order_col.find_one({"order_id": order_id})
            if order['payment_status'] != "no_pay":
                return

            # 按照order_id查找user_id,store_id,buyer_id并存储
            row = conn.new_order_col.find_one({"order_id": order_id}, {"order_id": 1, "user_id": 1, "store_id": 1})
            if row is None:
                return error.error_invalid_order_id(order_id)

            order_id = row["order_id"]
            buyer_id = row["user_id"]
            store_id = row["store_id"]

            if buyer_id != user_id:
                return error.error_authorization_fail()

            # 基于buyer_id查找balance(用户余额)与password,并判断password是否正确
            result = conn.user_col.find_one({"user_id": buyer_id}, {"balance": 1, "password": 1})
            if result is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = result["balance"]
            if password != result["password"]:
                return error.error_authorization_fail()

            # 通过store_id查找卖家
            result = conn.user_store_col.find_one({"store_id": store_id}, {"store_id": 1, "user_id": 1})
            if result is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = result["user_id"]

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            # 通过order_id查找购买书籍并计算价格总和
            result = conn.new_order_detail_col.find({"order_id": order_id}, {"book_id": 1, "count": 1, "price": 1})
            total_price = 0
            for row in result:
                count = row["count"]
                price = row["price"]
                total_price = total_price + price * count

            # 如果用户余额不够付钱,则error
            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            # 买家用户减去余额
            result = conn.user_col.update_one({"user_id": user_id, "balance": {"$gte": total_price}},
                                              {"$inc": {"balance": -total_price}})

            if result.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            # 卖家用户增加余额
            result = conn.user_col.update_one({"user_id": seller_id}, {"$inc": {"balance": total_price}})

            if result.modified_count == 0:
                return error.error_non_exist_user_id(seller_id)

            # 支付完毕修改订单状态
            result = conn.new_order_col.update_one({"order_id": order_id}, {"$set": {"payment_status": "paid"}})  # 已支付
            if result.modified_count == 0:
                return error.error_non_order_pay(order_id)

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

            # print(query_conditions)
            result = self.conn.store_col.find(query_conditions, {}).limit(10)

            if not any(result):
                return error.error_non_exist_book_id(book_id)
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    # 删除订单操作
    def delete_order(self, user_id, order_id) -> (int, str):
        try:
            # 获取订单信息
            order = self.conn.new_order_col.find_one({"order_id": order_id}, {})
            # 判断有无订单删除
            if not order:
                return error.error_non_order_delete(user_id)
            payment_status = order["payment_status"]
            # 如果有订单
            if payment_status == "paid":
                # 按照order_id查找store_id并存储
                row = self.conn.new_order_col.find_one({"order_id": order_id},
                                                       {"store_id": 1})
                if row is None:
                    return error.error_invalid_order_id(order_id)
                store_id = row["store_id"]

                # 通过store_id查找卖家
                seller_id = self.conn.user_store_col.find_one({"store_id": store_id}, {"user_id": 1})
                if seller_id is None:
                    return error.error_non_exist_store_id(store_id)

                if not self.user_id_exist(seller_id):
                    return error.error_non_exist_user_id(seller_id)
                # 如果支付状态是"paid"
                # 通过order_id查找购买书籍并计算价格总和
                result = self.conn.new_order_detail_col.find({"order_id": order_id},
                                                             {"count": 1, "price": 1})
                total_price = 0
                for row in result:
                    count = row["count"]
                    price = row["price"]
                    total_price = total_price + price * count

                # 用户余额返回
                self.conn.user_col.update_one({"user_id": user_id},
                                              {"$inc": {"balance": total_price}})

                # 卖家用户减少余额
                result = self.conn.user_col.update_one({"user_id": seller_id}, {"$inc": {"balance": -total_price}})
                if result.modified_count == 0:
                    return error.error_non_exist_user_id(seller_id)

                # 删除状态为"no_pay"与"paid"的订单
                self.conn.new_order_col.delete_many(
                    {"order_id": order_id})
                self.conn.new_order_detail_col.delete_many(
                    {"order_id": order_id})

            elif payment_status == "no_pay":
                # 还未付款直接删除,无需退钱
                # 删除状态为"no_pay"与"paid"的订单
                self.conn.new_order_col.delete_many(
                    {"order_id": order_id})
                self.conn.new_order_detail_col.delete_many(
                    {"order_id": order_id})
            else:
                return error.error_unable_to_delete(order_id)

        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def search_order(self, user_id) -> (int, str):
        try:
            # 搜索前遍历订单删除超时订单
            current_time = int(time.time())
            payment_overtime_order_ids = [order['order_id'] for order in
                                          self.conn.new_order_col.find({"payment_ddl": {"$lt": current_time},
                                                                        "payment_status": "no_pay"},
                                                                       {"order_id": 1})]
            self.conn.new_order_col.delete_many({"order_id": {"$in": payment_overtime_order_ids}})
            self.conn.new_order_detail_col.delete_many({"order_id": {"$in": payment_overtime_order_ids}})

            # 将用户作为买家进行搜索
            buyer_order_ids = [order['order_id'] for order in
                               self.conn.new_order_col.find({"user_id": user_id}, {"order_id": 1})]

            if not buyer_order_ids:
                return error.empty_order_search(user_id)

            self.conn.new_order_col.find({"order_id": {"$in": buyer_order_ids}}, {})

        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"

    def receive(self, user_id: str, store_id: str, order_id: str) -> (int, str):
        try:
            result = self.conn.new_order_col.find_one({"order_id": order_id})
            if result is None:
                return 503, "订单不存在"

            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)

            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)

            status = result['payment_status']

            if status == "no_pay":
                return 521, {"no_pay"}
            elif status == "paid":
                return 522, {"no_shipped"}
            elif status == "received":
                return 523, {"received"}

            self.conn.new_order_col.update_one({"order_id": order_id}, {"$set": {"payment_status": 'received'}})  # 已收货

        except BaseException as e:
            return 532, "{}".format(str(e))
        return 200, "ok"
