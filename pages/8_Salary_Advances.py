import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db
import utils

utils.apply_styling()

st.header("Salary & Advances")

# Create tables
conn = utils.get_db_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS SalaryAdvances (
        ID INTEGER PRIMARY KEY,
        Date TEXT NOT NULL,
        EmployeeID INTEGER NOT NULL,
        Amount REAL NOT NULL,
        Reason TEXT,
        FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID)
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS SalaryPayments (
        ID INTEGER PRIMARY KEY,
        SalaryMonth TEXT NOT NULL,
        EmployeeID INTEGER NOT NULL,
        GrossSalary REAL NOT NULL,
        TotalAdvances REAL NOT NULL,
        NetPayable REAL NOT NULL,
        PaymentDate TEXT,
        Status TEXT DEFAULT 'Pending',
        FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID),
        UNIQUE(SalaryMonth, EmployeeID)
    )
""")

conn.commit()
conn.close()

tab1, tab2, tab3 = st.tabs(["Advance Entry", "Salary Calculation", "Payment History"])

with tab1:
    st.subheader("Record Advance")
    
    conn = utils.get_db_connection()
    df_employees = pd.read_sql_query(
        "SELECT EmployeeID, Name FROM Employees WHERE Status = 'Active'",
        conn
    )
    conn.close()
    
    if df_employees.empty:
        st.warning("No active employees found.")
    else:
        with st.form("advance_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                advance_date = st.date_input("Date", datetime.now(), key="advance_date_input")
                employee_id = st.selectbox(
                    "Employee",
                    options=df_employees["EmployeeID"].tolist(),
                    format_func=lambda x: df_employees[df_employees["EmployeeID"] == x]["Name"].iloc[0]
                )
            
            with col2:
                amount = st.number_input("Amount", min_value=0.0, step=100.0)
                payment_mode = st.selectbox("Payment Mode", ["Cash", "Bank", "UPI"], key="advance_payment_mode")
                reason = st.text_input("Reason")
            
            if st.form_submit_button("Record Advance", type="primary"):
                try:
                    conn = utils.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO SalaryAdvances (Date, EmployeeID, Amount, Reason, PaymentMode)
                        VALUES (?, ?, ?, ?, ?)
                    """, (advance_date.strftime("%Y-%m-%d"), employee_id, amount, reason, payment_mode))
                    conn.commit()
                    conn.close()
                    st.success("Advance recorded successfully!")
                except Exception as e:
                    st.error(f"Error: {e}")
    
    st.markdown("### Recent Advances")
    conn = utils.get_db_connection()
    df_advances_full = pd.read_sql_query("""
        SELECT a.Date, a.EmployeeID, e.Name, a.Amount, a.PaymentMode, a.Reason
        FROM SalaryAdvances a
        JOIN Employees e ON a.EmployeeID = e.EmployeeID
        ORDER BY a.Date DESC
    """, conn)

    if not df_employees.empty:
        # Calculate Running Balance
        advances_agg = df_advances_full.groupby("EmployeeID")['Amount'].sum()
        
        # Fetch recoveries (from SalaryPayments)
        recoveries_df = pd.read_sql_query("SELECT EmployeeID, TotalAdvances FROM SalaryPayments", conn)
        recoveries_agg = recoveries_df.groupby("EmployeeID")['TotalAdvances'].sum()
        
        # Merge for balance
        balance_data = []
        for _, emp in df_employees.iterrows():
            eid = emp['EmployeeID']
            total_adv = advances_agg.get(eid, 0.0)
            total_rec = recoveries_agg.get(eid, 0.0)
            balance = total_adv - total_rec
            balance_data.append({
                "Employee": emp['Name'],
                "Total Taken": f"₹{total_adv:,.2f}",
                "Total Repaid": f"₹{total_rec:,.2f}",
                "Current Balance": f"₹{balance:,.2f}"
            })
        
        st.dataframe(pd.DataFrame(balance_data), hide_index=True, width="stretch")
    else:
        st.info("No active employees to calculate advance balance.")

    st.markdown("### Recent Transactions")
    if not df_advances_full.empty:
        # Display only the relevant columns for recent transactions
        df_recent_transactions = df_advances_full[['Date', 'Name', 'Amount', 'PaymentMode', 'Reason']].head(20)
        st.dataframe(df_recent_transactions, hide_index=True, width="stretch")
    else:
        st.info("No advances recorded yet.")
    conn.close()

with tab2:
    st.subheader("Calculate Salary")
    
    # Month selector
    salary_month = st.date_input("Salary Month", datetime.now().replace(day=1), key="salary_calc_month")
    month_str = salary_month.strftime("%Y-%m")
    
    # Calculate button
    if st.button("Calculate Salaries", type="primary"):
        conn = utils.get_db_connection()
        cursor = conn.cursor()
        
        # Get all active employees
        cursor.execute("SELECT EmployeeID, Name, MonthlySalary FROM Employees WHERE Status = 'Active'")
        employees = cursor.fetchall()
        
        salary_data = []
        
        for emp_id, emp_name, monthly_salary in employees:
            # Get attendance for the month
            start_date = salary_month.strftime("%Y-%m-01")
            end_date = (salary_month.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            end_date_str = end_date.strftime("%Y-%m-%d")
            
            cursor.execute("""
                SELECT COUNT(*) FROM Attendance
                WHERE EmployeeID = ? AND Date BETWEEN ? AND ? AND Status = 'Present'
            """, (emp_id, start_date, end_date_str))
            present_days = cursor.fetchone()[0]
            
            # Calculate gross salary (per day rate * present days)
            per_day_rate = monthly_salary / 30
            gross_salary = per_day_rate * present_days
            
            # Get advances for the month
            cursor.execute("""
                SELECT IFNULL(SUM(Amount), 0) FROM SalaryAdvances
                WHERE EmployeeID = ? AND Date BETWEEN ? AND ?
            """, (emp_id, start_date, end_date_str))
            total_advances = cursor.fetchone()[0]
            
            # Net payable
            net_payable = gross_salary - total_advances
            
            # Payment date (28 days after month end)
            payment_date = end_date + timedelta(days=28)
            
            salary_data.append({
                "Employee": emp_name,
                "Present Days": present_days,
                "Gross Salary": f"₹{gross_salary:,.2f}",
                "Advances": f"₹{total_advances:,.2f}",
                "Net Payable": f"₹{net_payable:,.2f}",
                "Payment Due": payment_date.strftime("%Y-%m-%d")
            })
            
            # Save to database
            try:
                cursor.execute("""
                    INSERT INTO SalaryPayments (SalaryMonth, EmployeeID, GrossSalary, TotalAdvances, NetPayable, PaymentDate, Status)
                    VALUES (?, ?, ?, ?, ?, ?, 'Pending')
                    ON CONFLICT(SalaryMonth, EmployeeID) DO UPDATE SET
                        GrossSalary=excluded.GrossSalary,
                        TotalAdvances=excluded.TotalAdvances,
                        NetPayable=excluded.NetPayable,
                        PaymentDate=excluded.PaymentDate
                """, (month_str, emp_id, gross_salary, total_advances, net_payable, payment_date.strftime("%Y-%m-%d")))
            except Exception as e:
                st.error(f"Error saving salary for {emp_name}: {e}")
        
        conn.commit()
        conn.close()
        
        if salary_data:
            st.success(f"Salaries calculated for {month_str}")
            df_salary = pd.DataFrame(salary_data)
            st.dataframe(df_salary, hide_index=True, width="stretch")
            
            st.info(f"**Note**: Salaries will be paid 28 days after month end as per company policy.")
        else:
            st.warning("No active employees found.")

with tab3:
    st.subheader("Payment History")
    
    conn = utils.get_db_connection()
    df_history = pd.read_sql_query("""
        SELECT 
            sp.SalaryMonth,
            e.Name,
            sp.GrossSalary,
            sp.TotalAdvances,
            sp.NetPayable,
            sp.PaymentDate,
            sp.Status
        FROM SalaryPayments sp
        JOIN Employees e ON sp.EmployeeID = e.EmployeeID
        ORDER BY sp.SalaryMonth DESC, e.Name
    """, conn)
    conn.close()
    
    if not df_history.empty:
        # Format currency columns
        df_history["GrossSalary"] = df_history["GrossSalary"].apply(lambda x: f"₹{x:,.2f}")
        df_history["TotalAdvances"] = df_history["TotalAdvances"].apply(lambda x: f"₹{x:,.2f}")
        df_history["NetPayable"] = df_history["NetPayable"].apply(lambda x: f"₹{x:,.2f}")
        
        st.dataframe(df_history, hide_index=True, width="stretch")
        
        # Mark as paid functionality
        st.markdown("### Mark Salary as Paid")
        col_p1, col_p2, col_p3 = st.columns(3)
        
        with col_p1:
            month_to_mark = st.selectbox("Month", df_history["SalaryMonth"].unique())
        with col_p2:
            emp_to_mark = st.selectbox("Employee", df_history[df_history["SalaryMonth"] == month_to_mark]["Name"].unique())
        
        if st.button("Mark as Paid"):
            try:
                conn = utils.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE SalaryPayments
                    SET Status = 'Paid'
                    WHERE SalaryMonth = ? AND EmployeeID = (
                        SELECT EmployeeID FROM Employees WHERE Name = ?
                    )
                """, (month_to_mark, emp_to_mark))
                conn.commit()
                conn.close()
                st.success(f"Marked {emp_to_mark}'s salary for {month_to_mark} as Paid!")
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.info("No salary payments recorded yet.")
