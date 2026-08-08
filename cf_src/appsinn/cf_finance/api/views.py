# cf-dev/cf_src/appsinn/cf_finance/api/views.py

"""DRF viewsets for cf_finance.

Querysets are tenant-scoped via ``for_user`` when available so list
endpoints stay efficient under multi-org / multi-million-user loads.
"""

from cf_finance import settings as app_settings
from cf_finance.models import (
    Budget,
    Fund,
    Transaction,
)
from cf_finance.api.serializers import (
    FundSerializer,
    TransactionSerializer,
    BudgetSerializer,
)
from cf_utils.api.viewsets import CFModelViewSet, CFReadOnlyModelViewSet

class FundViewSet(CFModelViewSet):
    """API for Fund. """
    queryset = Fund.objects.all()
    serializer_class = FundSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_FINANCE_API_ENABLED", True):
            return Fund.objects.none()
        return super().get_queryset()

class TransactionViewSet(CFModelViewSet):
    """API for Transaction. """
    queryset = Transaction.objects.all()
    serializer_class = TransactionSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_FINANCE_API_ENABLED", True):
            return Transaction.objects.none()
        return super().get_queryset()

class BudgetViewSet(CFModelViewSet):
    """API for Budget. """
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer
    tenant_scoped = True
    select_related_fields = ('branch',)

    def get_queryset(self):
        if not getattr(app_settings, "CF_FINANCE_API_ENABLED", True):
            return Budget.objects.none()
        return super().get_queryset()

