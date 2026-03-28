from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_date

from accounts.models import AccountStatus, BankAccount
from dashboard.services import get_director_count_map, get_director_overview_data
from qr_payments.api import QRGenerateSerializer
from qr_payments.services import build_qr_payload, build_qr_png_base64, build_signed_qr_payload
from transactions.models import Transaction, Transfer, TransferStatus
from transactions.services import TransferError, approve_pending_transfer, block_pending_transfer, create_transfer_request
from users.models import User, UserRole
from webui.forms import EmailAuthenticationForm, QRForm, RegisterForm, TransferForm


def _build_chart(chart_id, title, subtitle, items):
    max_value = max((item["value"] for item in items), default=0)
    normalized_items = []
    for item in items:
        value = item["value"]
        width_percent = 0
        if max_value:
            width_percent = round((value / max_value) * 100, 1)
            if value and width_percent < 8:
                width_percent = 8
        normalized_items.append(
            {
                "label": item["label"],
                "value": value,
                "display_value": item["display_value"],
                "width_percent": width_percent,
            }
        )
    return {
        "id": chart_id,
        "title": title,
        "subtitle": subtitle,
        "items": normalized_items,
    }


def _build_director_dashboard_context():
    overview = get_director_overview_data()
    role_counts = get_director_count_map(model=User, group_field="role")
    transaction_type_counts = get_director_count_map(model=Transaction, group_field="type")
    account_status_counts = get_director_count_map(model=BankAccount, group_field="status")
    transfer_status_counts = get_director_count_map(model=Transfer, group_field="status")

    today = timezone.now().date()
    start_day = today - timedelta(days=6)
    fee_totals = {start_day + timedelta(days=offset): 0 for offset in range(7)}
    for transfer in Transfer.objects.filter(status=TransferStatus.COMPLETED, processed_at__date__gte=start_day):
        fee_totals[transfer.processed_at.date()] += float(transfer.fee_amount)

    director_charts = [
        _build_chart(
            "users-chart",
            "User role distribution",
            "How accounts are split across the platform.",
            [
                {"label": "Users", "value": role_counts.get(UserRole.USER, 0), "display_value": str(role_counts.get(UserRole.USER, 0))},
                {
                    "label": "Managers",
                    "value": role_counts.get(UserRole.MANAGER, 0),
                    "display_value": str(role_counts.get(UserRole.MANAGER, 0)),
                },
                {
                    "label": "Directors",
                    "value": role_counts.get(UserRole.DIRECTOR, 0),
                    "display_value": str(role_counts.get(UserRole.DIRECTOR, 0)),
                },
            ],
        ),
        _build_chart(
            "transactions-chart",
            "Transaction type activity",
            "Distribution across credits, debits, fees, and bonuses.",
            [
                {
                    "label": "Credits",
                    "value": transaction_type_counts.get("credit", 0),
                    "display_value": str(transaction_type_counts.get("credit", 0)),
                },
                {
                    "label": "Debits",
                    "value": transaction_type_counts.get("debit", 0),
                    "display_value": str(transaction_type_counts.get("debit", 0)),
                },
                {
                    "label": "Fees",
                    "value": transaction_type_counts.get("fee", 0),
                    "display_value": str(transaction_type_counts.get("fee", 0)),
                },
                {
                    "label": "Welcome bonuses",
                    "value": transaction_type_counts.get("welcome_bonus", 0),
                    "display_value": str(transaction_type_counts.get("welcome_bonus", 0)),
                },
            ],
        ),
        _build_chart(
            "earnings-chart",
            "Fee earnings over the last 7 days",
            "Completed transfer fees recognized as bank earnings.",
            [
                {
                    "label": day.strftime("%a"),
                    "value": fee_totals[day],
                    "display_value": f"EUR {fee_totals[day]:.2f}",
                }
                for day in fee_totals
            ],
        ),
        _build_chart(
            "blocked-accounts-chart",
            "Account status overview",
            "Active versus blocked customer accounts.",
            [
                {
                    "label": "Active",
                    "value": account_status_counts.get(AccountStatus.ACTIVE, 0),
                    "display_value": str(account_status_counts.get(AccountStatus.ACTIVE, 0)),
                },
                {
                    "label": "Blocked",
                    "value": account_status_counts.get(AccountStatus.BLOCKED, 0),
                    "display_value": str(account_status_counts.get(AccountStatus.BLOCKED, 0)),
                },
            ],
        ),
        _build_chart(
            "pending-transfers-chart",
            "Transfer pipeline status",
            "Current state of the transfer review workflow.",
            [
                {
                    "label": "Pending",
                    "value": transfer_status_counts.get(TransferStatus.PENDING, 0),
                    "display_value": str(transfer_status_counts.get(TransferStatus.PENDING, 0)),
                },
                {
                    "label": "Completed",
                    "value": transfer_status_counts.get(TransferStatus.COMPLETED, 0),
                    "display_value": str(transfer_status_counts.get(TransferStatus.COMPLETED, 0)),
                },
                {
                    "label": "Blocked",
                    "value": transfer_status_counts.get(TransferStatus.BLOCKED, 0),
                    "display_value": str(transfer_status_counts.get(TransferStatus.BLOCKED, 0)),
                },
                {
                    "label": "Failed",
                    "value": transfer_status_counts.get(TransferStatus.FAILED, 0),
                    "display_value": str(transfer_status_counts.get(TransferStatus.FAILED, 0)),
                },
            ],
        ),
    ]

    director_cards = [
        {"label": "Users", "value": overview["users_count"], "chart_id": "users-chart", "prefix": "", "suffix": ""},
        {"label": "Transactions", "value": overview["transactions_count"], "chart_id": "transactions-chart", "prefix": "", "suffix": ""},
        {"label": "Fee earnings", "value": overview["bank_earnings"], "chart_id": "earnings-chart", "prefix": "EUR ", "suffix": ""},
        {"label": "Blocked accounts", "value": overview["blocked_accounts"], "chart_id": "blocked-accounts-chart", "prefix": "", "suffix": ""},
        {"label": "Pending transfers", "value": overview["pending_transfers"], "chart_id": "pending-transfers-chart", "prefix": "", "suffix": ""},
    ]

    return {
        "overview": overview,
        "director_cards": director_cards,
        "director_charts": director_charts,
        "default_director_chart_id": director_charts[0]["id"],
    }


def role_required(*roles):
    def decorator(view_func):
        def wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                messages.error(request, "You do not have permission to access this page.")
                return redirect("dashboard")
            return view_func(request, *args, **kwargs)

        return login_required(wrapped)

    return decorator


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "webui/home.html")


def register_view(request):
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Your SimpleBank account was created successfully.")
        return redirect("dashboard")
    return render(request, "webui/register.html", {"form": form})


def login_view(request):
    form = EmailAuthenticationForm(request.POST or None, request=request)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        messages.success(request, "Welcome back.")
        return redirect("dashboard")
    return render(request, "webui/login.html", {"form": form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


@login_required
def dashboard(request):
    context = {"role": request.user.role}
    if request.user.role == UserRole.USER:
        context.update(
            {
                "account": request.user.bank_account,
                "recent_transactions": request.user.bank_account.transactions.select_related("related_account")[:8],
                "pending_transfers": request.user.bank_account.outgoing_transfers.filter(status=TransferStatus.PENDING).select_related("receiver_account")[:8],
            }
        )
    elif request.user.role == UserRole.MANAGER:
        context["users"] = User.objects.filter(role=UserRole.USER).select_related("bank_account").order_by("email")
        context["pending_transfers"] = Transfer.objects.filter(status=TransferStatus.PENDING).select_related(
            "sender_account", "receiver_account", "initiated_by"
        )[:20]
    elif request.user.role == UserRole.DIRECTOR:
        context.update(_build_director_dashboard_context())
    return render(request, "webui/dashboard.html", context)


@role_required(UserRole.USER)
def transfer_view(request):
    form = TransferForm(request.POST or None, user=request.user)
    account = request.user.bank_account
    estimated_fee = "5.00"
    if request.method == "POST" and form.is_valid():
        try:
            create_transfer_request(
                sender_account=account,
                receiver_account=form.destination_account,
                amount=form.cleaned_data["amount"],
                initiated_by=request.user,
                swift_code=form.cleaned_data.get("swift_code", ""),
                reference=form.cleaned_data.get("reference", ""),
            )
        except TransferError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Transfer request submitted for manager approval.")
            return redirect("dashboard")
    return render(
        request,
        "webui/transfer.html",
        {
            "form": form,
            "account": account,
            "estimated_fee": estimated_fee,
        },
    )


@role_required(UserRole.USER)
def report_view(request):
    transactions = request.user.bank_account.transactions.select_related("related_account")
    from_date = parse_date(request.GET.get("from", ""))
    to_date = parse_date(request.GET.get("to", ""))
    if from_date:
        transactions = transactions.filter(created_at__date__gte=from_date)
    if to_date:
        transactions = transactions.filter(created_at__date__lte=to_date)
    return render(
        request,
        "webui/report.html",
        {"transactions": transactions[:100], "from": request.GET.get("from", ""), "to": request.GET.get("to", "")},
    )


@role_required(UserRole.USER)
def qr_view(request):
    form = QRForm(request.POST or None)
    qr_result = None
    if request.method == "POST" and form.is_valid():
        serializer = QRGenerateSerializer(data=form.cleaned_data)
        serializer.is_valid(raise_exception=True)
        payload = build_qr_payload(
            account_number=request.user.bank_account.account_number,
            user_name=request.user.full_name,
            amount=serializer.validated_data["amount"],
            note=serializer.validated_data.get("note", ""),
        )
        qr_result = {
            "payload": payload,
            "signed_payload": build_signed_qr_payload(payload),
            "png_base64": build_qr_png_base64(payload),
        }
    return render(request, "webui/qr.html", {"form": form, "qr_result": qr_result})


@role_required(UserRole.MANAGER)
def manager_user_detail(request, user_id):
    bank_user = get_object_or_404(User.objects.select_related("bank_account"), pk=user_id, role=UserRole.USER)
    transactions = bank_user.bank_account.transactions.select_related("related_account")[:100]
    return render(request, "webui/manager_user_detail.html", {"bank_user": bank_user, "transactions": transactions})


@role_required(UserRole.MANAGER)
def manager_block_account(request, account_id):
    account = get_object_or_404(BankAccount, pk=account_id)
    if request.method == "POST":
        account.status = AccountStatus.BLOCKED
        account.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Account {account.account_number} has been blocked.")
    return redirect("manager-user-detail", user_id=account.user_id)


@role_required(UserRole.MANAGER)
def manager_approve_transfer(request, transfer_id):
    transfer = get_object_or_404(Transfer, pk=transfer_id)
    if request.method == "POST":
        try:
            approve_pending_transfer(transfer=transfer, reviewed_by=request.user)
        except TransferError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Transfer #{transfer.id} approved.")
    return redirect("dashboard")


@role_required(UserRole.MANAGER)
def manager_block_transfer(request, transfer_id):
    transfer = get_object_or_404(Transfer, pk=transfer_id)
    if request.method == "POST":
        try:
            block_pending_transfer(transfer=transfer, reviewed_by=request.user)
        except TransferError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Transfer #{transfer.id} blocked.")
    return redirect("dashboard")
