import pytest
from unittest.mock import patch
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from django.urls import reverse

from library.models import Author, Book, Member, Loan
from library.tasks import send_loan_notification

@pytest.fixture
def user_member(db):
    u = User.objects.create_user(username="u1", password="x", email="u1@test.com")
    m = Member.objects.create(user=u)
    return u, m

@pytest.fixture
def book(db):
    a = Author.objects.create(first_name="A", last_name="B")
    return Book.objects.create(
        title="T",
        author=a,
        isbn="1234567890123",
        genre="fiction",
        available_copies=1,
    )

@pytest.mark.django_db
def test_loan_success(user_member, book):
    u, m = user_member
    c = APIClient()
    c.force_authenticate(user=u)

    url = reverse("book-loan", args=[book.id])
    r = c.post(url, {"member_id": m.id}, format="json")

    assert r.status_code == 201
    book.refresh_from_db()
    assert book.available_copies == 0
    assert Loan.objects.filter(book=book, member=m, is_returned=False).count() == 1

@pytest.mark.django_db
def test_loan_conflict_no_copies(user_member, book):
    u, m = user_member
    book.available_copies = 0
    book.save()

    c = APIClient()
    c.force_authenticate(user=u)

    url = reverse("book-loan", args=[book.id])
    r = c.post(url, {"member_id": m.id}, format="json")

    assert r.status_code == 409

@pytest.mark.django_db
def test_double_active_loan_conflict(user_member, book):
    u, m = user_member
    Loan.objects.create(book=book, member=m, is_returned=False)

    c = APIClient()
    c.force_authenticate(user=u)

    url = reverse("book-loan", args=[book.id])
    r = c.post(url, {"member_id": m.id}, format="json")

    assert r.status_code == 409

@pytest.mark.django_db
def test_return_success(user_member, book):
    u, m = user_member
    loan = Loan.objects.create(book=book, member=m, is_returned=False)
    book.available_copies = 0
    book.save()

    c = APIClient()
    c.force_authenticate(user=u)

    url = reverse("book-return-book", args=[book.id])
    r = c.post(url, {"member_id": m.id}, format="json")

    assert r.status_code == 200
    book.refresh_from_db()
    assert book.available_copies == 1
    loan.refresh_from_db()
    assert loan.is_returned is True

@pytest.mark.django_db
def test_idempotency_key_same_request_returns_same_loan(user_member, book):
    u, m = user_member
    c = APIClient()
    c.force_authenticate(user=u)

    url = reverse("book-loan", args=[book.id])
    headers = {"HTTP_IDEMPOTENCY_KEY": "k1"}

    r1 = c.post(url, {"member_id": m.id}, format="json", **headers)
    r2 = c.post(url, {"member_id": m.id}, format="json", **headers)

    assert r1.status_code == 201
    assert r2.status_code == 201
    assert r1.data["loan_id"] == r2.data["loan_id"]

@pytest.mark.django_db
@patch("library.tasks.send_mail")
def test_task_idempotent_sent_only_once(mock_send_mail, user_member, book):
    u, m = user_member
    loan = Loan.objects.create(book=book, member=m, is_returned=False, due_date="2030-01-01")

    send_loan_notification(loan.id)
    loan.refresh_from_db()
    assert loan.notification_status == "sent"
    assert mock_send_mail.call_count == 1

    # run again -> should not re-send
    send_loan_notification(loan.id)
    assert mock_send_mail.call_count == 1

@pytest.mark.django_db
@patch("library.tasks.send_mail", side_effect=Exception("SMTP down"))
def test_task_records_failure_and_raises_for_retry(mock_send_mail, user_member, book):
    u, m = user_member
    loan = Loan.objects.create(book=book, member=m, is_returned=False, due_date="2030-01-01")

    with pytest.raises(Exception):
        send_loan_notification(loan.id)

    loan.refresh_from_db()
    assert loan.notification_status == "failed"
    assert "SMTP down" in loan.last_notification_error
    assert loan.notification_attempts >= 1