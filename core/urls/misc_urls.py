from django.urls import path
from .. import views

urlpatterns = [
    # ── Reminder Engine ──────────────────────────────────────────────────────
    path("api/reminders/", views.ReminderRuleListView.as_view()),
    path("api/reminders/<int:pk>/", views.ReminderRuleDetailView.as_view()),
    path("api/reminders/check/", views.ReminderCheckView.as_view()),
    path("api/reminders/log/", views.ReminderLogListView.as_view()),
    # ── Certificate Statuses ─────────────────────────────────────────────────
    path("api/cert-statuses/", views.CertificateStatusListView.as_view()),
    path("api/cert-statuses/<int:pk>/", views.CertificateStatusDetailView.as_view()),
    path("api/translations/", views.get_translations),
    path("api/translations/save/", views.save_translations),
    path("api/translations/scan/", views.scan_translations),
    path("api/scan-translations/", views.scan_translations),
    # ── Advanced Reports ─────────────────────────────────────────────────────
    path("api/reports/salary/", views.SalaryReportView.as_view()),
    path("api/reports/balance/", views.BalanceReportView.as_view()),
    path("api/reports/certificates/", views.CertificateReportView.as_view()),
    # ── Dashboard Summary ────────────────────────────────────────────────────
    path("api/dashboard/summary/", views.DashboardSummaryView.as_view()),
    path("api/goals/", views.GoalListView.as_view()),
    path("api/goals/<int:pk>/", views.GoalDetailView.as_view()),
    path(
        "api/documents/categories/",
        views.DocumentCategoriesView.as_view(),
    ),
    path(
        "api/documents/file/<int:document_id>/",
        views.DocumentFileView.as_view(),
    ),
    path(
        "api/documents/<str:parent_type>/<int:parent_id>/",
        views.DocumentListUploadView.as_view(),
    ),
]
