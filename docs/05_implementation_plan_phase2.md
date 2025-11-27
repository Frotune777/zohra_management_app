# Implementation Plan - Phase 2: Multi-Page & New Modules

## Goal Description
Refactor the application into a multi-page Streamlit app and integrate new modules for Attendance, Salary, Sales, and P&L.

## User Review Required
> [!IMPORTANT]
> This is a major architectural change. The app will be split into multiple files.

## Proposed Changes

### Step 1: Multi-Page Refactor ✅ COMPLETED
- [NEW] Created `Home.py` (entry point)
- [NEW] Created `pages/` directory
- [NEW] Created `pages/1_Chicken_Rates.py`
- [NEW] Created `pages/2_Bill_Entry.py`
- [NEW] Created `pages/3_Vendor_Management.py`
- [NEW] Created `pages/4_Chicken_Dashboard.py`
- [NEW] Created `utils.py` for shared functions

### Step 2: Attendance Module (NEXT)
- [NEW] `pages/5_Attendance.py`
- [MODIFY] `chicken_db.py` to add `Employees` and `Attendance` tables
- [UI] Employee Master (Add/Edit Employees)
- [UI] Daily Attendance Entry (Grid view)

### Step 3: Salary & Advances
- [NEW] `pages/6_Salary_and_Advances.py`
- [MODIFY] DB to add `SalaryAdvances` and `SalaryPayments` tables
- [UI] Advance Entry form
- [UI] Salary Calculation (28-day rule)

### Step 4: Daily Sales & Expenses
- [NEW] `pages/7_Daily_Sales_Expense.py`
- [MODIFY] DB to add `DailySales` and `Expenses` tables
- [UI] Sales Entry form
- [UI] Expense Entry grid

### Step 5: P&L Dashboard
- [NEW] `pages/8_PnL_Dashboard.py`
- [UI] Aggregate view of Sales - (Chicken Cost + Staff Cost + Expenses)

## Verification Plan
- Verify each page loads correctly
- Check navigation between pages
- Verify data persistence in new modules
