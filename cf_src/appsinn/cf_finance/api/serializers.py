# cf-dev/cf_src/appsinn/cf_finance/api/serializers.py

"""DRF serializers for cf_finance (scale-oriented field sets)."""

from rest_framework import serializers

from cf_finance.models import (
    Budget,
    Fund,
    Transaction,
)

class FundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fund
        fields = ("id", "name", "branch")
        read_only_fields = ("id",)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = (
            "id",
            "branch",
            "financial_period",
            "fund",
            "transaction_type",
            "category",
            "amount",
            "reference_code",
        )
        read_only_fields = ("id", "reference_code")


class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = (
            "id",
            "branch",
            "financial_period",
            "department",
            "allocated_amount",
        )
        read_only_fields = ("id",)

