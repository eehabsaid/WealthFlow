from django.urls import path
from .. import views

urlpatterns = [
    path("api/budgets/", views.BudgetListView.as_view()),
    path("api/budgets/<int:pk>/", views.BudgetDetailView.as_view()),
    path("api/budgets/alerts/", views.BudgetAlertsView.as_view()),
    path("api/recurring-transactions/", views.RecurringTransactionListView.as_view()),
    path("api/recurring-transactions/<int:pk>/", views.RecurringTransactionDetailView.as_view()),
    path("api/recurring-transactions/due-preview/", views.RecurringTransactionDuePreviewView.as_view()),
    path("api/recurring-transactions/process-due/", views.RecurringTransactionProcessDueView.as_view()),
]
