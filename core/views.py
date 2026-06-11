import json
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from django.db.models import Sum, Count
from django.shortcuts import render, get_object_or_404, redirect
from .models import Company, SalaryEntry, Bank, BalanceEntry, AppSettings, ExchangeRate, GoldPrice, Currency, ExpenseCategory, ExpenseSubcategory, Expense, BankCertificate, PagePermission, PAGE_PERMISSION_CHOICES, UserProfile
from django.core.paginator import Paginator, EmptyPage
from django.db.models import Q
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from django.http import HttpResponse

@method_decorator(csrf_exempt, name="dispatch")
class ExportExcelWorkbookView(View):
    """
    Generates a multi-tab Excel Workbook mimicking the structure, styling,
    and behavior (formulas) of the original financial sheet tracking metrics.
    """
    
    def get(self, request):
        # Forward GET requests to the POST logic so it works via direct links/buttons
        return self.post(request)

    def post(self, request):
        # 1. Create a raw memory-based Excel instance
        wb = openpyxl.Workbook()
        
        # 2. Define standard style profiles matching your theme
        header_font = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="1E3A6E", end_color="1E3A6E", fill_type="solid") # Dark Blue
        data_font = Font(name="Segoe UI", size=10)
        total_font = Font(name="Segoe UI", size=11, bold=True)
        total_fill = PatternFill(start_color="E6EDF2", end_color="E6EDF2", fill_type="solid") # Soft grayish-blue
        
        thin_border = Border(
            left=Side(style='thin', color='D1D5DB'),
            right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'),
            bottom=Side(style='thin', color='D1D5DB')
        )

        # ==========================================
        # TAB 1: BALANCE SUMMARY
        # ==========================================
        ws_balance = wb.active
        ws_balance.title = "BALANCE"
        ws_balance.views.sheetView[0].showGridLines = True
        
        balance_headers = ["Title", "EGP", "USD", "EUR", "SAR", "Gold"]
        ws_balance.append(balance_headers)
        
        # Pull latest available rate benchmarks from your GoldPrice model structure
        latest_rates = GoldPrice.objects.last()
        usd_rate = float(latest_rates.usd_to_egp) if latest_rates and hasattr(latest_rates, 'usd_to_egp') else 51.88
        gold_rate_24k = float(latest_rates.carat_24k) if latest_rates and hasattr(latest_rates, 'carat_24k') else 7526.00
        
        # Populate current static asset snapshot values
        ws_balance.append(["Home Balance", 0, 36930, 4500, 483.25, 125])
        ws_balance.append(["ENBD Bank Account Balance", 358075.51, "", "", "", ""])
        ws_balance.append(["QNB Bank Account Balance", 108021.65, "", "", "", ""])
        ws_balance.append(["QNB Certificates Balance", 3458000, "", "", "", ""])
        
        # Inject structural sum formulas
        ws_balance.cell(row=6, column=1, value="Total EGP Balance").font = total_font
        ws_balance.cell(row=6, column=2, value="=SUM(B2:B5)").font = total_font
        
        # Dynamic multi-currency valuation conversion formula matching sheet patterns
        ws_balance.cell(row=7, column=1, value="Total all Balances").font = total_font
        ws_balance.cell(row=7, column=2, value=f"=B6+(C2*{usd_rate})+(D2*60.25)+(F2/31.1035*{gold_rate_24k})").font = total_font 

        # ==========================================
        # TABS 2+: DYNAMIC SALARY HISTORIES BY COMPANY
        # ==========================================
        companies = Company.objects.all()
        
        for company in companies:
            # Safe unique string limit tracking (max 31 chars required by Excel sheet rules)
            tab_title = str(company.display_name if hasattr(company, 'display_name') else company.name)[:30]
            ws_company = wb.create_sheet(title=tab_title)
            ws_company.views.sheetView[0].showGridLines = True
            
            # Write company specific structured tracking columns
            company_headers = ["Year", "Month", "Expected", "Paid", "Remaining"]
            ws_company.append(company_headers)
            
            # Fetch relational payment allocations chronologically
            entries = SalaryEntry.objects.filter(company=company).order_by('year', 'id')
            
            current_row = 2
            for entry in entries:
                # Resolve field properties or fallback gracefully
                yr = getattr(entry, 'year', '')
                mnth = getattr(entry, 'month', '')
                exp = float(entry.expected) if hasattr(entry, 'expected') and entry.expected else 0.0
                pd = float(entry.paid) if hasattr(entry, 'paid') and entry.paid else 0.0
                
                ws_company.cell(row=current_row, column=1, value=yr)
                ws_company.cell(row=current_row, column=2, value=mnth)
                ws_company.cell(row=current_row, column=3, value=exp)
                ws_company.cell(row=current_row, column=4, value=pd)
                
                # Active Formula tracking: Remaining = Expected - Paid
                ws_company.cell(row=current_row, column=5, value=f"=C{current_row}-D{current_row}")
                current_row += 1
            
            # Final calculation bounds for this specific company tab
            ws_company.cell(row=current_row, column=1, value="Total").font = total_font
            ws_company.cell(row=current_row, column=2, value=f"=COUNTA(B2:B{current_row-1})").font = total_font
            ws_company.cell(row=current_row, column=3, value=f"=SUM(C2:C{current_row-1})").font = total_font
            ws_company.cell(row=current_row, column=4, value=f"=SUM(D2:D{current_row-1})").font = total_font
            ws_company.cell(row=current_row, column=5, value=f"=SUM(E2:E{current_row-1})").font = total_font
            
            # Apply styling accents over summary bounds
            for col in range(1, 6):
                cell = ws_company.cell(row=current_row, column=col)
                cell.fill = total_fill
                cell.border = thin_border

        # ==========================================
        # TAB: BANK CERTIFICATES
        # ==========================================
        ws_certs = wb.create_sheet(title="Bank-Certificates")
        ws_certs.views.sheetView[0].showGridLines = True
        
        cert_headers = ["Amount", "Interest Rate", "Interest Value", "Frequency", "Start Date", "End Date"]
        ws_certs.append(cert_headers)
        
        certs = BankCertificate.objects.all()
        c_row = 2
        for cert in certs:
            amount_val = float(cert.amount) if hasattr(cert, 'amount') and cert.amount else 0.0
            rate_val = float(cert.interest_rate) if hasattr(cert, 'interest_rate') and cert.interest_rate else 0.0
            
            ws_certs.cell(row=c_row, column=1, value=amount_val)
            ws_certs.cell(row=c_row, column=2, value=rate_val)
            
            # Interest Value formula: = (Amount * Interest Rate) / 12
            ws_certs.cell(row=c_row, column=3, value=f"=(A{c_row}*B{c_row})/12")
            ws_certs.cell(row=c_row, column=4, value=getattr(cert, 'frequency', 'Monthly'))
            
            # Resolve flexible date mappings across model variables
            s_date = getattr(cert, 'start_date', getattr(cert, 'issue_date', getattr(cert, 'date', None)))
            if s_date:
                ws_certs.cell(row=c_row, column=5, value=s_date.strftime('%Y-%m-%d') if hasattr(s_date, 'strftime') else str(s_date))
            else:
                ws_certs.cell(row=c_row, column=5, value="")
                
            e_date = getattr(cert, 'end_date', getattr(cert, 'maturity_date', getattr(cert, 'expiry_date', None)))
            if e_date:
                ws_certs.cell(row=c_row, column=6, value=e_date.strftime('%Y-%m-%d') if hasattr(e_date, 'strftime') else str(e_date))
            else:
                ws_certs.cell(row=c_row, column=6, value="")
                
            c_row += 1

        # ==========================================
        # POST-PROCESSING: APPLY FORMATTING & PADDING
        # ==========================================
        for sheet in wb.worksheets:
            # Format row header cells
            for cell in sheet[1]:
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Traversal auto formatting rules engine over structural rows
            for col in sheet.columns:
                max_len = 0
                col_letter = get_column_letter(col[0].column)
                header_text = str(sheet.cell(row=1, column=col[0].column).value)
                
                for cell in col:
                    if cell.row > 1:
                        cell.font = data_font
                        cell.border = thin_border
                        
                        # Currency Formatting rules matching original template looks
                        if type(cell.value) in [int, float] or (isinstance(cell.value, str) and cell.value.startswith('=')):
                            if any(x in header_text for x in ["EGP", "USD", "EUR", "SAR", "Gold", "Expected", "Paid", "Remaining", "Amount", "Value"]):
                                cell.number_format = '#,##0.00'
                            elif "Rate" in header_text:
                                cell.number_format = '0.00%'

                    if cell.value:
                        max_len = max(max_len, len(str(cell.value)))
                
                # Expand specific columns to avoid ### truncation clipping
                sheet.column_dimensions[col_letter].width = max(max_len + 4, 14)

        # 3. Save to structural http application output streams
        response = HttpResponse(content_type='application/vnd.openpyxl.sheet')
        response['Content-Disposition'] = 'attachment; filename="SalaryTracker_Balance.xlsx"'
        wb.save(response)
        return response
        
User = get_user_model()

PAGE_PERMISSION_KEYS = [key for key, _ in PAGE_PERMISSION_CHOICES]

# Month sort order — ensures API returns months in calendar order, not alphabetically
MONTH_ORDER = [
    'January','February','March','April','May','June',
    'July','August','September','October','November','December',
    'Quarter-Bonuses',
]

def month_sort_key(entry_dict):
    try:
        return MONTH_ORDER.index(entry_dict.get('month', ''))
    except ValueError:
        return len(MONTH_ORDER)



@login_required(login_url='/accounts/login/')
def index(request):
    return render(request, "index.html")


def _api_auth_required(request):
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    return None


class AdminRequiredMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=401)
        return JsonResponse({"error": "Admin access required"}, status=403)


def _build_user_dict(user):
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def _get_user_allowed_pages(user):
    return [perm.page for perm in user.page_permissions.all()]


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('/')
        return render(request, 'login.html', {'error': 'Invalid username or password'})
    return render(request, 'login.html')


def signup_view(request):
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if not username or not email or not password:
            return render(request, 'signup.html', {'error': 'All fields are required'})
        if password != confirm_password:
            return render(request, 'signup.html', {'error': 'Passwords do not match'})
        if User.objects.filter(username=username).exists():
            return render(request, 'signup.html', {'error': 'Username is already taken'})
        if User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Email is already registered'})

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('/')

    return render(request, 'signup.html')


def logout_view(request):
    logout(request)
    return redirect('/accounts/login/')


class LoginAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
        username = data.get('username', '').strip()
        password = data.get('password', '')
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({'error': 'Invalid credentials'}, status=400)
        login(request, user)
        return JsonResponse({'user': _build_user_dict(user), 'allowed_pages': _get_user_allowed_pages(user)})


class SignupAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')

        if not username or not email or not password:
            return JsonResponse({'error': 'Username, email and password are required'}, status=400)
        if password != confirm_password:
            return JsonResponse({'error': 'Passwords do not match'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username is already taken'}, status=400)
        if User.objects.filter(email=email).exists():
            return JsonResponse({'error': 'Email is already registered'}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return JsonResponse({'user': _build_user_dict(user), 'allowed_pages': _get_user_allowed_pages(user)})


class LogoutAPIView(View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        logout(request)
        return JsonResponse({'success': True})


class CurrentUserView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'user': None, 'allowed_pages': []})
        return JsonResponse({'user': _build_user_dict(request.user), 'allowed_pages': _get_user_allowed_pages(request.user)})


class UserListView(AdminRequiredMixin, View):
    def get(self, request):
        # support pagination and search: ?page=1&page_size=20&q=term
        q = request.GET.get('q', '').strip()
        page = int(request.GET.get('page', 1) or 1)
        page_size = int(request.GET.get('page_size', 20) or 20)

        qs = User.objects.order_by('username').all()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))

        paginator = Paginator(qs, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)

        users = [_build_user_dict(u) for u in page_obj.object_list]
        return JsonResponse({
            'users': users,
            'page': page_obj.number,
            'page_size': page_size,
            'total': paginator.count,
            'num_pages': paginator.num_pages,
        })

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        if not username or not email or not password:
            return JsonResponse({'error': 'username, email and password are required'}, status=400)
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username is already taken'}, status=400)
        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_active = data.get('is_active', True)
        user.is_staff = data.get('is_staff', False)
        user.is_superuser = data.get('is_superuser', False)
        user.save()
        return JsonResponse({'user': _build_user_dict(user)}, status=201)


class UserDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        return JsonResponse({'user': _build_user_dict(user)})

    def put(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
        for field in ['email', 'is_active', 'is_staff', 'is_superuser']:
            if field in data:
                setattr(user, field, data[field])
        if data.get('password'):
            user.set_password(data['password'])
        user.save()
        return JsonResponse({'user': _build_user_dict(user)})

    def delete(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        user.delete()
        return JsonResponse({'deleted': pk})


class UserPermissionListView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        permissions = user.page_permissions.all()
        return JsonResponse({'permissions': [perm.to_dict() for perm in permissions], 'available_pages': PAGE_PERMISSION_CHOICES})

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
        page = data.get('page')
        if page not in PAGE_PERMISSION_KEYS:
            return JsonResponse({'error': 'Invalid page permission'}, status=400)
        perm, created = PagePermission.objects.get_or_create(user=user, page=page)
        return JsonResponse({'permission': perm.to_dict()}, status=201 if created else 200)


class UserBulkActionView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request):
        data = json.loads(request.body.decode('utf-8') if isinstance(request.body, bytes) else request.body)
        action = data.get('action')
        ids = data.get('ids') or []
        if not action or not isinstance(ids, list):
            return JsonResponse({'error': 'action and ids required'}, status=400)

        users = User.objects.filter(id__in=ids)
        changed = 0
        if action == 'delete':
            changed = users.count()
            users.delete()
        elif action == 'activate':
            changed = users.update(is_active=True)
        elif action == 'deactivate':
            changed = users.update(is_active=False)
        elif action == 'set_staff':
            val = bool(data.get('value'))
            changed = users.update(is_staff=val)
        elif action == 'set_superuser':
            val = bool(data.get('value'))
            changed = users.update(is_superuser=val)
        else:
            return JsonResponse({'error': 'unknown action'}, status=400)

        return JsonResponse({'changed': changed})


class UserPermissionDetailView(AdminRequiredMixin, View):
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, pk):
        perm = get_object_or_404(PagePermission, pk=pk)
        perm.delete()
        return JsonResponse({'deleted': pk})


class PagePermissionChoicesView(AdminRequiredMixin, View):
    def get(self, request):
        return JsonResponse({'available_pages': PAGE_PERMISSION_CHOICES})


@login_required(login_url='/accounts/login/')
def user_management_page(request):
    # Only staff (admins) can access the management UI
    if not request.user.is_staff:
        return redirect('/')
    return render(request, 'user_management.html')


@method_decorator(csrf_exempt, name="dispatch")
class CompanyListView(View):
    def get(self, request):
        companies = Company.objects.all().order_by("order")
        return JsonResponse({"companies": [c.to_dict() for c in companies]})

    def post(self, request):
        data = json.loads(request.body)
        company = Company.objects.create(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            group_name=data.get("group_name", ""),
            color_hex=data.get("color_hex", "#0d6efd"),
            is_active=data.get("is_active", True),
            order=data.get("order", 0),
        )
        return JsonResponse(company.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class CompanyDetailView(View):
    def get(self, request, pk):
        c = get_object_or_404(Company, pk=pk)
        return JsonResponse(c.to_dict())

    def put(self, request, pk):
        c = get_object_or_404(Company, pk=pk)
        data = json.loads(request.body)
        for field in ["name", "display_name", "group_name", "color_hex", "is_active", "order"]:
            if field in data:
                setattr(c, field, data[field])
        c.save()
        return JsonResponse(c.to_dict())

    def delete(self, request, pk):
        c = get_object_or_404(Company, pk=pk)
        c.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class SalaryListView(View):
    def get(self, request):
        qs = SalaryEntry.objects.select_related("company").all()
        company_id = request.GET.get("company")
        year = request.GET.get("year")
        if company_id:
            qs = qs.filter(company_id=company_id)
        if year:
            qs = qs.filter(year=year)
        return JsonResponse({"entries": sorted([e.to_dict() for e in qs], key=month_sort_key)})

    def post(self, request):
        data = json.loads(request.body)
        entry = SalaryEntry.objects.create(
            company_id=data["company_id"],
            year=data["year"],
            month=data["month"],
            expected=data.get("expected", 0),
            paid=data.get("paid", 0),
            bonus=data.get("bonus", 0),
            notes=data.get("notes", ""),
        )
        return JsonResponse(entry.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class SalaryDetailView(View):
    def put(self, request, pk):
        entry = get_object_or_404(SalaryEntry, pk=pk)
        data = json.loads(request.body)
        for field in ["year", "month", "expected", "paid", "bonus", "notes"]:
            if field in data:
                setattr(entry, field, data[field])
        entry.save()
        return JsonResponse(entry.to_dict())

    def delete(self, request, pk):
        entry = get_object_or_404(SalaryEntry, pk=pk)
        entry.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class SalarySummaryView(View):
    def get(self, request):
        companies = Company.objects.all().order_by("order")
        result = []
        grand = {"total_months": 0, "total_expected": 0.0,
                 "total_paid": 0.0, "total_remaining": 0.0, "total_bonus": 0.0}
        for c in companies:
            entries = c.salary_entries.all()
            agg = entries.aggregate(
                months=Count("id", filter=Q(paid__gt=0)),
                exp=Sum("expected"),
                paid=Sum("paid"),
                bonus=Sum("bonus"),
            )
            exp = float(agg["exp"] or 0)
            paid = float(agg["paid"] or 0)
            bonus = float(agg["bonus"] or 0)
            result.append({
                "id": c.id,
                "name": c.name,
                "display_name": c.display_name,
                "group_name": c.group_name,
                "color_hex": c.color_hex,
                "total_months": agg["months"],
                "total_expected": exp,
                "total_paid": paid,
                "total_remaining": max(0.0, exp - paid),
                "total_bonus": bonus,
                "years": list(
                    entries.values_list("year", flat=True).distinct().order_by("year")
                ),
            })
            grand["total_months"] += agg["months"]
            grand["total_expected"] += exp
            grand["total_paid"] += paid
            grand["total_remaining"] += max(0.0, exp - paid)
            grand["total_bonus"] += bonus
        return JsonResponse({"companies": result, "grand_total": grand})


@method_decorator(csrf_exempt, name="dispatch")
class BankListView(View):
    def get(self, request):
        return JsonResponse({"banks": [b.to_dict() for b in Bank.objects.all()]})

    def post(self, request):
        data = json.loads(request.body)
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
        return JsonResponse(bank.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class BankDetailView(View):
    def put(self, request, pk):
        bank = get_object_or_404(Bank, pk=pk)
        data = json.loads(request.body)
        for field in ["name", "account_number", "card_id", "swift_code",
                      "customer_id", "customer_name", "is_active", "order"]:
            if field in data:
                setattr(bank, field, data[field])
        bank.save()
        return JsonResponse(bank.to_dict())

    def delete(self, request, pk):
        bank = get_object_or_404(Bank, pk=pk)
        bank.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class BankCertificateListView(View):
    def get(self, request):
        certificates = BankCertificate.objects.select_related("bank", "currency").all()
        return JsonResponse({"certificates": [c.to_dict() for c in certificates]})

    def post(self, request):
        data = json.loads(request.body)
        certificate = BankCertificate.objects.create(
            bank_id=data["bank_id"],
            currency_id=data.get("currency_id"),
            issue_date=data.get("issue_date") or None,
            expiry_date=data.get("expiry_date") or None,
            amount=data.get("amount", 0),
            status=data.get("status", "Active"),
            notes=data.get("notes", ""),
        )
        return JsonResponse(certificate.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class BankCertificateDetailView(View):
    def get(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        return JsonResponse(certificate.to_dict())

    def put(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        data = json.loads(request.body)
        for field in ["bank_id", "currency_id", "issue_date",
                      "expiry_date", "amount", "interest_rate", "interest_value",
                      "frequency", "status", "notes"]:
            if field in data:
                setattr(certificate, field, data[field])
        certificate.save()
        return JsonResponse(certificate.to_dict())

    def delete(self, request, pk):
        certificate = get_object_or_404(BankCertificate, pk=pk)
        certificate.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
class CurrencyListView(View):
    def get(self, request):
        currencies = Currency.objects.all().order_by("order")
        return JsonResponse({"currencies": [c.to_dict() for c in currencies]})

    def post(self, request):
        data = json.loads(request.body)
        currency = Currency.objects.create(
            code=data["code"],
            symbol=data.get("symbol", ""),
            flag=data.get("flag", "💱"),
            name=data.get("name", data["code"]),
            order=data.get("order", 0),
        )
        return JsonResponse(currency.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class CurrencyDetailView(View):
    def get(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        return JsonResponse(c.to_dict())

    def put(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        data = json.loads(request.body)
        for field in ["code", "symbol", "flag", "name", "order"]:
            if field in data:
                setattr(c, field, data[field])
        c.save()
        return JsonResponse(c.to_dict())

    def delete(self, request, pk):
        c = get_object_or_404(Currency, pk=pk)
        c.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
@method_decorator(csrf_exempt, name="dispatch")
class BalanceListView(View):
    def get(self, request):
        entries = BalanceEntry.objects.select_related("bank", "currency").all()
        return JsonResponse({"entries": [e.to_dict() for e in entries]})

    def post(self, request):
        data = json.loads(request.body)
        entry = BalanceEntry.objects.create(
            title=data["title"],
            bank_id=data.get("bank_id"),
            currency_id=data.get("currency_id", 1),
            amount=data.get("amount", 0),
            notes=data.get("notes", ""),
        )
        return JsonResponse(entry.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class BalanceDetailView(View):
    def put(self, request, pk):
        entry = get_object_or_404(BalanceEntry, pk=pk)
        data = json.loads(request.body)
        for field in ["title", "bank_id", "currency_id", "amount", "notes"]:
            if field in data:
                setattr(entry, field, data[field])
        entry.save()
        return JsonResponse(entry.to_dict())

    def delete(self, request, pk):
        entry = get_object_or_404(BalanceEntry, pk=pk)
        entry.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class SettingsView(View):
    def get(self, request):
        settings = AppSettings.objects.all()
        return JsonResponse({"settings": {s.key: s.value for s in settings}})

    def post(self, request):
        data = json.loads(request.body)
        obj = AppSettings.set(data["key"], data["value"])
        return JsonResponse({"key": obj.key, "value": obj.value})


# ── Exchange Rates views ──────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class ExchangeRateListView(View):
    """GET  /api/rates/          → latest rate per currency
       POST /api/rates/refresh/  → fetch from internet and save"""

    def get(self, request):
        """Return the single most-recent row per currency code."""
        from django.db.models import Max
        latest_ids = (
            ExchangeRate.objects
            .values("currency_code")
            .annotate(max_id=Max("id"))
            .values_list("max_id", flat=True)
        )
        rates = ExchangeRate.objects.filter(id__in=latest_ids).order_by("currency_code")
        last = ExchangeRate.objects.order_by("-fetched_at").first()
        return JsonResponse({
            "rates":      [r.to_dict() for r in rates],
            "fetched_at": last.fetched_at.strftime("%Y-%m-%d %H:%M") if last else None,
        })


@method_decorator(csrf_exempt, name="dispatch")
class ExchangeRateRefreshView(View):
    """Calls open.er-api.com and saves latest rates to DB."""

    def post(self, request):
        import urllib.request as _ur
        import json as _json
        import decimal

        CURRENCY_NAMES = {
            "USD": "US Dollar",       "EUR": "Euro",
            "GBP": "Pound Sterling",  "SAR": "Saudi Riyal",
            "AED": "UAE Dirham",      "KWD": "Kuwaiti Dinar",
            "CAD": "Canadian Dollar", "CHF": "Swiss Franc",
            "JPY": "Japanese Yen",    "CNY": "Chinese Yuan",
            "QAR": "Qatari Riyal",    "BHD": "Bahraini Dinar",
            "OMR": "Omani Riyal",     "JOD": "Jordanian Dinar",
            "NOK": "Norwegian Krone", "SEK": "Swedish Krona",
            "DKK": "Danish Krone",    "AUD": "Australian Dollar",
        }

        try:
            url = "https://open.er-api.com/v6/latest/EGP"
            req = _ur.Request(url, headers={"User-Agent": "SalaryTracker/1.0"})
            with _ur.urlopen(req, timeout=15) as resp:
                data = _json.loads(resp.read().decode())

            if data.get("result") != "success":
                return JsonResponse({"error": "API returned non-success"}, status=502)

            rates_raw = data.get("rates", {})   # all rates are X per 1 EGP
            saved = 0
            with transaction.atomic():
                ExchangeRate.objects.all().delete()
                for code, name in CURRENCY_NAMES.items():
                    if code not in rates_raw:
                        continue
                    # rates_raw[code] = how many <code> per 1 EGP
                    # We want EGP per 1 <code>  (buy rate)
                    egp_per_unit = 1.0 / float(rates_raw[code]) if float(rates_raw[code]) else 0
                    # Apply a typical 0.5% spread for buy/sell simulation
                    spread = egp_per_unit * 0.005
                    ExchangeRate.objects.create(
                        currency_code=code,
                        currency_name=name,
                        buy_rate=round(egp_per_unit - spread, 6),
                        sell_rate=round(egp_per_unit + spread, 6),
                        mid_rate=round(egp_per_unit, 6),
                        source="open.er-api.com",
                    )
                    saved += 1

            return JsonResponse({"saved": saved, "message": f"Fetched {saved} currencies"})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)


# ── Gold Price views ──────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class GoldPriceListView(View):
    """GET /api/gold/ → latest gold price"""

    def get(self, request):
        latest = GoldPrice.objects.order_by("-fetched_at").first()
        if not latest:
            return JsonResponse({"gold": None, "message": "No data yet. Click Refresh."})
        return JsonResponse({"gold": latest.to_dict()})


@method_decorator(csrf_exempt, name="dispatch")
class GoldPriceRefreshView(View):
    """Fetches EGP gold prices from goldbullioneg.com and USD/EGP from open.er-api.com."""
    def get(self, request):
        return self.post(request)
    
    def post(self, request):
        import urllib.request as _ur
        import json as _json
        from html.parser import HTMLParser
        import re

        class GoldTableParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.in_table = False
                self.in_tr = False
                self.in_td = False
                self.current_cell = None
                self.current_row = []
                self.rows = []

            def handle_starttag(self, tag, attrs):
                if tag == 'table' and not self.in_table:
                    self.in_table = True
                    return
                if not self.in_table:
                    return
                if tag == 'tr':
                    self.in_tr = True
                    self.current_row = []
                elif self.in_tr and tag == 'td':
                    self.in_td = True
                    self.current_cell = {'text': '', 'data_val': None}
                    attrs = dict(attrs)
                    if 'data-val' in attrs:
                        self.current_cell['data_val'] = attrs['data-val']

            def handle_data(self, data):
                if self.in_td and self.current_cell is not None:
                    self.current_cell['text'] += data

            def handle_endtag(self, tag):
                if tag == 'td' and self.in_td:
                    self.current_row.append(self.current_cell)
                    self.in_td = False
                    self.current_cell = None
                elif tag == 'tr' and self.in_tr:
                    if self.current_row:
                        self.rows.append(self.current_row)
                    self.in_tr = False
                elif tag == 'table' and self.in_table:
                    self.in_table = False

        try:
            # Step 1: Scrape gold prices directly from goldbullioneg.com (EGP table)
            page_url = "https://goldbullioneg.com/%D8%A3%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8/"
            req = _ur.Request(page_url, headers={"User-Agent": "SalaryTracker/1.0"})
            with _ur.urlopen(req, timeout=15) as resp:
                page_html = resp.read().decode('utf-8', errors='ignore')

            parser = GoldTableParser()
            parser.feed(page_html)

            if not parser.rows or len(parser.rows) < 8:
                return JsonResponse({"error": "Unable to parse complete gold price table from goldbullioneg.com"}, status=502)

            prices_egp = {}  # {carat: {'buy': X, 'sell': Y}}
            usd_to_egp = None
            usd_per_oz = None
            
            for idx, row in enumerate(parser.rows):
                if len(row) < 3:
                    continue
                label = (row[0]['text'] or '').strip()
                buy_val = (row[1]['data_val'] or row[1]['text'] or '').strip()
                sell_val = (row[2]['data_val'] or row[2]['text'] or '').strip()
                
                if not buy_val or not sell_val:
                    continue
                
                try:
                    buy_num = float(buy_val.replace(',', ''))
                    sell_num = float(sell_val.replace(',', ''))
                except ValueError:
                    continue
                
                # Check for karat prices (جرام عيار X)
                karat_match = re.search(r'عيار\s*([0-9]{1,2})', label)
                if karat_match:
                    carat = int(karat_match.group(1))
                    prices_egp[carat] = {'buy': buy_num, 'sell': sell_num}
                    continue
                
                # Check for USD/EGP rate (الدولار)
                if 'دولار' in label.lower():
                    usd_to_egp = sell_num
                    continue
                
                # Check for USD spot price per ounce (الأونصة)
                if 'أونصة' in label.lower() or 'ounce' in label.lower():
                    usd_per_oz = sell_num
                    continue

            if not all(k in prices_egp for k in (24, 22, 21, 18)):
                return JsonResponse({"error": "Missing required karat prices from goldbullioneg.com"}, status=502)
            
            if usd_to_egp is None:
                return JsonResponse({"error": "Could not find USD/EGP rate on goldbullioneg.com"}, status=502)
            
            if usd_per_oz is None:
                return JsonResponse({"error": "Could not find USD/oz spot price on goldbullioneg.com"}, status=502)

            # Calculate USD per gram from the EGP per gram (using sell price)
            usd_gram_24k = prices_egp[24]['sell'] / usd_to_egp if usd_to_egp else 0
            
            with transaction.atomic():
                GoldPrice.objects.all().delete()
                gp = GoldPrice.objects.create(
                    carat_24k    = round(prices_egp[24]['sell'], 2),
                    carat_22k    = round(prices_egp[22]['sell'], 2),
                    carat_21k    = round(prices_egp[21]['sell'], 2),
                    carat_18k    = round(prices_egp[18]['sell'], 2),
                    carat_24k_buy = round(prices_egp[24]['buy'], 2),
                    carat_22k_buy = round(prices_egp[22]['buy'], 2),
                    carat_21k_buy = round(prices_egp[21]['buy'], 2),
                    carat_18k_buy = round(prices_egp[18]['buy'], 2),
                    usd_gram_24k = round(usd_gram_24k, 6),
                    usd_per_oz   = round(usd_per_oz, 4),
                    usd_to_egp   = round(usd_to_egp, 6),
                    source_gold  = "goldbullioneg.com",
                    source_fx    = "goldbullioneg.com",
                )
            return JsonResponse({"gold": gp.to_dict()})

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=502)


# ══════════════════════════════════════════════════════════════
# EXPENSE VIEWS
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name="dispatch")
class ExpenseCategoryListView(View):
    def get(self, request):
        cats = ExpenseCategory.objects.prefetch_related("subcategories").all()
        data = []
        for c in cats:
            d = c.to_dict()
            d["subcategories"] = [s.to_dict() for s in c.subcategories.all()]
            data.append(d)
        return JsonResponse({"categories": data})

    def post(self, request):
        data = json.loads(request.body)
        cat = ExpenseCategory.objects.create(
            name=data["name"],
            icon=data.get("icon", "💰"),
            color_hex=data.get("color_hex", "#0d6efd"),
            order=data.get("order", 0),
        )
        return JsonResponse(cat.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseCategoryDetailView(View):
    def put(self, request, pk):
        cat = get_object_or_404(ExpenseCategory, pk=pk)
        data = json.loads(request.body)
        for f in ["name", "icon", "color_hex", "order"]:
            if f in data:
                setattr(cat, f, data[f])
        cat.save()
        return JsonResponse(cat.to_dict())

    def delete(self, request, pk):
        cat = get_object_or_404(ExpenseCategory, pk=pk)
        cat.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSubcategoryListView(View):
    def post(self, request):
        data = json.loads(request.body)
        sub = ExpenseSubcategory.objects.create(
            category_id=data["category_id"],
            name=data["name"],
            order=data.get("order", 0),
        )
        return JsonResponse(sub.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSubcategoryDetailView(View):
    def put(self, request, pk):
        sub = get_object_or_404(ExpenseSubcategory, pk=pk)
        data = json.loads(request.body)
        for f in ["name", "order"]:
            if f in data:
                setattr(sub, f, data[f])
        sub.save()
        return JsonResponse(sub.to_dict())

    def delete(self, request, pk):
        sub = get_object_or_404(ExpenseSubcategory, pk=pk)
        sub.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseListView(View):
    def get(self, request):
        qs = Expense.objects.select_related(
            "category",
            "subcategory",
            "currency"
        ).all()

        year = request.GET.get("year")
        month = request.GET.get("month")
        cat_id = request.GET.get("category")
        search = request.GET.get("search", "").strip()

        start_date = request.GET.get("start")
        end_date = request.GET.get("end")

        if start_date and end_date:
            qs = qs.filter(
                date__gte=start_date,
                date__lte=end_date
            )
        else:
            if year:
                qs = qs.filter(year=int(year))

            if month:
                qs = qs.filter(month=int(month))

        if cat_id:
            qs = qs.filter(category_id=int(cat_id))

        if search:
            qs = (
                qs.filter(description__icontains=search)
                | qs.filter(notes__icontains=search)
            )

        entries = [e.to_dict() for e in qs]

        total = sum(
            float(e["amount"] or 0)
            for e in entries
        )

        return JsonResponse({
            "entries": entries,
            "total": total
        })

    def post(self, request):
        data  = json.loads(request.body)
        from datetime import date as _date
        d     = _date.fromisoformat(data["date"])
        exp   = Expense.objects.create(
            date=d, year=d.year, month=d.month,
            category_id=data.get("category_id"),
            subcategory_id=data.get("subcategory_id"),
            description=data.get("description", ""),
            amount=data.get("amount", 0),
            currency_id=data.get("currency_id"),
            payment_method=data.get("payment_method", "Cash"),
            notes=data.get("notes", ""),
        )
        return JsonResponse(exp.to_dict(), status=201)


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseDetailView(View):
    def put(self, request, pk):
        exp  = get_object_or_404(Expense, pk=pk)
        data = json.loads(request.body)
        if "date" in data:
            from datetime import date as _date
            d = _date.fromisoformat(data["date"])
            exp.date = d; exp.year = d.year; exp.month = d.month
        for f in ["category_id","subcategory_id","description",
                  "amount","currency_id","payment_method","notes"]:
            if f in data:
                setattr(exp, f, data[f])
        exp.save()
        return JsonResponse(exp.to_dict())

    def delete(self, request, pk):
        exp = get_object_or_404(Expense, pk=pk)
        exp.delete()
        return JsonResponse({"deleted": pk})


@method_decorator(csrf_exempt, name="dispatch")
class ExpenseSummaryView(View):
    """Returns monthly totals + category breakdown for charts."""
    def get(self, request):
        from django.db.models import Sum
        year  = request.GET.get("year")
        month = request.GET.get("month")
        qs    = Expense.objects.all()
        if year:  qs = qs.filter(year=int(year))
        if month: qs = qs.filter(month=int(month))

        # By category
        by_cat = {}
        for e in qs.select_related("category"):
            name  = e.category.name  if e.category  else "Uncategorised"
            icon  = e.category.icon  if e.category  else "💰"
            color = e.category.color_hex if e.category else "#6c757d"
            key   = name
            if key not in by_cat:
                by_cat[key] = {"name": name, "icon": icon, "color": color, "total": 0}
            by_cat[key]["total"] += float(e.amount)

        # Monthly trend (last 12 months)
        from django.db.models.functions import TruncMonth
        import datetime
        monthly = []
        for m in range(1, 13):
            y = int(year) if year else datetime.date.today().year
            total = Expense.objects.filter(year=y, month=m).aggregate(
                t=Sum("amount"))["t"] or 0
            monthly.append({"month": m, "total": float(total)})

        grand_total = sum(v["total"] for v in by_cat.values())
        return JsonResponse({
            "by_category": list(by_cat.values()),
            "monthly_trend": monthly,
            "grand_total": grand_total,
        })


# ══════════════════════════════════════════════════════════════
# PDF REPORT VIEW
# ══════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name="dispatch")
class GenerateReportView(View):
    """
    POST /api/reports/generate/
    body: { type: "monthly"|"yearly"|"custom",
            year: 2026, month: 5,       # for monthly
            start_date: "2026-01-01",   # for custom
            end_date:   "2026-05-31" }
    Returns: PDF file
    """
    def post(self, request):
        import json as _json, datetime
        from django.http import HttpResponse, JsonResponse
        from django.db.models import Sum

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                            Table, TableStyle, HRFlowable)
            from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
            import io
        except ImportError:
            return JsonResponse({"error": "reportlab not installed. Run: pip install reportlab"}, status=500)

        data       = _json.loads(request.body)
        rtype      = data.get("type", "monthly")
        year       = int(data.get("year", datetime.date.today().year))
        month      = int(data.get("month", datetime.date.today().month))
        
        # Accept both parameter styles (with or without suffix) to be fully secure
        start_date = data.get("start_date") or data.get("start")
        end_date   = data.get("end_date") or data.get("end")

        # ── Filter expenses safely across all field schemas ──
        qs = Expense.objects.select_related("category", "subcategory").all()
        if rtype == "monthly":
            qs = qs.filter(year=year, month=month)
            title_str = f"Monthly Report — {datetime.date(year, month, 1).strftime('%B %Y')}"
            filename  = f"report_{year}_{month:02d}.pdf"
        elif rtype == "yearly":
            qs = qs.filter(year=year)
            title_str = f"Yearly Report — {year}"
            filename  = f"report_{year}.pdf"
        else:

            from datetime import date as _date

            sd = _date.fromisoformat(start_date)
            ed = _date.fromisoformat(end_date)

            qs = qs.filter(
                date__gte=sd,
                date__lte=ed
            )

            title_str = f"Report {start_date} to {end_date}"

            filename = f"report_{start_date}_{end_date}.pdf"

        expenses   = list(qs)
        total_exp  = sum(float(e.amount) for e in expenses)

        # Income for period (salary paid amounts)
        total_inc = 0
        if rtype == "monthly":
            # Target the previous month relative to the report month
            curr_date = datetime.date(year, month, 1)
            prev_date = curr_date - datetime.timedelta(days=1)
            sal_qs = SalaryEntry.objects.filter(
                year=prev_date.year, 
                month=prev_date.strftime("%B")
            )
        elif rtype == "yearly":
            sal_qs = SalaryEntry.objects.filter(year=year)
        else:
            from datetime import date as _date

            sd = _date.fromisoformat(start_date)
            ed = _date.fromisoformat(end_date)

            MONTHS = [
                "January", "February", "March", "April",
                "May", "June", "July", "August",
                "September", "October", "November", "December"
            ]

            sal_qs = SalaryEntry.objects.none()

            for year_num in range(sd.year, ed.year + 1):

                year_entries = SalaryEntry.objects.filter(
                    year=year_num
                )

                for entry in year_entries:

                    try:

                        month_index = MONTHS.index(entry.month) + 1

                        entry_date = _date(
                            year_num,
                            month_index,
                            1
                        )

                        if sd <= entry_date <= ed:

                            sal_qs |= SalaryEntry.objects.filter(
                                pk=entry.pk
                            )

                    except Exception:
                        pass
            
        total_inc += sum(float(s.paid or 0) for s in sal_qs)
        
        # 2. Add Bank Interest (Summing all certificates)
        total_interest = sum(float(c.interest_value or 0) for c in BankCertificate.objects.all())
        #total_interest = 0
        total_inc += total_interest

        # 3. Final Calculations
        net_sav    = total_inc - total_exp
        sav_rate   = (net_sav / total_inc * 100) if total_inc > 0 else 0

        # Category breakdown
        cat_totals = {}
        for e in expenses:
            cname = e.category.name if e.category else "Uncategorised"
            cat_totals[cname] = cat_totals.get(cname, 0) + float(e.amount)

        # ── Build PDF ──
        buffer = io.BytesIO()
        doc    = SimpleDocTemplate(buffer, pagesize=A4,
                                   rightMargin=2*cm, leftMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        navy   = colors.HexColor("#0d1530")
        blue   = colors.HexColor("#1a6ef5")
        green  = colors.HexColor("#00d68f")
        red    = colors.HexColor("#ff4d6d")
        yellow = colors.HexColor("#ffd166")
        grey   = colors.HexColor("#7b97cc")

        H1 = ParagraphStyle("H1", fontSize=22, textColor=blue,
                             spaceAfter=6, alignment=TA_CENTER, fontName="Helvetica-Bold")
        H2 = ParagraphStyle("H2", fontSize=14, textColor=navy,
                             spaceAfter=4, spaceBefore=12, fontName="Helvetica-Bold")
        BODY = ParagraphStyle("BODY", fontSize=10, textColor=navy, spaceAfter=4)
        SUB  = ParagraphStyle("SUB", fontSize=9, textColor=grey, spaceAfter=2)

        story = []

        # Cover
        story.append(Spacer(1, 1*cm))
        story.append(Paragraph("💰 Financial Report", H1))
        story.append(Paragraph(title_str, ParagraphStyle("S",fontSize=13,
            textColor=grey,alignment=TA_CENTER,spaceAfter=6)))
        story.append(HRFlowable(width="100%", thickness=1, color=blue))
        story.append(Spacer(1, 0.5*cm))

        # Summary KPIs
        story.append(Paragraph("Summary", H2))
        kpi_data = [
            ["Metric", "Amount (EGP)"],
            ["Total Income",   f"{total_inc:,.2f}"],
            ["Total Expenses", f"{total_exp:,.2f}"],
            ["Net Savings",    f"{net_sav:,.2f}"],
            ["Savings Rate",   f"{sav_rate:.1f}%"],
        ]
        kpi_table = Table(kpi_data, colWidths=[9*cm, 7*cm])
        kpi_table.setStyle(TableStyle([
            ("BACKGROUND",   (0,0), (-1,0),  blue),
            ("TEXTCOLOR",    (0,0), (-1,0),  colors.white),
            ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
            ("FONTSIZE",     (0,0), (-1,-1), 10),
            ("ALIGN",        (1,0), (1,-1),  "RIGHT"),
            ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.HexColor("#f0f4ff"), colors.white]),
            ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#1e3a6e")),
            ("PADDING",      (0,0), (-1,-1), 7),
            ("TEXTCOLOR",    (1,3), (1,3), green if net_sav >= 0 else red),
            ("FONTNAME",     (1,3), (1,3), "Helvetica-Bold"),
        ]))
        story.append(kpi_table)
        story.append(Spacer(1, 0.5*cm))

        # Category breakdown
        if cat_totals:
            story.append(Paragraph("Expense Breakdown by Category", H2))
            cat_data = [["Category", "Amount (EGP)", "% of Total"]]
            for cname, ctotal in sorted(cat_totals.items(), key=lambda x: -x[1]):
                pct = (ctotal / total_exp * 100) if total_exp > 0 else 0
                cat_data.append([cname, f"{ctotal:,.2f}", f"{pct:.1f}%"])
            cat_data.append(["TOTAL", f"{total_exp:,.2f}", "100%"])
            cat_table = Table(cat_data, colWidths=[9*cm, 5*cm, 3*cm])
            cat_table.setStyle(TableStyle([
                ("BACKGROUND",   (0,0), (-1,0),  blue),
                ("TEXTCOLOR",    (0,0), (-1,0),  colors.white),
                ("FONTNAME",     (0,0), (-1,0),  "Helvetica-Bold"),
                ("FONTNAME",     (0,-1),(-1,-1), "Helvetica-Bold"),
                ("BACKGROUND",   (0,-1),(-1,-1), colors.HexColor("#e8f0fe")),
                ("FONTSIZE",     (0,0), (-1,-1), 9),
                ("ALIGN",        (1,0), (-1,-1), "RIGHT"),
                ("ROWBACKGROUNDS",(0,1),(-1,-2), [colors.HexColor("#f0f4ff"), colors.white]),
                ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#1e3a6e")),
                ("PADDING",      (0,0), (-1,-1), 6),
            ]))
            story.append(cat_table)
            story.append(Spacer(1, 0.5*cm))

        # Detailed expense entries
        if expenses:
            story.append(Paragraph("Expense Entries", H2))
            exp_data = [["Date", "Category", "Description", "Method", "Amount"]]
            for e in sorted(expenses, key=lambda x: x.date):
                exp_data.append([
                    e.date.strftime("%d/%m/%Y"),
                    e.category.name if e.category else "—",
                    (e.description or "—")[:40],
                    e.payment_method or "—",
                    f"{float(e.amount):,.2f}",
                ])
            exp_table = Table(exp_data, colWidths=[2.5*cm, 3.5*cm, 6*cm, 3*cm, 3*cm])
            exp_table.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,0), blue),
                ("TEXTCOLOR",     (0,0), (-1,0), colors.white),
                ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",      (0,0), (-1,-1), 8),
                ("ALIGN",         (4,0), (4,-1), "RIGHT"),
                ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#f0f4ff"), colors.white]),
                ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#1e3a6e")),
                ("PADDING",       (0,0), (-1,-1), 5),
            ]))
            story.append(exp_table)

        # Footer
        story.append(Spacer(1, 1*cm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=grey))
        story.append(Paragraph(
            f"Generated by Salary & Balance Tracker — {datetime.date.today().strftime('%d %B %Y')}",
            ParagraphStyle("F", fontSize=8, textColor=grey, alignment=TA_CENTER)
        ))

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response    
# ── Profile update + avatar upload ───────────────────────────

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Auto-create a UserProfile whenever a new User is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


@method_decorator(csrf_exempt, name="dispatch")
class UpdateProfileView(View):
    """
    GET  /api/auth/profile/          — get current user profile
    POST /api/auth/profile/          — update full_name / bio
    POST /api/auth/profile/avatar/   — upload profile picture (multipart)
    """
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return JsonResponse({"profile": profile.to_dict(),
                             "user": _build_user_dict(request.user)})

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Not authenticated"}, status=401)
        profile, _ = UserProfile.objects.get_or_create(user=request.user)

        # Handle avatar upload — store as base64 in DB (no file system)
        if request.FILES.get("avatar"):
            import base64 as _b64
            f         = request.FILES["avatar"]
            mime_type = f.content_type or "image/jpeg"
            raw_bytes = f.read()
            # Resize to max 256x256 to keep DB size reasonable
            try:
                from PIL import Image
                import io as _io
                img = Image.open(_io.BytesIO(raw_bytes))
                img.thumbnail((256, 256), Image.LANCZOS)
                buf = _io.BytesIO()
                fmt = "JPEG" if "jpeg" in mime_type or "jpg" in mime_type else "PNG"
                img.save(buf, format=fmt, quality=85)
                raw_bytes = buf.getvalue()
                mime_type = "image/jpeg" if fmt == "JPEG" else "image/png"
            except Exception:
                pass   # If Pillow not available, store full image
            b64_str = _b64.b64encode(raw_bytes).decode("utf-8")
            profile.avatar_b64 = f"data:{mime_type};base64,{b64_str}"
            profile.save()
            return JsonResponse({"avatar_url": profile.avatar_url(),
                                 "message": "Avatar updated"})

        # Handle JSON profile update
        try:
            data = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        if "full_name" in data:
            profile.full_name = data["full_name"].strip()
            # Also update Django User first/last name
            parts = profile.full_name.split(" ", 1)
            request.user.first_name = parts[0]
            request.user.last_name  = parts[1] if len(parts) > 1 else ""
            request.user.save(update_fields=["first_name", "last_name"])
        if "bio" in data:
            profile.bio = data["bio"]

        profile.save()
        return JsonResponse({"profile": profile.to_dict(),
                             "user":    _build_user_dict(request.user)})
