from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from library.tests.factories import create_author, create_book, create_member, create_loan, make_overdue


class LoanExtendDueDateTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.member = create_member()
        self.author = create_author()
        self.book = create_book(author=self.author, isbn="9999999999999", available_copies=2)

    def test_extend_due_date_success(self):
        loan = create_loan(book=self.book, member=self.member)
        old_due = loan.due_date

        resp = self.client.post(f"/api/loans/{loan.id}/extend_due_date/", {"additional_days": 7}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], loan.id)
        self.assertEqual(resp.data["due_date"], (old_due + timedelta(days=7)).isoformat())

    def test_extend_due_date_rejects_overdue(self):
        loan = create_loan(book=self.book, member=self.member)
        make_overdue(loan, days_overdue=2)

        resp = self.client.post(f"/api/loans/{loan.id}/extend_due_date/", {"additional_days": 7}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.data)

    def test_extend_due_date_rejects_non_positive(self):
        loan = create_loan(book=self.book, member=self.member)

        resp = self.client.post(f"/api/loans/{loan.id}/extend_due_date/", {"additional_days": 0}, format="json")
        self.assertEqual(resp.status_code, 400)

        resp = self.client.post(f"/api/loans/{loan.id}/extend_due_date/", {"additional_days": -5}, format="json")
        self.assertEqual(resp.status_code, 400)

    def test_extend_due_date_rejects_non_integer(self):
        loan = create_loan(book=self.book, member=self.member)

        resp = self.client.post(f"/api/loans/{loan.id}/extend_due_date/", {"additional_days": "abc"}, format="json")
        self.assertEqual(resp.status_code, 400)


class BookLoanAndReturnTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.member = create_member()
        self.author = create_author()
        self.book = create_book(author=self.author, isbn="8888888888888", available_copies=1)

    def test_book_loan_decrements_available_copies(self):
        resp = self.client.post(f"/api/books/{self.book.id}/loan/", {"member_id": self.member.id}, format="json")
        self.assertEqual(resp.status_code, 201)

        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 0)

    def test_book_loan_fails_when_no_copies(self):
        self.book.available_copies = 0
        self.book.save(update_fields=["available_copies"])

        resp = self.client.post(f"/api/books/{self.book.id}/loan/", {"member_id": self.member.id}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.data)

    def test_return_book_increments_available_copies(self):
        # loan once
        resp = self.client.post(f"/api/books/{self.book.id}/loan/", {"member_id": self.member.id}, format="json")
        self.assertEqual(resp.status_code, 201)

        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 0)

        # return
        resp = self.client.post(f"/api/books/{self.book.id}/return_book/", {"member_id": self.member.id}, format="json")
        self.assertEqual(resp.status_code, 200)

        self.book.refresh_from_db()
        self.assertEqual(self.book.available_copies, 1)