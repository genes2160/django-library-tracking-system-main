from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action

from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from datetime import timedelta

from .models import Author, Book, Member, Loan
from .serializers import (
    AuthorSerializer,
    BookSerializer,
    MemberSerializer,
    LoanSerializer,
)
from .tasks import send_loan_notification


# ----------------------------
# Author ViewSet
# ----------------------------
class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


# ----------------------------
# Book ViewSet
# ----------------------------
class BookViewSet(viewsets.ModelViewSet):
    # Optimized to prevent N+1 when accessing author
    queryset = Book.objects.select_related("author").all()
    serializer_class = BookSerializer

    @action(detail=True, methods=["post"])
    def loan(self, request, pk=None):
        book = self.get_object()

        if book.available_copies < 1:
            return Response(
                {"error": "No available copies."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        member_id = request.data.get("member_id")
        if not member_id:
            return Response(
                {"error": "member_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response(
                {"error": "Member does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            loan = Loan.objects.create(book=book, member=member)
            book.available_copies -= 1
            book.save(update_fields=["available_copies"])

        # Async notification
        send_loan_notification.delay(loan.id)

        return Response(
            {"status": "Book loaned successfully."},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get("member_id")

        try:
            loan = Loan.objects.get(
                book=book,
                member__id=member_id,
                is_returned=False,
            )
        except Loan.DoesNotExist:
            return Response(
                {"error": "Active loan does not exist."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            loan.is_returned = True
            loan.return_date = timezone.now().date()
            loan.save(update_fields=["is_returned", "return_date"])

            book.available_copies += 1
            book.save(update_fields=["available_copies"])

        return Response(
            {"status": "Book returned successfully."},
            status=status.HTTP_200_OK,
        )


# ----------------------------
# Loan ViewSet
# ----------------------------
class LoanViewSet(viewsets.ModelViewSet):
    # Optimized for related access
    queryset = Loan.objects.select_related(
        "book",
        "book__author",
        "member",
        "member__user",
    ).all()
    serializer_class = LoanSerializer

    @action(detail=True, methods=["post"])
    def extend_due_date(self, request, pk=None):
        loan = self.get_object()

        # Cannot extend returned loan
        if loan.is_returned:
            return Response(
                {"error": "Cannot extend a returned loan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        today = timezone.now().date()

        # Cannot extend overdue loan
        if loan.due_date < today:
            return Response(
                {"error": "Cannot extend an overdue loan."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        additional_days = request.data.get("additional_days")

        try:
            additional_days = int(additional_days)
        except (TypeError, ValueError):
            return Response(
                {"error": "additional_days must be a positive integer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if additional_days <= 0:
            return Response(
                {"error": "additional_days must be greater than zero."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # Lock row for safe concurrent updates
            loan = Loan.objects.select_for_update().get(pk=loan.pk)
            loan.due_date = loan.due_date + timedelta(days=additional_days)
            loan.save(update_fields=["due_date"])

        return Response(
            LoanSerializer(loan).data,
            status=status.HTTP_200_OK,
        )


# ----------------------------
# Member ViewSet
# ----------------------------
class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.select_related("user").all()
    serializer_class = MemberSerializer

    @action(detail=False, methods=["get"], url_path="top-active")
    def top_active(self, request):
        members = (
            Member.objects
            .select_related("user")
            .annotate(
                active_loans=Count(
                    "loans",  # matches related_name in model
                    filter=Q(loans__is_returned=False),
                )
            )
            .order_by("-active_loans", "id")[:5]
        )

        data = [
            {
                "id": m.id,
                "username": m.user.username,
                "email": m.user.email,
                "active_loans": m.active_loans,
            }
            for m in members
        ]

        return Response(data, status=status.HTTP_200_OK)