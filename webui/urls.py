from django.urls import path

from webui import views

urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("app/", views.dashboard, name="dashboard"),
    path("app/transfer/", views.transfer_view, name="transfer"),
    path("app/report/", views.report_view, name="report"),
    path("app/qr/", views.qr_view, name="qr"),
    path("app/manager/users/<int:user_id>/", views.manager_user_detail, name="manager-user-detail"),
    path("app/manager/accounts/<int:account_id>/block/", views.manager_block_account, name="manager-block-account"),
    path("app/manager/transfers/<int:transfer_id>/approve/", views.manager_approve_transfer, name="manager-approve-transfer"),
    path("app/manager/transfers/<int:transfer_id>/block/", views.manager_block_transfer, name="manager-block-transfer"),
]
