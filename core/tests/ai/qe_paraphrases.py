"""Paraphrase corpus for the query-engine router: >=30 phrasings per capability (en + ar)."""

TODAY_NOTE = "months are explicit or relative so results do not depend on today's date"

EXPENSES = [
    "total expenses for Sept 2026", "how much did I spend in September 2026", "what were my expenses in Sep 2026",
    "my spending for 2026-09", "expenses this month", "how much have I spent last month", "show me my expenses for June 2026",
    "what did I spend in Aug 2026?", "total spent in Jul 2026", "expense total for 09/2026",
    "give me the total expenses from Jun to Sept 2026", "expenses between June and September 2026", "how much did I spend from June 2026 to August 2026",
    "expenses by category for Sept 2026", "spending per category in August 2026", "category breakdown of my expenses in Jul 2026",
    "daily expenses for Sept 2026", "expenses per day in August 2026", "day by day spending for Jun 2026",
    "expenses by month for 2026", "monthly spending from Jan to Sept 2026", "how much did I spend each month in 2026",
    "detailed expenses table for Jun 2026 and Jul 2026", "list my transactions for Sept 2026", "itemized expenses Aug 2026",
    "my last expense", "what is my latest expense", "show the last 5 expenses", "most recent purchase I made",
    "biggest expense in Sept 2026", "top 3 expenses in August 2026", "average monthly expenses for 2026",
    "how much did I spend in the last 3 months", "expenses in 2026", "what was my spending last year",
    "كم صرفت في سبتمبر 2026", "مصروفات شهر يونيو 2026", "اجمالي المصروفات لشهر اغسطس 2026", "مصروفات الشهر ده",
    "المصاريف من يونيو حتى سبتمبر 2026", "مصروفات حسب الفئة في سبتمبر 2026", "مصروفات يومية لشهر يوليو 2026", "اخر مصروف", "كم انفقت الشهر الماضي",
]
SALARY = [
    "What was my paid salary for January 2026?", "salary in jan 2026", "How much was my salary in March 2025?", "my salary for Sept 2026",
    "paid salary 2026-09", "what was my paid salary last month", "What is my latest paid salary?", "last salary", "most recent salary I received",
    "how much did I get paid in June 2026", "what did my payslip say for Aug 2026", "my paycheck for July 2026", "take-home pay in Sep 2026",
    "salary for Jun to Sept 2026", "salaries between June and September 2026", "total salary for 2026", "how much did I earn in 2026 in salary",
    "average monthly salary in 2026", "expected salary for March 2026", "bonus in Dec 2025", "my bonuses for 2025",
    "salary by company for 2026", "salary per month in 2026", "wages for May 2026", "what was my pay in April 2026",
    "how much salary did I receive in Feb 2026", "latest salary paid", "last paycheck", "current salary", "salary table for Jan to Mar 2026",
    "ما هو راتبي في يناير 2026", "كم كان مرتبي في مارس 2026", "راتب شهر سبتمبر 2026", "اخر راتب", "اخر راتب استلمته",
    "اجمالي الراتب لعام 2026", "رواتب من يناير حتى مارس 2026", "راتبي الشهر الماضي", "متوسط الراتب الشهري 2026", "مكافأة ديسمبر 2025",
]
BALANCE = [
    "what is my balance", "how much money do I have", "total balance", "my total liquid balance", "how much do I have in my accounts",
    "what's in my bank accounts", "show my account balances", "balances by currency", "balance per bank", "list all my accounts",
    "how much cash do I have", "my balance in USD", "how much USD do I have", "balance in euros", "what is my current balance",
    "total funds across all banks", "bank balance summary", "balance by account type",
    "show balances for each account", "what are my balances", "how much is in my wallet", "my liquid cash total", "account balance",
    "how much money is in my accounts right now", "cash balance", "what do I have in the bank", "total of all my accounts",
    "how many accounts do I have and total balance", "balances per currency",
    "كم رصيدي", "ما هو رصيدي الحالي", "اجمالي الارصده", "كم عندي في الحسابات", "رصيدي بالدولار", "الارصدة حسب العملة", "ارصدة البنوك",
    "معايا كام في الحساب", "اعرض كل الحسابات", "كم فلوسي",
]
CERTIFICATES = [
    "my certificates", "how many certificates do I have", "total certificates principal", "certificate summary", "list my certificates",
    "when is my next certificate interest", "next interest payout on my certificates", "which certificate matures first", "certificate maturity dates",
    "when does my certificate expire", "how much monthly interest do my certificates pay", "total interest from certificates", "my fixed deposits",
    "show all bank certificates", "what is the average interest rate of my certificates", "certificates expiring soon", "details of my certificates",
    "how much is invested in certificates", "certificate principal", "my deposit certificates", "next certificate interest date", "certificate interest income",
    "what certificates do I hold", "active certificates", "bank certificates overview", "when will my certificate mature", "nearest certificate maturity",
    "upcoming certificate interest", "how much do I have in certificates", "time deposits total",
    "شهاداتي", "كم عدد الشهادات", "اجمالي الشهادات", "موعد العايد القادم للشهادات", "متى تستحق الشهادة", "قائمة شهاداتي", "ودائعي في البنك",
]
FIXED_ASSETS = [
    "what are my fixed assets", "total fixed assets", "value of my assets", "how much are my assets worth", "list my assets",
    "my real estate value", "how many assets do I own", "assets by type", "asset allocation", "show my properties", "total value of my property",
    "my fixed assets summary", "what assets do I have", "breakdown of my assets by type", "how much is my villa worth", "value of my apartments",
    "my vehicles value", "show all fixed assets", "asset class allocation", "total assets value", "what is my car worth",
    "fixed assets list", "my land value", "assets total", "how much do my fixed assets add up to", "real estate holdings",
    "what do I own in assets", "value of all my assets", "fixed asset breakdown", "my assets",
    "ما هي اصولي الثابتة", "اجمالي الاصول", "قيمة عقاراتي", "كم عدد الاصول", "اصولي حسب النوع", "قيمة الشقه", "توزيع الاصول",
]
GOLD = [
    "what is the gold price today for 24k?", "gold price today", "current gold price", "price of 21k gold", "gold 18k price per gram",
    "how much is a gram of 24 karat gold", "gold rate today", "24k gold buy price", "21k gold sell price", "what's the gold price for 18 karat",
    "gold prices by karat", "price of gold per gram", "gold price now", "what is 21k gold worth per gram", "22k gold price",
    "latest gold price", "gold buying price 21k", "gold selling price 24k", "how much does a gram of 18k cost", "gold ounce price",
    "price of gold today 21k", "today's gold rate 24k", "karat 21 price", "gold 24k", "what is the price of gold", "gold price per gram 21 karat",
    "current price of 24 carat gold", "what is gold trading at per gram", "give me all gold prices", "gold quote today",
    "سعر الذهب اليوم", "سعر جرام الذهب عيار 21", "كم سعر الذهب عيار 24", "اسعار الذهب", "سعر بيع الذهب عيار 18", "سعر شراء الذهب عيار 21", "سعر الذهب النهارده",
]
FX = [
    "what is the USD exchange rate", "dollar rate today", "USD to EGP rate", "exchange rates", "how much is 1 USD", "euro exchange rate",
    "what is the EUR rate", "current exchange rates", "SAR exchange rate", "USD buy rate", "USD sell rate", "dollar buy price", "price of the dollar today",
    "GBP rate", "AED to EGP", "how much is the dollar today", "show me currency rates", "forex rates today", "exchange rate for dollars",
    "what's the dollar rate", "euro rate today", "usd price", "what is the rate of the riyal", "kwd exchange rate", "all exchange rates",
    "currency exchange rates now", "the dollar exchange rate now", "eur to usd rate", "latest usd rate", "fx rates",
    "سعر الدولار", "سعر الدولار اليوم", "كام الدولار", "سعر اليورو", "اسعار الصرف", "سعر الريال السعودي", "سعر الصرف الان", "اسعار العملات",
]
GOLD_HOLDINGS = [
    "how much gold do I have", "how much gold do I hold", "how much gold do I own", "my gold holdings", "gold holdings",
    "how many grams of gold do I have", "how many grams of gold do I own", "what is my gold worth", "how much is my gold worth",
    "my gold", "show my gold", "gold I own", "gold I hold", "total gold I have", "how much gold do I have in my balances",
    "what gold do I hold", "my gold weight", "gold grams I have", "value of the gold I own", "how much gold do I have in grams",
    "do I own any gold", "what is the total weight of my gold", "my gold portfolio", "how many grams do I own in gold", "how much gold is in my accounts",
    "what is the value of my gold holdings", "gold I have in grams", "tell me how much gold I hold", "my gold grams and value", "total gold holdings",
    "كم عندي ذهب", "كم معي ذهب", "كم املك من ذهب", "ذهبي", "مقتنيات الذهب", "جرامات الذهب عندي", "كم جرام ذهب معي",
]
BUDGETS = [
    "show my budgets", "what is my budget status", "how are my budgets doing", "budget status", "list my budgets", "my budgets this month",
    "how much of my budget have I used", "how much of my food budget is left", "what is left in my budget", "remaining budget",
    "how much is left in my groceries budget", "budget remaining for transport", "am I over budget", "which budgets am I over",
    "did I exceed any budget", "have I overspent my budget", "which budget is close to its limit", "any budget at risk",
    "budgets that are over the limit", "is my entertainment budget exceeded", "percent of my budget used", "how much budget do I have left this month",
    "what are my spending limits", "show my spending limit status", "weekly budget status", "monthly budgets overview", "yearly budget status",
    "my budget for dining out", "budget left for shopping", "what is my total budget",
    "ما هي ميزانيتي", "حالة الميزانيات", "كم تبقى من ميزانيتي", "هل تجاوزت ميزانيتي", "ميزانياتي هذا الشهر", "المتبقي من ميزانية الطعام",
    "اعرض ميزانياتي", "اي ميزانية تجاوزت الحد", "ميزانيات قريبة من الحد", "كم استخدمت من ميزانية المواصلات",
]
RECURRING = [
    "show my recurring transactions", "list my recurring payments", "what are my recurring bills", "my subscriptions", "list my subscriptions",
    "what subscriptions do I have", "upcoming subscriptions", "next recurring payment", "which recurring bills are due soon", "recurring expenses due this month",
    "what bills are coming up", "upcoming bills", "when is my next scheduled payment", "show scheduled payments", "my autopay list",
    "how much do my subscriptions cost per month", "total of my recurring expenses", "monthly total of recurring payments", "how much am I committed to each month in recurring bills",
    "what is the total cost of my subscriptions", "my standing orders", "my direct debits", "fixed monthly bills", "regular payments I have",
    "show my recurring items", "recurring expenses", "what recurring payments are due", "due bills this month", "next bills due", "all my repeating payments",
    "اشتراكاتي", "ما هي اشتراكاتي", "المدفوعات المتكررة", "المعاملات المتكررة", "فواتير قادمة", "اشتراكاتي القادمة",
    "كم تكلفني اشتراكاتي شهريا", "اجمالي المصروفات المتكررة", "التزاماتي الشهرية", "اعرض المصروفات المتكررة",
]
CORPUS = {"expenses": EXPENSES, "salary": SALARY, "balance": BALANCE, "certificates": CERTIFICATES,
          "fixed_assets": FIXED_ASSETS, "gold_holdings": GOLD_HOLDINGS, "gold_price": GOLD, "exchange_rates": FX,
          "budgets": BUDGETS, "recurring": RECURRING}

# Must NOT be answered by the engine (advice / why / compare / forecast / actions / not data).
FALL_THROUGH = [
    "why are my expenses so high in Sept 2026", "compare my spending in Aug 2026 and Sept 2026", "how can I reduce my expenses",
    "should I buy gold now", "is it a good time to invest in certificates", "forecast my balance next year", "what if I lose my job",
    "advise me on my salary raise", "explain my net worth", "add an expense of 50 for lunch", "delete my last expense", "transfer 500 to savings",
    "hello", "thanks", "what can you do", "how does the app work", "why is the dollar rising", "recommend how to save money",
    "compare my salary Jan 2026 and Feb 2026", "لماذا ارتفعت مصروفاتي في سبتمبر 2026", "قارن مصروفات اغسطس وسبتمبر 2026", "كيف اوفر فلوسي", "هل اشتري ذهب الان",
    "what is the meaning of life", "write me a poem about gold",
    "how should I budget my salary", "how can I stay within my budget", "should I increase my food budget", "recommend a budget for next year",
    "set a budget of 500 for food", "delete my entertainment budget", "why did I go over budget in Sept 2026", "كيف اضع ميزانية لراتبي", "هل يجب ان ازيد ميزانيتي",
    "should I cancel my subscriptions", "how can I reduce my recurring bills", "add a recurring payment for rent",
]
