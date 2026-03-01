from datetime import timedelta
from django.test import TestCase, override_settings
from django.utils import timezone
from django.core import mail

from library.tests.factories import create_member, create_book, create_loan, make_overdue
from library.tasks import check_overdue_loans


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class OverdueNotificationTaskTests(TestCase):
    def test_task_sends_email_for_overdue_loans(self):
        member = create_member(username="overdue", email="overdue@test.com")
        book = create_book(isbn="6666666666666", available_copies=2)

        loan = create_loan(book=book, member=member)
        make_overdue(loan, days_overdue=1)

        result = check_overdue_loans()  # call directly (fine) OR check_overdue_loans.delay().get()

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Overdue", mail.outbox[0].subject)
        self.assertIn("overdue@test.com", mail.outbox[0].to)
        self.assertIn(str(loan.due_date), mail.outbox[0].body)

        self.assertIn("overdue_found", result)
        self.assertIn("emails_sent", result)

    def test_task_does_not_email_when_not_overdue(self):
        member = create_member(username="ok", email="ok@test.com")
        book = create_book(isbn="5555555555555", available_copies=2)

        # due today or in future should not count as overdue
        loan = create_loan(book=book, member=member, due_date=timezone.now().date())

        check_overdue_loans()

        self.assertEqual(len(mail.outbox), 0)

    def test_task_skips_members_without_email(self):
        member = create_member(username="noemail", email="")
        member.user.email = ""
        member.user.save(update_fields=["email"])

        book = create_book(isbn="4444444444444", available_copies=2)
        loan = create_loan(book=book, member=member)
        make_overdue(loan, days_overdue=1)

        check_overdue_loans()

        self.assertEqual(len(mail.outbox), 0)