import json
import os

manifest_path = 'docs/generated/manifest.json'
content_path = 'doc_engine/content/page_descriptions.json'

with open(manifest_path, 'r', encoding='utf-8') as f:
    manifest = json.load(f)

with open(content_path, 'r', encoding='utf-8') as f:
    content = json.load(f)

def get_custom_content(route, tab, nested_tab, modal):
    purpose = 'Provides tools and information.'
    steps = ['Navigate to the section.', 'Review information.']
    
    if route == 'auth':
        if tab == 'login':
            purpose = 'Authenticate into your WealthFlow account securely.'
            steps = ['Enter your email address.', 'Enter your secure password.', 'Click Login to access your dashboard.']
        elif tab == 'create_account':
            purpose = 'Register a new WealthFlow account to begin tracking your wealth.'
            steps = ['Fill in your personal details.', 'Create a secure password.', 'Submit the form to create your account.']
        elif tab == 'forgot_password':
            purpose = 'Recover access to your account if you forgot your password.'
            steps = ['Enter your registered email address.', 'Check your inbox for a reset link.', 'Follow the link to create a new password.']
            
    elif route == 'dashboard':
        purpose = 'Provides a comprehensive, real-time overview of your net worth, recent transactions, and financial health.'
        steps = ['Log in to WealthFlow.', 'Review the top-level KPI widgets for Net Worth and Cash Flow.', 'Analyze the charts to understand your financial trends.']
        if modal == 'user_profile':
            purpose = 'Manage your personal profile, avatar, and individual user settings.'
            steps = ['Click on your avatar in the top right corner.', 'Update your personal details or upload a new profile picture.', 'Save your changes.']
            
    elif route == 'financial-advisor':
        if tab == 'overview':
            purpose = 'Get AI-driven insights summarizing your entire financial standing and immediate action items.'
            steps = ['Navigate to the Financial Advisor Overview tab.', 'Read the AI-generated summary of your wealth.', 'Review the top recommendations for immediate action.']
        elif tab == 'cash-flow':
            purpose = 'Analyze your historical and current cash flow metrics, comparing income against expenses.'
            steps = ['Select the Cash Flow tab.', 'Adjust the time period filter.', 'Analyze income versus expense breakdowns.']
        elif tab == 'wealth-growth':
            purpose = 'Track the historical growth of your net worth and investment portfolio over time.'
            steps = ['Select the Wealth Growth tab.', 'Review your net worth trajectory.', 'Identify periods of high growth or decline.']
        elif tab == 'portfolio':
            purpose = 'Review your asset allocation and portfolio diversification across different asset classes.'
            steps = ['Navigate to the Portfolio tab.', 'Review the pie chart showing asset distribution.', 'Identify any over-concentrated asset classes.']
        elif tab == 'goal-planning':
            purpose = 'Set, track, and manage your long-term financial goals and milestones.'
            steps = ['Navigate to Goal Planning.', 'Create a new financial goal.', 'Track your progress towards the target amount.']
        elif tab == 'risk-analysis':
            purpose = 'Evaluate your exposure to market risks, currency fluctuations, and liquidity constraints.'
            steps = ['Open the Risk Analysis tab.', 'Review the AI risk score.', 'Read the mitigation strategies provided by the advisor.']
        elif tab == 'spending-intelligence':
            purpose = 'Gain deep insights into your spending habits, identifying unnecessary subscriptions or high-expense categories.'
            steps = ['Navigate to Spending Intelligence.', 'Review the breakdown of discretionary vs mandatory spending.', 'Identify areas to cut costs.']
        elif tab == 'opportunity-detection':
            purpose = 'Discover personalized investment opportunities and strategies to optimize your idle cash.'
            steps = ['Open Opportunity Detection.', 'Review the systems suggestions for high-yield savings or asset purchases.', 'Assess the projected ROI for each opportunity.']
        elif tab == 'market-intelligence':
            purpose = 'Stay updated with real-time market trends, inflation rates, and macroeconomic indicators affecting your wealth.'
            steps = ['Navigate to Market Intelligence.', 'Review current economic indicators.', 'Understand how they impact your specific asset classes.']
        elif tab == 'ai-financial-advisor':
            purpose = 'Interact directly with the AI financial advisor via a conversational interface to ask specific financial questions.'
            steps = ['Open the AI Financial Advisor tab.', 'Type your specific financial question in the chat box.', 'Review the tailored advice provided by the AI.']
        elif tab == 'what-if-simulator':
            purpose = 'Simulate various financial scenarios to see their impact on your net worth.'
            steps = ['Navigate to the What-If Simulator.', 'Adjust the sliders to model different economic or personal scenarios.', 'Review the projected impact on your long-term wealth.']

    elif str(route).startswith('salary-'):
        purpose = 'Manage your income streams, salary structures, and employment benefits.'
        steps = ['Navigate to the Salary section.', 'Review your base salary, allowances, and deductions.', 'Track your net income over time.']
        if modal == 'add_salary_entry':
            purpose = 'Record a new monthly salary payout or income entry.'
            steps = ['Click Add Entry.', 'Enter the exact payout amount and date.', 'Save the entry to update your cash flow.']
        elif 'perdiem' in str(modal):
            purpose = 'Manage your per diem allowances and daily travel compensations.'
            steps = ['Open the Per Diem modal.', 'Enter your travel dates and daily rates.', 'Save the allowance to your income sheet.']

    elif route == 'all-companies':
        purpose = 'Manage the list of employers, businesses, or organizations associated with your income streams.'
        steps = ['Navigate to All Companies.', 'Review the list of active companies.', 'Click on a company to edit its details.']
        if modal == 'add_company':
            purpose = 'Register a new company or employer to the system.'
            steps = ['Click Add Company.', 'Enter the company name, industry, and contact details.', 'Save the company profile.']

    elif route == 'balance':
        if tab == 'overview':
            purpose = 'View a consolidated summary of all your bank accounts, liquid cash, and total balances.'
            steps = ['Navigate to Balance > Overview.', 'Review the total liquid wealth.', 'Analyze the distribution of funds across different banks.']
        elif tab == 'accounts':
            purpose = 'Manage individual bank accounts, view their balances, and track their transaction histories.'
            steps = ['Navigate to the Accounts tab.', 'Select a specific bank account.', 'Review its current balance and recent activity.']
            if modal == 'add_balance':
                purpose = 'Manually adjust or record a new balance entry for a specific bank account.'
                steps = ['Click Add Balance.', 'Select the account and enter the new balance amount.', 'Save to update your records.']
        elif tab == 'transfers':
            purpose = 'Track and manage internal fund transfers between your own bank accounts.'
            steps = ['Navigate to the Transfers tab.', 'Review the history of internal movements.', 'Verify the status of pending transfers.']
            if modal == 'add_transfer':
                purpose = 'Record a new internal transfer of funds from one account to another.'
                steps = ['Click Add Transfer.', 'Select the source account and destination account.', 'Enter the amount and date, then save.']
        elif tab == 'allocation':
            purpose = 'Analyze how your liquid cash is allocated across different currencies or regions.'
            steps = ['Navigate to the Allocation tab.', 'Review the currency breakdown charts.', 'Ensure your cash is sufficiently diversified.']
        elif tab == 'forecasts':
            purpose = 'Project your future bank balances based on expected income and recurring expenses.'
            steps = ['Navigate to the Forecasts tab.', 'Review the projected cash flow graph.', 'Identify any potential future liquidity shortages.']
        elif tab == 'recommendations':
            purpose = 'Receive AI suggestions on optimizing your cash holdings, such as moving idle funds to high-yield accounts.'
            steps = ['Navigate to Recommendations.', 'Review the AI suggestions for cash optimization.', 'Execute the recommended transfers if desired.']

    elif route == 'bank-certificates':
        purpose = 'Track and manage your fixed-term bank deposit certificates and bonds.'
        steps = ['Navigate to Bank Certificates.', 'Review your active and matured certificates.', 'Track the accrued interest and maturity dates.']
        if modal == 'add_certificate':
            purpose = 'Register a new fixed-term bank certificate into your portfolio.'
            steps = ['Click Add Certificate.', 'Enter the principal amount, interest rate, and maturity date.', 'Save the certificate details.']
        elif modal == 'interest_history':
            purpose = 'View the historical interest payouts received from a specific certificate.'
            steps = ['Click on Interest History for a certificate.', 'Review the schedule of payouts.', 'Verify that the amounts match your bank statements.']

    elif route == 'fixed-assets':
        if tab == 'dashboard':
            purpose = 'View a high-level summary of all your illiquid fixed assets, including real estate and gold.'
            steps = ['Navigate to Fixed Assets > Dashboard.', 'Review the total valuation of your physical assets.', 'Analyze the breakdown by asset class.']
        elif tab == 'analytic':
            purpose = 'Perform deep analytics on the performance, depreciation, and appreciation of your fixed assets.'
            steps = ['Navigate to the Analytic tab.', 'Review the ROI and valuation charts.', 'Compare the performance of different asset categories.']
        elif tab == 'reports':
            purpose = 'Generate comprehensive PDF or Excel reports detailing your fixed asset portfolio.'
            steps = ['Navigate to the Reports tab.', 'Select the desired reporting period and asset classes.', 'Click Generate to download the report.']
        elif tab == 'assets':
            purpose = 'Manage the detailed profiles of your individual fixed assets (Real Estate, Gold, Vehicles, etc.).'
            steps = ['Navigate to the Assets tab.', 'Browse your list of assets.', 'Click on an asset to view or edit its detailed profile.']
            
            if nested_tab == 'general':
                purpose = 'View or edit the primary general information (name, type, purchase date) of the asset.'
                steps = ['Navigate to the General sub-tab.', 'Update the assets core details.', 'Save your changes.']
            elif nested_tab == 'gold_details' or nested_tab == 'asset-core':
                purpose = 'Manage specific characteristics of a gold asset, such as purity (karat), weight, and maker.'
                steps = ['Navigate to the Gold Details sub-tab.', 'Enter the exact weight in grams and karat purity.', 'Save the details to ensure accurate live valuation.']
            elif nested_tab == 'photos':
                purpose = 'Upload and manage visual evidence and photos of the physical asset.'
                steps = ['Navigate to the Photos sub-tab.', 'Click Upload to add new images.', 'Set a primary cover image for the asset.']
            elif nested_tab == 'documents_title':
                purpose = 'Store and manage legal documents, title deeds, and purchase receipts for the asset.'
                steps = ['Navigate to the Documents sub-tab.', 'Upload PDF or image copies of legal deeds.', 'Securely save the records.']
            elif nested_tab == 'sale':
                purpose = 'Record the sale or disposal of the asset, calculating the final realized profit or loss.'
                steps = ['Navigate to the Sale sub-tab.', 'Enter the sale date and final sale price.', 'Confirm the disposal to remove it from active valuation.']
            elif nested_tab == 'property':
                purpose = 'Manage real-estate specific details such as property type, address, area size, and zoning.'
                steps = ['Navigate to the Property sub-tab.', 'Enter the square footage and physical address.', 'Save the property specifics.']
            elif nested_tab == 'renovations':
                purpose = 'Track the costs of any renovations or improvements made to the property, which add to its cost basis.'
                steps = ['Navigate to the Renovations sub-tab.', 'Add a new renovation entry with its cost and date.', 'Save to update the assets total capital invested.']
            elif nested_tab == 'acquisition_costs':
                purpose = 'Record the supplementary costs of acquiring the asset, such as broker fees, taxes, and legal fees.'
                steps = ['Navigate to the Acquisition Costs sub-tab.', 'Enter any fees incurred during purchase.', 'Save to accurately calculate your true cost basis.']
            elif nested_tab == 'furniture':
                purpose = 'Inventory the furniture and appliances included within a real estate property.'
                steps = ['Navigate to the Furniture sub-tab.', 'List the items and their estimated values.', 'Save the inventory.']
            elif nested_tab == 'mortgage':
                purpose = 'Track the financing and mortgage details attached to this specific property.'
                steps = ['Navigate to the Mortgage sub-tab.', 'Enter the loan amount, interest rate, and term.', 'Track your remaining principal balance.']
            elif nested_tab == 'rental':
                purpose = 'Manage the rental income, tenant details, and lease agreements for an investment property.'
                steps = ['Navigate to the Rental sub-tab.', 'Enter the active lease details and monthly rent.', 'Track the generated yield.']
            elif nested_tab == 'valuation_history':
                purpose = 'Track the historical market appraisals and manual valuations of the asset over time.'
                steps = ['Navigate to Valuation History.', 'Add a new manual valuation entry based on current market rates.', 'Save to update your current net worth.']

    elif route == 'exchange-rates':
        purpose = 'Monitor live global currency exchange rates and track historical forex trends.'
        steps = ['Navigate to Exchange Rates.', 'Review the live currency pairs.', 'Use the charts to analyze historical exchange rate movements.']

    elif route == 'gold-price':
        purpose = 'Monitor live global gold prices per ounce/gram and track historical commodity trends.'
        steps = ['Navigate to Gold Price.', 'Review the live market rate for gold.', 'Analyze the historical price charts to inform your buying/selling decisions.']

    elif route == 'expenses':
        purpose = 'Track your day-to-day spending and manage your personal or business expenses.'
        steps = ['Navigate to Expenses.', 'Review your recent expense entries.', 'Analyze your spending via the summary charts.']
        if modal == 'edit_add_expenses':
            purpose = 'Record a new expense or modify an existing transaction.'
            steps = ['Click Add Expense.', 'Enter the amount, date, payee, and select a category.', 'Save the transaction.']

    elif route == 'expense-categories':
        purpose = 'Manage the taxonomy of your spending by creating and organizing expense categories.'
        steps = ['Navigate to Expense Categories.', 'Review your active list of categories.', 'Reorganize or edit categories as needed.']
        if modal == 'add_category':
            purpose = 'Create a new top-level expense category.'
            steps = ['Click Add Category.', 'Provide a name and select an icon/color.', 'Save the new category.']
        elif modal == 'add_subcategory':
            purpose = 'Create a nested subcategory for more granular expense tracking.'
            steps = ['Click Add Subcategory under a parent.', 'Provide a name and assign it to the parent category.', 'Save the subcategory.']

    elif str(route).startswith('settings'):
        title_str = str(tab or route).replace("-", " ").title()
        purpose = f'Configure the administrative settings and preferences for {title_str}.'
        steps = ['Navigate to the Settings panel.', 'Adjust the system preferences as needed.', 'Save the configuration to apply changes globally.']

    return purpose, steps

for p in manifest.get('pages', []):
    keys = [p.get('route')]
    if p.get('tab_id'): keys.append(p.get('tab_id'))
    if p.get('nested_tab_id'): keys.append(p.get('nested_tab_id'))
    if p.get('modal_id'): keys.append(p.get('modal_id'))
    
    stable_key = '::'.join(filter(None, keys))
    
    route = p.get('route')
    tab = p.get('tab_id')
    nested_tab = p.get('nested_tab_id')
    modal = p.get('modal_id')
    
    purpose, steps = get_custom_content(route, tab, nested_tab, modal)
    
    content[stable_key] = {
        'purpose': purpose,
        'steps': steps
    }

with open(content_path, 'w', encoding='utf-8') as f:
    json.dump(content, f, indent=4)
    f.write('\n')
