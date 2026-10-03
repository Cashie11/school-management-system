from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    return render(request, "core/home.html")


def privacy(request):
    return render(request, "core/privacy.html")


def health(request):
    """Liveness probe used by monitoring and deployment checks."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # noqa: BLE001
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})
