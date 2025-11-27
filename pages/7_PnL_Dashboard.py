import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db
import utils

utils.apply_styling()

st.header("Profit & Loss Dashboard")

# Date range selector
col_d1, col_d2 = st.columns(2)
with col_d1:
    start_date = st.date_input("From", datetime.now().replace(day=1))
with col_d2:
    end_date = st.date_input("To", datetime.now())

start_str = start_date.strftime("%Y-%m-%d")
end_str = end_date.strftime("%Y-%m-%d")

conn = utils.get_db_connection()

# 1. SALES
try:
    df_sales = pd.read_sql_query("""
        SELECT IFNULL(SUM(Total), 0) as TotalSales
        FROM DailySales
        WHERE Date BETWEEN ? AND ?
    """, conn, params=(start_str, end_str))
    total_sales = df_sales["TotalSales"].iloc[0] if not df_sales.empty else 0.0
except:
    total_sales = 0.0

# 2. RAW MATERIAL COST (Chicken)
try:
    df_chicken = pd.read_sql_query("""
        SELECT IFNULL(SUM(Qty * VendorRate), 0) as ChickenCost
        FROM BillEntries
        WHERE Date BETWEEN ? AND ?
    """, conn, params=(start_str, end_str))
    chicken_cost = df_chicken["ChickenCost"].iloc[0] if not df_chicken.empty else 0.0
except:
    chicken_cost = 0.0

# 3. OTHER EXPENSES
try:
    df_expenses = pd.read_sql_query("""
        SELECT Category, SUM(Amount) as Total
        FROM Expenses
        WHERE Date BETWEEN ? AND ?
        GROUP BY Category
    """, conn, params=(start_str, end_str))
    total_expenses = df_expenses["Total"].sum() if not df_expenses.empty else 0.0
except:
    total_expenses = 0.0
    df_expenses = pd.DataFrame()

# 4. STAFF COST (Estimated based on attendance)
try:
    df_staff = pd.read_sql_query("""
        SELECT 
            e.Name,
            e.MonthlySalary,
            COUNT(CASE WHEN a.Status = 'Present' THEN 1 END) as PresentDays
        FROM Employees e
        LEFT JOIN Attendance a ON e.EmployeeID = a.EmployeeID AND a.Date BETWEEN ? AND ?
        WHERE e.Status = 'Active'
        GROUP BY e.EmployeeID, e.Name, e.MonthlySalary
    """, conn, params=(start_str, end_str))
    
    # Estimate: (Monthly Salary / 30) * Present Days
    if not df_staff.empty:
        df_staff["EstimatedCost"] = (df_staff["MonthlySalary"] / 30) * df_staff["PresentDays"]
        staff_cost = df_staff["EstimatedCost"].sum()
    else:
        staff_cost = 0.0
except:
    staff_cost = 0.0
    df_staff = pd.DataFrame()

conn.close()

# Calculate P&L
total_cost = chicken_cost + total_expenses + staff_cost
net_profit = total_sales - total_cost
profit_margin = (net_profit / total_sales * 100) if total_sales > 0 else 0

# Display Metrics
st.markdown("### Key Metrics")
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

col_m1.metric("Total Sales", f"₹{total_sales:,.2f}")
col_m2.metric("Total Costs", f"₹{total_cost:,.2f}")
col_m3.metric("Net Profit", f"₹{net_profit:,.2f}", delta=f"{profit_margin:.1f}%")
col_m4.metric("Profit Margin", f"{profit_margin:.1f}%")

# P&L Statement
st.markdown("### Profit & Loss Statement")

pnl_data = {
    "Item": [
        "Sales Revenue",
        "",
        "Cost of Goods Sold:",
        "  - Chicken/Raw Material",
        "  - Other Inventory",
        "",
        "Operating Expenses:",
        "  - Staff Salaries (Est.)",
        "  - Other Expenses",
        "",
        "Total Costs",
        "",
        "Net Profit/(Loss)"
    ],
    "Amount (₹)": [
        f"{total_sales:,.2f}",
        "",
        "",
        f"({chicken_cost:,.2f})",
        f"(0.00)",
        "",
        "",
        f"({staff_cost:,.2f})",
        f"({total_expenses:,.2f})",
        "",
        f"({total_cost:,.2f})",
        "",
        f"{net_profit:,.2f}"
    ]
}

df_pnl = pd.DataFrame(pnl_data)
st.dataframe(df_pnl, hide_index=True, width="stretch")

# Cost Breakdown
st.markdown("### Cost Breakdown")

col_c1, col_c2 = st.columns(2)

with col_c1:
    st.markdown("#### By Category")
    cost_breakdown = pd.DataFrame({
        "Category": ["Chicken/Raw Material", "Staff Salaries", "Other Expenses"],
        "Amount": [chicken_cost, staff_cost, total_expenses]
    })
    cost_breakdown = cost_breakdown[cost_breakdown["Amount"] > 0]
    
    if not cost_breakdown.empty:
        cost_breakdown.set_index("Category", inplace=True)
        st.bar_chart(cost_breakdown)
    else:
        st.info("No cost data available.")

with col_c2:
    st.markdown("#### Expense Details")
    if not df_expenses.empty:
        df_expenses.set_index("Category", inplace=True)
        st.bar_chart(df_expenses)
    else:
        st.info("No expense data available.")

# Sales Trend
st.markdown("### Sales Trend")
conn = utils.get_db_connection()
try:
    df_sales_trend = pd.read_sql_query("""
        SELECT Date, Total as Sales
        FROM DailySales
        WHERE Date BETWEEN ? AND ?
        ORDER BY Date
    """, conn, params=(start_str, end_str))
    
    if not df_sales_trend.empty:
        df_sales_trend["Date"] = pd.to_datetime(df_sales_trend["Date"])
        df_sales_trend.set_index("Date", inplace=True)
        st.line_chart(df_sales_trend)
    else:
        st.info("No sales data available for this period.")
except:
    st.info("No sales data available.")

conn.close()

# Notes
st.markdown("---")
st.markdown("""
**Notes:**
- Staff cost is estimated based on (Monthly Salary ÷ 30) × Present Days
- For accurate salary calculations, use the Salary & Advances module
- Chicken cost includes all items from Bill Entry module
""")
