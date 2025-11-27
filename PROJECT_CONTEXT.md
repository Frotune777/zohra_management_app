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
