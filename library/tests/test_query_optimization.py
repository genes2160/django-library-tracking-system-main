from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.db import connection
from rest_framework.test import APIClient

from library.tests.factories import create_author, create_book


class QueryOptimizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        author = create_author()
        for i in range(10):
            create_book(author=author, title=f"QB{i}", isbn=f"3333333333{100+i}", available_copies=1)

    def test_books_list_does_not_n_plus_one_on_author(self):
        # Expect a small number of queries, not 1 + N.
        with CaptureQueriesContext(connection) as ctx:
            resp = self.client.get("/api/books/")
            self.assertEqual(resp.status_code, 200)

        # This number may vary depending on pagination/count queries.
        # Typically: 2 queries (count + results) is common with pagination.
        self.assertLessEqual(len(ctx.captured_queries), 4)