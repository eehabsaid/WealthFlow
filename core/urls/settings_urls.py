from django.urls import path
from .. import views
from ..views import ExportExcelWorkbookView

urlpatterns = [
    # Reports
    path("api/reports/generate/", views.GenerateReportView.as_view()),
    path("api/settings/", views.SettingsView.as_view()),
    path("api/settings/email-templates/", views.EmailTemplateListView.as_view()),
    path("api/settings/email-templates/<int:pk>/", views.EmailTemplateDetailView.as_view()),
    path("api/settings/email-test/", views.EmailSettingsTestView.as_view()),
    path("api/settings/ai/", views.AISettingsView.as_view()),
    path("api/settings/ai/providers/", views.AIProviderListView.as_view()),
    path("api/settings/ai/test-connection/", views.AIConnectionTestView.as_view()),
    path("api/settings/gold-types/", views.GoldTypeSettingsListView.as_view()),
    path("api/settings/gold-types/<int:pk>/", views.GoldTypeSettingsDetailView.as_view()),
    path("api/settings/gold-purities/", views.GoldPuritySettingsListView.as_view()),
    path("api/settings/gold-purities/<int:pk>/", views.GoldPuritySettingsDetailView.as_view()),
    path("api/settings/scrape-property-rates/", views.ScrapePropertyRatesView.as_view()),
    # Backup & Restore
    path("api/settings/backup/create/", views.BackupCreateView.as_view()),
    path("api/settings/backup/list/", views.BackupListView.as_view()),
    path("api/settings/backup/delete/", views.BackupDeleteView.as_view()),
    path("api/settings/backup/restore/", views.BackupRestoreView.as_view()),
    # Documentation Engine
    path("api/settings/documentation/capture/", views.CaptureScreenshotsView.as_view()),
    path("api/settings/documentation/generate-docs/", views.GenerateDocumentsView.as_view()),
    path("api/settings/documentation/validate-capture/", views.ValidateCaptureView.as_view()),
    path("api/settings/documentation/validate-generate/", views.ValidateGenerationView.as_view()),
    path("api/settings/documentation/cancel/", views.CancelDocumentationView.as_view()),
    path("api/settings/documentation/status/", views.DocumentationStatusView.as_view()),
    path("api/settings/documentation/devices/", views.DocumentationDevicesView.as_view()),
    path("api/settings/documentation/history/", views.DocumentationHistoryView.as_view()),
    path("api/settings/documentation/open/", views.OpenFolderView.as_view()),
    # excel export
    path("api/export/excel/", ExportExcelWorkbookView.as_view(), name="export_excel"),
]
