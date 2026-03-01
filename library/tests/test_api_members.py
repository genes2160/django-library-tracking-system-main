from django.test import TestCase
from rest_framework.test import APIClient

from library.tests.factories import create_member, create_book, create_loan


class TopActiveMembersTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_top_active_returns_top_5_with_counts(self):
        book = create_book(isbn="7777777777777", available_copies=50)

        # Create 6 members with varying active loan counts
        members = [create_member(username=f"m{i}", email=f"m{i}@t.com") for i in range(6)]

        # active loans: 0..5
        for i, m in enumerate(members):
            for _ in range(i):
                create_loan(book=book, member=m, is_returned=False)

        resp = self.client.get("/api/members/top-active/")
        self.assertEqual(resp.status_code, 200)

        data = resp.json()
        self.assertLessEqual(len(data), 5)

        # first should have highest count (5)
        self.assertEqual(data[0]["active_loans"], 5)
        self.assertIn("username", data[0])
        self.assertIn("email", data[0])

    def test_top_active_empty_when_no_members_or_loans(self):
        resp = self.client.get("/api/members/top-active/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), [])