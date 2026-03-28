from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date

from accounts.models import AccountStatus, BankAccount
from qr_payments.api import QRGenerateSerializer
from transactions.models import Transaction, Transfer, TransferStatus
from transactions.services import TransferError, perform_transfer
from users.models import User, UserRole
from webui.forms import EmailAuthenticationForm, QRForm, RegisterForm, TransferForm


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
                "fee_earnings": Transfer.objects.filter(status=TransferStatus.COMPLETED).aggregate(total=Sum("fee_amount"))["total"] or 0,
            }
        )
    elif request.user.role == UserRole.MANAGER:
        context["users"] = User.objects.filter(role=UserRole.USER).select_related("bank_account").order_by("email")
    elif request.user.role == UserRole.DIRECTOR:
        context["overview"] = {
            "users_count": User.objects.filter(role=UserRole.USER).count(),
            "transactions_count": Transaction.objects.count(),
            "bank_earnings": Transfer.objects.filter(status=TransferStatus.COMPLETED).aggregate(total=Sum("fee_amount"))["total"] or 0,
            "blocked_accounts": BankAccount.objects.filter(status=AccountStatus.BLOCKED).count(),
        }
    return render(request, "webui/dashboard.html", context)


@role_required(UserRole.USER)
def transfer_view(request):
    form = TransferForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        destination = get_object_or_404(BankAccount, account_number=form.cleaned_data["destination_account_number"])
        try:
            perform_transfer(
                sender_account=request.user.bank_account,
                receiver_account=destination,
                amount=form.cleaned_data["amount"],
                initiated_by=request.user,
                swift_code=form.cleaned_data.get("swift_code", ""),
                reference=form.cleaned_data.get("reference", ""),
            )
        except TransferError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Transfer completed successfully.")
            return redirect("dashboard")
    return render(request, "webui/transfer.html", {"form": form})


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
        qr_result = {
            "payload": {
                "account_number": request.user.bank_account.account_number,
                "user_name": request.user.full_name,
                "amount": str(serializer.validated_data["amount"]),
                "note": serializer.validated_data.get("note", ""),
            }
        }
        import base64
        from io import BytesIO
        import qrcode

        img = qrcode.make(qr_result["payload"])
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        qr_result["png_base64"] = base64.b64encode(buffer.getvalue()).decode("utf-8")
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
