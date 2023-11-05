from be.model import error
from be.model import db_conn
import pymongo


class Seller(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def add_book(self, user_id: str, store_id: str, book_id: str, book_json_str: str, stock_level: int):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)


            data = {
                "store_id": store_id,
                "book_id": book_id,
                "book_info": book_json_str,
                "stock_level": stock_level
            }
            # 插入数据到MongoDB
            self.conn.store_col.insert_one(data)

        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"  # 成功添加书籍，返回状态码200和消息

    def add_stock_level(
            self, user_id: str, store_id: str, book_id: str, add_stock_level: int
    ):
        try:

            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            # self.conn.execute(
            #     "UPDATE store SET stock_level = stock_level + ? "
            #     "WHERE store_id = ? AND book_id = ?",
            #     (add_stock_level, store_id, book_id),
            # )

            filter_query = {"store_id": store_id, "book_id": book_id}
            update_query = {"$inc": {"stock_level": add_stock_level}}

            self.conn.store_col.update_one(filter_query, update_query)
        except BaseException as e:
            return 500, "{}".format(str(e))

        return 200, "ok"

    def create_store(self, user_id: str, store_id: str) -> (int, str):
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)

            # 检查是否已存在相同的store_id
            # existing_store = self.conn.user_store_col.find_one({"store_id": store_id})
            # if existing_store:
            #     return 532, "店铺已经存在"

            data = {
                "store_id": store_id,
                "user_id": user_id
            }

            self.conn.user_store_col.insert_one(data)

        except BaseException as e:
            return 500, "{}".format(str(e))
        return 200, "ok"
