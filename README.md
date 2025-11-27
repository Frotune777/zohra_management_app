# Chicken Rate & Bill Tracker

## Overview
This application is a desktop tool built with Python and Tkinter for managing chicken rates, vendor details, and daily bill entries. It uses SQLite for data storage.

## Features
- **Daily Rate Entry**: Record market rates for Tandoor, Boiler, and Egg.
- **Bill Entry**: Track daily purchases with automatic variance calculation.
- **Vendor Management**: Manage suppliers and markup rules with data consistency.
- **Dashboard**: Visualize rate trends and vendor dues.
- **Attendance**: Track employee attendance with bulk grid entry.
- **Sales & Expenses**: Record daily sales and expenses with category-wise tracking.
- **P&L Dashboard**: Comprehensive profit & loss analysis.
- **Vendor Management**: Add, update, and delete vendors. Manage markup rules for each vendor.
- **Ledger**: Track payments and view net due balances for vendors.

## Project Structure
- `chicken_app.py`: Main application entry point. Sets up the UI and navigation.
- `chicken_db.py`: Database management module. Handles SQLite connections and schema initialization.
- `bill_entry.py`: Logic for the "Daily Bill Entry" tab.
- `vendor_management.py`: Logic for the "Vendor Management" tab.

## Dependencies
- Python 3.x
- `tkinter` (usually included with Python)
- `pandas`
- `numpy`
- `tkcalendar`

## Project Structure
```
management_app/
├── Home.py                 # Main entry point
├── pages/                  # Multi-page modules
│   ├── 1_Chicken_Rates.py
│   ├── 2_Bill_Entry.py
│   ├── 3_Vendor_Management.py
│   ├── 4_Chicken_Dashboard.py
│   ├── 5_Daily_Sales_Expense.py
│   ├── 6_Attendance.py
│   └── 7_PnL_Dashboard.py
├── utils.py                # Shared utilities
├── chicken_db.py           # Database layer
├── docs/                   # Implementation plans
├── tests/                  # Unit tests
├── venv/                   # Virtual environment
└── chicken_tracker.db      # SQLite database
```

## How to Run
1. Activate virtual environment:
   ```bash
   source venv/bin/activate  # On Linux/Mac
   # or
   venv\Scripts\activate     # On Windows
   ```

2. Run the application:
   ```bash
   streamlit run Home.py
   ```

3. Access the app at `http://localhost:8501`
