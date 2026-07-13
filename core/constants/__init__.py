from decimal import Decimal

PAGE_PERMISSION_CHOICES = [
    ("dashboard", "Dashboard"),
    ("companies", "Companies"),
    ("salary", "Salary"),
    ("all_companies", "All Companies"),
    ("banks", "Banks"),
    ("bank_certificates", "Bank Certificates"),
    ("currencies", "Currencies"),
    ("balance", "Balance"),
    ("settings", "Settings"),
    ("expense-categories", "Expense Categories"),
    ("exchange_rates", "Exchange Rates"),
    ("gold_price", "Gold Price"),
    ("user_management", "User Management"),
    ("expenses", "Expenses"),
    ("reports", "Reports"),
    ("fixed_assets", "Fixed Assets"),
    ("advanced_reports", "Advanced Reports"),
    ("financial_advisor", "Financial Advisor"),
]

PAGE_PERMISSION_KEYS = [key for key, _ in PAGE_PERMISSION_CHOICES]

MONTH_ORDER = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

ASSET_TYPES = [
    ("Real Estate", "Real Estate"),
    ("Vehicles", "Vehicles"),
    ("Gold", "Gold"),
    ("Other Assets", "Other Assets"),
]

ASSET_STATUS = [
    ("Owned", "Owned"),
    ("Sold", "Sold"),
]

VALUATION_SOURCE = [
    ("Manual", "Manual"),
    ("Automatic", "Automatic"),
]

REAL_ESTATE_ASSET_TYPES = {"Real Estate"}
VEHICLE_ASSET_TYPES = {"Vehicles"}
GOLD_ASSET_TYPES = {"Gold"}
OTHER_ASSET_TYPES = {"Other Assets"}

ASSET_PAYMENT_METHOD_CASH = "Cash"
ASSET_PAYMENT_METHOD_CARD = "Card"
ASSET_PAYMENT_METHOD_BANK = "Bank"
ASSET_PAYMENT_METHOD_BANK_TRANSFER = "Bank Transfer"

ASSET_PAYMENT_METHOD_NORMALIZED = {
    "cash": ASSET_PAYMENT_METHOD_CASH,
    "card": ASSET_PAYMENT_METHOD_CARD,
    "bank": ASSET_PAYMENT_METHOD_BANK,
    "bank transfer": ASSET_PAYMENT_METHOD_BANK_TRANSFER,
    "bank_transfer": ASSET_PAYMENT_METHOD_BANK_TRANSFER,
}

GOLD_UNIT_TO_GRAMS = {
    "g": Decimal("1"),
    "gm": Decimal("1"),
    "gram": Decimal("1"),
    "grams": Decimal("1"),
    "kg": Decimal("1000"),
    "kilogram": Decimal("1000"),
    "kilograms": Decimal("1000"),
    "oz": Decimal("31.1034768"),
    "ounce": Decimal("31.1034768"),
    "ounces": Decimal("31.1034768"),
    "tola": Decimal("11.6638038"),
}

REMINDER_TYPE_CHOICES = [
    ("cert_maturity", "Certificate Maturity"),
    ("insurance_expiry", "Insurance Expiry"),
    ("vehicle_license_expiry", "Vehicle License Expiry"),
    ("property_tax_reminder", "Property Tax Reminder"),
    ("salary_unpaid", "Salary Unpaid"),
    ("salary_day", "Salary Day"),
    ("custom", "Custom"),
]

SALARY_TRIGGER_CHOICES = [
    ("day_of_month", "Day of Month"),
    ("days_before_eom", "Days Before End of Month"),
    ("days_after_som", "Days After Start of Month"),
]

RENOVATION_TYPES = [
    "Finishing",
    "Painting",
    "Flooring",
    "Kitchen",
    "Bathroom",
    "Electrical",
    "Plumbing",
    "Doors & Windows",
    "Furniture",
    "Landscape",
    "Maintenance",
    "Flooring Ceramic",
    "Wall Tiles",
    "Alumital Windows",
    "Other",
]

FURNITURE_CATEGORIES = [
    "Living Room",
    "Bedroom",
    "Kitchen",
    "Bathroom",
    "Dining Room",
    "Office",
    "Outdoor",
    "Air Conditioner",
    "Refrigerator",
    "Freezer",
    "Cooker",
    "Oven",
    "Range Hood",
    "Microwave",
    "Dishwasher",
    "Washing Machine",
    "Water Heater",
    "Water Dispenser",
    "TV",
    "Ceiling Fan",
    "Router",
    "Vacuum Cleaner",
    "Water Pump",
    "Generator",
    "Other Appliance",
    "Other",
]

ACQUISITION_COST_CATEGORIES = [
    "Lawyer Fees",
    "Registration Fees",
    "Notary Fees",
    "Government Fees",
    "Utility Transfer Fees",
    "Brokerage Fees",
    "Other",
]

__all__ = [
    "Decimal",
    "RENOVATION_TYPES",
    "FURNITURE_CATEGORIES",
    "ACQUISITION_COST_CATEGORIES",
]

