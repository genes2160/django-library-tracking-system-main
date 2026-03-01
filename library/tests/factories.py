from datetime import timedelta
from django.contrib.auth.models import User
from django.utils import timezone

from library.models import Author, Book, Member, Loan


def create_user(username="user", email="user@test.com"):
    return User.objects.create_user(username=username, email=email, password="pass1234")


def create_member(username="member", email="member@test.com"):
    user = create_user(username=username, email=email)
    return Member.objects.create(user=user)


def create_author(first_name="Test", last_name="Author"):
    return Author.objects.create(first_name=first_name, last_name=last_name, biography="bio")


def create_book(author=None, title="Test Book", isbn="1234567890123", genre="fiction", available_copies=3):
    author = author or create_author()
    return Book.objects.create(
        title=title,
        author=author,
        isbn=isbn,
        genre=genre,
        available_copies=available_copies,
    )


def create_loan(book=None, member=None, due_date=None, is_returned=False):
    book = book or create_book()
    member = member or create_member()
    loan = Loan.objects.create(book=book, member=member, is_returned=is_returned)

    if due_date is not None:
        loan.due_date = due_date
        loan.save(update_fields=["due_date"])

    return loan


def make_overdue(loan: Loan, days_overdue=1):
    loan.due_date = timezone.now().date() - timedelta(days=days_overdue)
    loan.save(update_fields=["due_date"])
    return loan