import requests
from urllib.parse import urljoin
from fe.access import book
from fe.access.auth import Auth


class Booksearch:
    def __init__(self, url_prefix):
        self.url_prefix = urljoin(url_prefix, "booksearch/")

    def book_search(self, store_id: str, book_info: book.Book):
        json = {
            "store_id": store_id,
            "book_info": book_info.__dict__
        }
        url = urljoin(self.url_prefix, "search_book")
        r = requests.post(url, json=json)
        return r.status_code, r.json().get("token")
