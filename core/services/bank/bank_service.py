from core.models import Bank

class BankService(object):
    @staticmethod
    def create_bank(data):
        bank = Bank.objects.create(
            name=data["name"],
            account_number=data.get("account_number", ""),
            card_id=data.get("card_id", ""),
            swift_code=data.get("swift_code", ""),
            customer_id=data.get("customer_id", ""),
            customer_name=data.get("customer_name", ""),
            is_active=data.get("is_active", True),
            order=data.get("order", 0),
        )
        return bank

    @staticmethod
    def update_bank(bank_id, data):
        from django.shortcuts import get_object_or_404
        bank = get_object_or_404(Bank, pk=bank_id)
        for field in [
            "name",
            "account_number",
            "card_id",
            "swift_code",
            "customer_id",
            "customer_name",
            "is_active",
            "order",
        ]:
            if field in data:
                setattr(bank, field, data[field])
        bank.save()
        return bank

    @staticmethod
    def delete_bank(bank_id):
        from django.shortcuts import get_object_or_404
        bank = get_object_or_404(Bank, pk=bank_id)
        bank.delete()
