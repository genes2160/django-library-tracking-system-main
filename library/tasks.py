from django.utils import timezone

from celery import shared_task
from .models import Loan, Member
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction

@shared_task
def send_loan_notification(loan_id):
    try:
        loan = Loan.objects.get(id=loan_id)
        member_email = loan.member.user.email
        book_title = loan.book.title
        send_mail(
            subject='Book Loaned Successfully',
            message=f'Hello {loan.member.user.username},\n\nYou have successfully loaned "{book_title}".\nPlease return it by the due date.',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False,
        )
    except Loan.DoesNotExist:
        pass

@shared_task
def check_overdue_loans():
    today = timezone.now().date()

    overdue_found = 0
    emails_sent = 0

    with transaction.atomic():
        loans = (
            Loan.objects
            .select_related("book", "member", "member__user")
            .select_for_update(skip_locked=True)
            .filter(
                due_date__lt=today,
                is_returned=False,
            )
        )

        overdue_found = loans.count()

        for loan in loans:
            email = loan.member.user.email
            if email:
                try:
                    message = (
                        f"Hello {loan.member.user.username},\n\n"
                        f"Your loan for '{loan.book.title}' "
                        f"was due on {loan.due_date}. "
                        f"Please return it as soon as possible."
                    )

                    send_mail(
                        subject="Overdue Book Notification",
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )

                    emails_sent += 1

                except Exception as err:
                    print("Email error:", err)

    return {
        "overdue_found": overdue_found,
        "emails_sent": emails_sent,
    }