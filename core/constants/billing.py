"""Billing & subscription choice constants."""

TRIAL_DAYS_DEFAULT = 14

PLAN_CODE_CHOICES = [
    ("basic", "Basic"),
    ("pro", "Pro"),
]

SUBSCRIPTION_STATUS_CHOICES = [
    ("trialing", "Trialing"),
    ("active", "Active"),
    ("past_due", "Past Due"),
    ("canceled", "Canceled"),
    ("expired", "Expired"),
]

# Statuses under which the user should still be granted access to the app.
SUBSCRIPTION_ACCESS_STATUSES = ("trialing", "active", "past_due")

GATEWAY_CHOICES = [
    ("none", "None"),
    ("paymob", "Paymob"),
    ("stripe", "Stripe"),
]

INVOICE_STATUS_CHOICES = [
    ("pending", "Pending"),
    ("paid", "Paid"),
    ("failed", "Failed"),
    ("refunded", "Refunded"),
]
