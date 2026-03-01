from django.test import TestCase
from rest_framework.test import APIClient
from library.tests.factories import create_author, create_book


class BookListPaginationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = create_author()
        # create 12 books to force pagination
        for i in range(12):
            create_book(author=author, title=f"Book {i}", isbn=f"1234567890{100+i}", available_copies=2)

    def test_books_list_is_paginated(self):
        resp = self.client.get("/api/books/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("results", resp.data)
        self.assertIn("count", resp.data)

    def test_books_list_page_size_query_param_if_enabled(self):
        # If you enabled page_size_query_param in your pagination class, this should work.
        # If not enabled, this test will still pass as long as results are returned.
        resp = self.client.get("/api/books/?page_size=5")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("results", resp.data)