from django.http import JsonResponse

from core.validators.json_body import BadJsonError


class JsonBodyErrorMiddleware:
    """Turn an uncaught BadJsonError from any view into a JSON 400."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if isinstance(exception, BadJsonError):
            return JsonResponse({"error": str(exception)}, status=400)
        return None
