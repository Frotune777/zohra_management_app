# PROJECT CONTEXT - Zohra Restaurant Management System

> **Purpose**: This file provides complete project context for LLMs to understand the entire system architecture, codebase, and functionality.

---

## 🎯 Project Overview

**Name**: Zohra Restaurant Management System  
**Type**: Web Application (Streamlit-based)  
**Purpose**: Comprehensive restaurant management covering chicken procurement, vendor management, employee operations, and financial tracking  
**Tech Stack**: Python, Streamlit, SQLite, Pandas  
**Database**: SQLite (chicken_tracker.db)  

---

## 📁 Complete File Structure

```
management_app/
├── Home.py                          # Main entry point with tab navigation
├── chicken_db.py                    # Core database layer (11 functions)
├── utils.py                         # Utilities (DB connection, styling)
├── pages/                           # 8 feature modules
│   ├── 1_Chicken_Rates.py          # Daily market rate entry
│   ├── 2_Bill_Entry.py             # Purchase recording with variance
│   ├── 3_Vendor_Management.py      # Vendor CRUD + markup rules
│   ├── 4_Chicken_Dashboard.py      # Rate trends visualization
│   ├── 5_Daily_Sales_Expense.py    # Sales & expense tracking
│   ├── 6_Attendance.py             # Employee attendance
│   ├── 7_PnL_Dashboard.py          # Profit & Loss analysis
│   └── 8_Salary_Advances.py        # Salary calculation (28-day rule)
├── tests/                           # 26 unit tests (100% pass)
│   ├── test_chicken_db.py          # Database operations (18 tests)
│   ├── test_utils.py               # Utilities (2 tests)
│   ├── test_business_logic.py      # Integration (3 tests)
│   ├── test_vendor_flow.py         # Vendor workflows (2 tests)
│   └── run_tests.py                # Test runner
├── docs/                            # Documentation
│   ├── INDEX.md                    # Documentation hub
│   ├── API_REFERENCE.md            # Complete API docs
│   ├── DEVELOPER_GUIDE.md          # Development handbook
│   └── [5 implementation plans]
├── .streamlit/                      # Streamlit config
├── chicken_tracker.db               # SQLite database
├── requirements.txt                 # Dependencies
├── README.md                        # Main documentation
└── CHANGELOG.md                     # Version history
```

---

## 📌 SINGLE SOURCE OF TRUTH – CRITICAL BUSINESS RULES

**These are non-negotiable rules that MUST NOT be broken when coding:**

1. **Markup Rules**: Must support 0–2 chained operations (Op1, Val1, Op2, Val2). Never add Op3.

2. **BillEntries Uniqueness**: Must remain unique on `(Date, SupplierName, ItemName)`. No duplicates allowed.

3. **Attendance Uniqueness**: Must remain unique on `(Date, EmployeeID)`. One record per employee per day.

4. **Salary Payment Rule**: Must always follow the 28-day payment delay rule (payment_date = month_end + 28 days). No shortcuts.

5. **Vendor Rename**: Must be transactional across ALL these tables: `Suppliers`, `Markups`, `BillEntries`, `VendorLedger`. Partial updates will corrupt data.

6. **Vendor Delete**: Must cascade in this exact order: `VendorLedger` → `BillEntries` → `Markups` → `Suppliers`. Wrong order will cause foreign key violations.

7. **Rate Calculation**: Must use the formula: `base_rate Op1 Val1 Op2 Val2` (if Op2 exists). Never skip operations or change order.

8. **Currency**: Always INR (₹). No multi-currency support.

9. **Month Length**: Default 30 days for salary calculations unless specified otherwise.

10. **Transaction Integrity**: All multi-table updates must use database transactions with rollback on error.

---

## 🚫 DO NOT CHANGE (Assumptions)

**These are fixed business assumptions. Do not "optimize" these:**

- Currency is always **INR (₹)**
- Default month length in salary calculation is **30 days**
- Raw material P&L currently considers **only chicken**; other items can be added later but must not break existing flows
- Payment delay (**28 days**) is a fixed business rule, not a configurable parameter
- Variance threshold for "High" status is a business decision, not a technical one
- Markup operators are limited to: `+`, `-`, `*`, `/` (no other operators)

---

## 🗄️ Database Schema (11 Tables)

### Core Chicken Management

**Suppliers** - Vendor master data
- SupplierID (PK), SupplierName (UK), VendorType, MarkupRequired, etc.

**Markups** - Pricing rules per vendor/item
- ItemID (PK), SupplierName (FK), ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2
- Supports chained operations: e.g., TandoorRate + 10 * 1.1

**RawData** - Daily market rates
- Date (PK), TandoorRate, BoilerRate, EggRate

**BillEntries** - Purchase transactions
- ID (PK), Date, SupplierName (FK), ItemName, Qty, VendorRate, ExpectedRate, Variance, Status
- Unique: (Date, SupplierName, ItemName)

**VendorLedger** - Financial transactions
- ID (PK), Date, SupplierName (FK), TransactionType, Amount, Details

### Employee Management

**Employees** - Employee master
- EmployeeID (PK), Name, Role, MonthlySalary, Status

**Attendance** - Daily attendance
- ID (PK), Date, EmployeeID (FK), Status, OTHours, Remarks
- Unique: (Date, EmployeeID)

**SalaryAdvances** - Salary advances
- ID (PK), Date, EmployeeID (FK), Amount, Reason

**SalaryPayments** - Monthly salary records
- ID (PK), SalaryMonth, EmployeeID (FK), GrossSalary, TotalAdvances, NetPayable, PaymentDate, Status
- Unique: (SalaryMonth, EmployeeID)

### Financial Tracking

**DailySales** - Daily sales by channel
- ID (PK), Date (UK), DineIn, Takeaway, Online, Total

**Expenses** - Categorized expenses
- ID (PK), Date, Category, Amount, Description, PaymentMode

---

## 🔄 Key Data Flows

### 1. Bill Entry Workflow
```
User selects vendor → Fetch items & markup rules → Fetch market rates → 
Calculate expected rates → User enters quantities & vendor rates → 
Calculate variance → Save to BillEntries → Update VendorLedger
```

**Variance Calculation**:
```python
expected_rate = calculate_expected_rate(raw_rates, markup_rule)
variance = vendor_rate - expected_rate
status = 'High' if abs(variance) > threshold else 'Okay'
```

### 2. Rate Calculation Logic
```python
# Example: Boneless chicken
raw_rates = (100, 90, 80)  # Tandoor, Boiler, Egg
rule = ('TandoorRate', '+', 95, None, None)
# Calculation: 100 + 95 = 195

# Example: With chained operations
rule = ('TandoorRate', '+', 10, '*', 1.1)
# Calculation: (100 + 10) * 1.1 = 121
```

### 3. Salary Calculation
```
Fetch active employees → Count present days → Sum advances → 
Calculate: gross_salary - advances = net_payable → 
Payment date = month_end + 28 days → Save to SalaryPayments
```

### 4. P&L Calculation
```
Total Sales = SUM(DailySales.Total)
Chicken Cost = SUM(BillEntries.Qty * VendorRate)
Other Expenses = SUM(Expenses.Amount)
Staff Cost = SUM((MonthlySalary / 30) * PresentDays)
Net Profit = Total Sales - (Chicken Cost + Other Expenses + Staff Cost)
```

---

## 🔧 Core Functions (chicken_db.py)

### Database Initialization
- `initialize_db()` - Creates all tables, handles migrations

### Vendor Operations
- `fetch_suppliers_and_items()` → (list, dict)
- `fetch_vendor_type(vendor_name)` → str | None
- `rename_vendor(old_name, new_name)` → bool (transactional, updates 4 tables)
- `delete_vendor_and_cleanup(id, name)` → bool (cascading delete)
- `insert_default_markups(vendor, rules)` → bool
- `fetch_items_for_supplier(vendor)` → list

### Rate Calculations
- `fetch_rate_and_rule(date, vendor, item)` → (raw_rates, rule)
- `calculate_expected_rate(raw_rates, rule)` → float
  - Supports operators: +, -, *, /
  - Handles chained operations
  - Returns rounded to 2 decimals

### Data Retrieval
- `fetch_rate_history(limit=30)` → list[tuple]
- `fetch_vendor_dues()` → dict {vendor: due_amount}

---

## 📄 Module Descriptions

### Home.py
- Entry point with horizontal tab navigation
- Loads pages dynamically using `exec()`
- Custom CSS for dark theme

### 1_Chicken_Rates.py
- Form for daily rate entry (Tandoor, Boiler, Egg)
- Loads existing rates for editing
- Saves to RawData table

### 2_Bill_Entry.py
- Vendor selection
- Grid-based item entry
- Auto-calculates expected rates and variance
- Flags high-variance items
- Updates BillEntries and VendorLedger

### 3_Vendor_Management.py
- Vendor CRUD operations
- Markup rule management (grid editor)
- Vendor ledger view
- Payment recording
- Due calculation

### 4_Chicken_Dashboard.py
- Rate history line chart
- Vendor dues bar chart
- Summary metrics

### 5_Daily_Sales_Expense.py
- Sales entry (3 channels: Dine-in, Takeaway, Online)
- Expense entry (grid-based, categorized)
- Summary view with date range filtering

### 6_Attendance.py
- Daily attendance grid (all employees)
- Employee master management
- Attendance reports

### 7_PnL_Dashboard.py
- Revenue calculation
- Cost breakdown (Chicken, Staff, Other)
- Profit calculation
- Visualizations (charts, trends)

### 8_Salary_Advances.py
- Advance recording
- Salary calculation (with 28-day delay)
- Payment history
- Mark as paid functionality

---

## 🧪 Testing

**Test Coverage**: 26 tests, 100% pass rate

**Test Files**:
- `test_chicken_db.py` - 18 tests (DB operations, vendor ops, rate calculations)
- `test_utils.py` - 2 tests (DB connection)
- `test_business_logic.py` - 3 tests (bill entry, ledger)
- `test_vendor_flow.py` - 2 tests (vendor lifecycle)

**Run Tests**:
```bash
python tests/run_tests.py
```

---

## 🎨 UI/UX Patterns

### Form Pattern
```python
with st.form("form_name"):
    field1 = st.text_input("Label")
    submitted = st.form_submit_button("Submit")
    if submitted:
        # Validation and save
```

### Data Editor Pattern
```python
df = pd.read_sql_query("SELECT * FROM Table", conn)
edited_df = st.data_editor(df, num_rows="dynamic")
if st.button("Save"):
    # Save edited_df to database
```

### Styling
- Custom CSS in `utils.apply_styling()`
- Inter font family
- Red accent color (#ef4444)
- Dark theme optimized

---

## 🔑 Key Business Rules

1. **Markup Rules**: Support chained operations (Op1, Op2)
2. **Variance Tracking**: Flag when |vendor_rate - expected_rate| > threshold
3. **Salary Payment**: 28-day delay after month end
4. **Attendance**: Unique constraint on (Date, EmployeeID)
5. **Bill Entries**: Unique constraint on (Date, SupplierName, ItemName)
6. **Vendor Rename**: Transactional update across 4 tables
7. **Vendor Delete**: Cascading delete (Ledger → Bills → Markups → Supplier)

---

## 🚀 Running the Application

```bash
# Setup
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt

# Initialize DB
python -c "import chicken_db; chicken_db.initialize_db()"

# Run
streamlit run Home.py

# Access at http://localhost:8501
```

---

## 📦 Dependencies

```
streamlit
pandas
numpy
```

---

## 🏗️ Architecture Layers

1. **UI Layer**: Streamlit pages (Home.py + 8 page modules)
2. **Business Logic**: chicken_db.py (database operations)
3. **Utilities**: utils.py (shared functions)
4. **Data Layer**: SQLite database (11 tables)

---

## 🔍 Common Operations

### Add New Vendor
```python
# In Vendor Management page
conn = utils.get_db_connection()
cursor = conn.cursor()
cursor.execute("INSERT INTO Suppliers (SupplierName, VendorType) VALUES (?, ?)", 
               (name, vendor_type))
conn.commit()
conn.close()
```

### Calculate Expected Rate
```python
raw_rates, rule = chicken_db.fetch_rate_and_rule(date, vendor, item)
expected = chicken_db.calculate_expected_rate(raw_rates, rule)
```

### Record Bill Entry
```python
cursor.execute("""
    INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (date, vendor, item, qty, vendor_rate, expected_rate, variance, status))

cursor.execute("""
    INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount)
    VALUES (?, ?, ?, ?)
""", (date, vendor, 'Bill', total_amount))
```

---

## 📚 Documentation Files

- **README.md** - Complete system documentation with diagrams
- **docs/API_REFERENCE.md** - Full API documentation
- **docs/DEVELOPER_GUIDE.md** - Development handbook
- **docs/INDEX.md** - Documentation navigation

---

## 🎯 Key Features Summary

✅ Daily chicken rate tracking  
✅ Automated variance calculation  
✅ Vendor management with markup rules  
✅ Bill entry with ledger integration  
✅ Employee attendance tracking  
✅ Salary calculation with 28-day rule  
✅ Sales & expense tracking  
✅ P&L dashboard with visualizations  
✅ Comprehensive testing (26 tests)  
✅ Complete documentation  

---

## 🧠 FOR LLMs – How to Use This Context

**When asked about:**

- **Rates / Bills** → Reason using `RawData`, `Markups`, `BillEntries`, `VendorLedger` tables
- **Vendors** → Use `Suppliers`, `Markups`, `VendorLedger` tables
- **Salary / Attendance** → Use `Employees`, `Attendance`, `SalaryAdvances`, `SalaryPayments` tables
- **P&L** → Aggregate from `DailySales`, `Expenses`, `BillEntries`, `Employees` tables

**Critical Rules for LLMs:**

1. **Never invent new tables or fields** – Always stay within the defined schema
2. **Respect all constraints** listed under "Critical Business Rules"
3. **Use transactions** for multi-table updates
4. **Follow calculation formulas** exactly as documented
5. **Maintain data integrity** – check foreign keys and unique constraints

**When generating code:**
- Use `chicken_db.py` functions instead of direct SQL when available
- Always close database connections
- Handle errors with try/except blocks
- Use `utils.get_db_connection()` for consistency

---

## 🔍 FAQ Mapping – Where to Look in Code

**Q: How is expected chicken rate calculated?**  
→ `chicken_db.calculate_expected_rate()` + `Markups` table logic

**Q: How do we compute vendor dues?**  
→ `VendorLedger` table + `chicken_db.fetch_vendor_dues()` function

**Q: How is salary for a given month calculated?**  
→ `Attendance`, `SalaryAdvances`, `SalaryPayments` tables + logic in `pages/8_Salary_Advances.py`

**Q: How is Net Profit computed in P&L?**  
→ See "P&L Calculation" section + logic in `pages/7_PnL_Dashboard.py`

**Q: How does variance tracking work?**  
→ `variance = vendor_rate - expected_rate` in `pages/2_Bill_Entry.py`

**Q: How to add a new vendor?**  
→ Insert into `Suppliers` table via `pages/3_Vendor_Management.py`

**Q: How to rename a vendor safely?**  
→ Use `chicken_db.rename_vendor()` which handles all 4 tables transactionally

**Q: Where are daily rates stored?**  
→ `RawData` table, entered via `pages/1_Chicken_Rates.py`

**Q: How to record a payment to vendor?**  
→ Insert into `VendorLedger` with `TransactionType='Payment'` and negative `Amount`

**Q: What happens when an employee is deleted?**  
→ Currently no cascade delete for employees (should be added if needed)

---

## 🧪 Test Expectations

**If you change:**

| Change | Update These Tests |
|--------|-------------------|
| **DB Schema** | `initialize_db()` in `chicken_db.py` + corresponding tests in `test_chicken_db.py` |
| **Salary Rules** | Tests in `test_business_logic.py` related to salary & P&L calculations |
| **Markup Logic** | `test_chicken_db.py::test_calculate_expected_rate_*` (all rate calculation tests) |
| **Vendor Operations** | `test_chicken_db.py::TestVendorOperations` + `test_vendor_flow.py` |
| **Bill Entry Logic** | `test_business_logic.py::TestBillEntryWorkflow` |
| **Database Functions** | Corresponding test in `test_chicken_db.py` |

**Breaking Changes Look Like:**
- Schema changes without updating `initialize_db()`
- Changing function signatures without updating tests
- Modifying calculation formulas without updating expected values in tests
- Adding new constraints without testing them

**Test Coverage Goals:**
- Minimum: 70% code coverage
- Target: 85% code coverage
- Critical paths (DB operations, calculations): 100% coverage

---

## 📄 Module Descriptions with Extension Guidelines

### Home.py
- Entry point with horizontal tab navigation
- Loads pages dynamically using `exec()`
- Custom CSS for dark theme

**Extension Guidelines:**
- **New pages**: Add to `pages/` directory, update tab list and exec() calls
- **Navigation changes**: Modify tab definitions in `st.tabs()`
- **Global styling**: Update CSS in markdown block or `utils.apply_styling()`

### 1_Chicken_Rates.py
- Form for daily rate entry (Tandoor, Boiler, Egg)
- Loads existing rates for editing
- Saves to RawData table

**Extension Guidelines:**
- **New rate types**: Add column to `RawData` table, update form and save logic
- **Validation rules**: Add in form submission block
- **Rate history**: Modify `chicken_db.fetch_rate_history()` query

### 2_Bill_Entry.py
- Vendor selection
- Grid-based item entry
- Auto-calculates expected rates and variance
- Flags high-variance items
- Updates BillEntries and VendorLedger

**Extension Guidelines:**
- **New variance thresholds**: Modify status calculation logic
- **Additional fields**: Add columns to `BillEntries` table and update insert query
- **Bulk import**: Add CSV upload feature before grid display

### 3_Vendor_Management.py
- Vendor CRUD operations
- Markup rule management (grid editor)
- Vendor ledger view
- Payment recording
- Due calculation

**Extension Guidelines:**
- **New vendor fields**: Add columns to `Suppliers` table, update form and save logic
- **New markup fields**: Add columns to `Markups` table, update grid config
- **Payment methods**: Add to `PreferredPaymentType` options
- **Ledger filters**: Add date range or transaction type filters

### 4_Chicken_Dashboard.py
- Rate history line chart
- Vendor dues bar chart
- Summary metrics

**Extension Guidelines:**
- **New charts**: Add using `st.line_chart()`, `st.bar_chart()`, or plotly
- **Date range filters**: Add date inputs and modify queries
- **Export features**: Add download buttons for chart data

### 5_Daily_Sales_Expense.py
- Sales entry (3 channels: Dine-in, Takeaway, Online)
- Expense entry (grid-based, categorized)
- Summary view with date range filtering

**Extension Guidelines:**
- **New sales channels**: Add columns to `DailySales` table and update P&L aggregation in `pages/7_PnL_Dashboard.py`
- **New expense categories**: No DB change needed; use free-text `Category` or define controlled list in SelectboxColumn config
- **Payment tracking**: Add payment mode analysis charts

### 6_Attendance.py
- Daily attendance grid (all employees)
- Employee master management
- Attendance reports

**Extension Guidelines:**
- **New attendance statuses**: Add to SelectboxColumn options (e.g., "Half Day", "Sick Leave")
- **Shift management**: Add `Shift` column to `Attendance` table
- **Leave balance**: Create new `LeaveBalance` table and tracking logic

### 7_PnL_Dashboard.py
- Revenue calculation
- Cost breakdown (Chicken, Staff, Other)
- Profit calculation
- Visualizations (charts, trends)

**Extension Guidelines:**
- **P&L formula changes**: Update calculation logic in main query section
- **New cost categories**: Add to cost breakdown DataFrame and chart
- **Comparison periods**: Add year-over-year or month-over-month comparison
- **Export to Excel**: Add `df.to_excel()` functionality

### 8_Salary_Advances.py
- Advance recording
- Salary calculation (with 28-day delay)
- Payment history
- Mark as paid functionality

**Extension Guidelines:**
- **Salary formula changes**: Modify calculation in "Calculate Salaries" button handler
- **Deduction types**: Add new deduction tables (e.g., `Loans`, `Penalties`)
- **Payment delay rule**: If changing 28-day rule, update `payment_date` calculation AND update tests
- **Bonus/Incentives**: Add `Bonuses` table and include in gross salary calculation

---

## 💡 Understanding the Project

**For LLMs**: This project is a complete restaurant management system with:
- **8 interconnected modules** for different business functions
- **11 database tables** with proper relationships
- **Complex business logic** (rate calculations, variance tracking, salary rules)
- **Clean architecture** (separation of UI, business logic, data)
- **Production-ready** with tests and documentation

**Key Complexity Areas**:
1. **Rate Calculation**: Dynamic markup rules with chained operations
2. **Variance Tracking**: Comparing vendor rates against calculated expected rates
3. **Salary Calculation**: 28-day payment delay with advance deductions
4. **P&L Calculation**: Aggregating data from multiple sources

**Code Quality**:
- Modular design
- Comprehensive testing
- Detailed documentation
- Error handling
- Transaction management for data integrity

---

## 🔗 Quick Reference

- **Entry Point**: `Home.py`
- **Database Layer**: `chicken_db.py`
- **Database File**: `chicken_tracker.db`
- **Test Suite**: `tests/run_tests.py`
- **Main Docs**: `README.md`
- **API Docs**: `docs/API_REFERENCE.md`

---

**Last Updated**: 2025-11-28  
**Version**: 2.0  
**Status**: Production Ready
