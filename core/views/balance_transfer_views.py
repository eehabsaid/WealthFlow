import json
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from django.db import transaction
from core.models import BalanceTransfer

@method_decorator(csrf_exempt, name="dispatch")
class BalanceTransferListView(View):
    def get(self, request):
        transfers = BalanceTransfer.objects.select_related(
            'from_bank', 'to_bank', 'currency'
        ).all()
        return JsonResponse({"transfers": [t.to_dict() for t in transfers]})

    def post(self, request):
        try:
            data = json.loads(request.body)
            transfer_date = data["transfer_date"]
            transfer_type = data["transfer_type"]
            from_bank_id = data.get("from_bank_id")
            to_bank_id = data.get("to_bank_id")
            currency_id = data["currency_id"]
            amount = float(data.get("amount", 0))
            fee = float(data.get("fee", 0))
            notes = data.get("notes", "")

            with transaction.atomic():
                transfer = BalanceTransfer.objects.create(
                    transfer_date=transfer_date,
                    transfer_type=transfer_type,
                    from_bank_id=from_bank_id if transfer_type in [BalanceTransfer.TransferType.BANK_TO_BANK, BalanceTransfer.TransferType.BANK_TO_CASH] else None,
                    to_bank_id=to_bank_id if transfer_type in [BalanceTransfer.TransferType.BANK_TO_BANK, BalanceTransfer.TransferType.CASH_TO_BANK] else None,
                    currency_id=currency_id,
                    amount=amount,
                    fee=fee,
                    notes=notes
                )
                transfer.apply_transfer()
                
            return JsonResponse(transfer.to_dict(), status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

@method_decorator(csrf_exempt, name="dispatch")
class BalanceTransferDetailView(View):
    def put(self, request, pk):
        try:
            transfer = get_object_or_404(BalanceTransfer, pk=pk)
            data = json.loads(request.body)

            with transaction.atomic():
                # Reverse the old transfer
                transfer.reverse_transfer()

                # Update fields
                if "transfer_date" in data:
                    transfer.transfer_date = data["transfer_date"]
                if "transfer_type" in data:
                    transfer.transfer_type = data["transfer_type"]
                    # Reset irrelevant bank fields based on new type
                    if transfer.transfer_type == BalanceTransfer.TransferType.BANK_TO_CASH:
                        transfer.to_bank_id = None
                    elif transfer.transfer_type == BalanceTransfer.TransferType.CASH_TO_BANK:
                        transfer.from_bank_id = None
                        
                if "from_bank_id" in data:
                    transfer.from_bank_id = data["from_bank_id"] if data["from_bank_id"] else None
                if "to_bank_id" in data:
                    transfer.to_bank_id = data["to_bank_id"] if data["to_bank_id"] else None
                if "currency_id" in data:
                    transfer.currency_id = data["currency_id"]
                if "amount" in data:
                    transfer.amount = float(data["amount"])
                if "fee" in data:
                    transfer.fee = float(data["fee"])
                if "notes" in data:
                    transfer.notes = data["notes"]

                transfer.save()
                
                # Apply the new transfer
                transfer.apply_transfer()

            return JsonResponse(transfer.to_dict())
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)

    def delete(self, request, pk):
        try:
            transfer = get_object_or_404(BalanceTransfer, pk=pk)
            with transaction.atomic():
                transfer.reverse_transfer()
                transfer.delete()
            return JsonResponse({"deleted": pk})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
