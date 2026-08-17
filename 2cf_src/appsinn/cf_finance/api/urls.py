# cf-dev/cf_src/appsinn/cf_finance/api/urls.py

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from cf_finance.api import views

app_name = "cf_finance_api"

router = DefaultRouter()
router.register(r"funds", views.FundViewSet, basename="funds")
router.register(r"transactions", views.TransactionViewSet, basename="transactions")
router.register(r"budgets", views.BudgetViewSet, basename="budgets")

urlpatterns = [
    path("", include(router.urls)),
]
