# pyright: reportMissingTypeStubs=false, reportPrivateUsage=false, reportUnknownParameterType=false, reportUnknownArgumentType=false, reportUnknownLambdaType=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportMissingParameterType=false, reportIncompatibleMethodOverride=false, reportOptionalMemberAccess=false

from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import get_object_or_404
from core.models import (
    FixedAsset,
    AssetPhoto,

)
from django.http import HttpResponse


@method_decorator(csrf_exempt, name="dispatch")
class FixedAssetPhotoView(View):

    def post(self, request, pk):

        asset = get_object_or_404(FixedAsset, pk=pk)

        files = request.FILES.getlist("photos")

        if not files:
            return JsonResponse(
                {"error": "No photos uploaded"},
                status=400,
            )

        uploaded = []

        for file in files:

            photo = AssetPhoto.objects.create(
                asset=asset,
                image_data=file.read(),
                filename=file.name,
                mime_type=file.content_type,
            )

            uploaded.append(photo.to_dict())

        return JsonResponse(uploaded, safe=False)

    def delete(self, request, pk, photo_id):

        photo = get_object_or_404(
            AssetPhoto,
            pk=photo_id,
            asset_id=pk,
        )

        photo.delete()

        return JsonResponse({"deleted": True})


class AssetPhotoView(View):

    def get(self, request, photo_id):

        photo = get_object_or_404(
            AssetPhoto,
            pk=photo_id,
        )

        return HttpResponse(
            photo.image_data,
            content_type=photo.mime_type,
        )


