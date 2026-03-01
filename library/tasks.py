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


# Implement a Celery task that runs daily to check for overdue book loans and sends email notifications to members.
@shared_task
def check_overdue_loans ():
    #1. run daily
    from datetime import datetime
    with transaction.atomic():
        loans = Loan.objects.select_related("users", "members").select_for_update(skipped=True).filter(
            due_date__lt=datetime.now(),
            is_returned=False,
        )
        
        #loans
        active_loans = []
        for loan in loans:
            #check for idempotency
            if loan.member.user.email:
                active_loans.append(loan)
        
    for loan in active_loans:
        try:
            message = f"Hello {loan.member.user.username},\n\nYour book loan is overdue return it by the {loan.due_date}"
            send_mail(
                subject='Book Loaned Successfully',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[loan.member.email],
                fail_silently=False,
            ) 
            print("....")
        except Exception as err:
            print("....", err)
        
        