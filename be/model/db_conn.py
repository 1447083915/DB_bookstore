from be.model import store


class DBConn:
    def __init__(self):
        self.conn = store.get_db_conn()

    def user_id_exist(self, user_id):
        # cursor = self.conn.execute(
        #     "SELECT user_id FROM user WHERE user_id = ?;", (user_id,)
        # )
        # row = cursor.fetchone()
        # if row is None:
        #     return False
        # else:
        #     return True

        result = self.conn.user_col.find_one({"user_id": user_id})
        if result is None:
            return False
        else:
            return True

    def book_id_exist(self, store_id, book_id):
        # cursor = self.conn.execute(
        #     "SELECT book_id FROM store WHERE store_id = ? AND book_id = ?;",
        #     (store_id, book_id),
        # )
        # row = cursor.fetchone()
        # if row is None:
        #     return False
        # else:
        #     return True

        result = self.conn.store_col.find_one({"store_id": store_id, "book_id": book_id}, {"book_id": 1})
        if result is None:
            return False
        else:
            return True

    def store_id_exist(self, store_id):
        # cursor = self.conn.execute(
        #     "SELECT store_id FROM user_store WHERE store_id = ?;", (store_id,)
        # )
        # row = cursor.fetchone()
        # if row is None:
        #     return False
        # else:
        #     return True

        result = self.conn.user_store_col.find_one({"store_id": store_id})
        if result is None:
            return False
        else:
            return True
