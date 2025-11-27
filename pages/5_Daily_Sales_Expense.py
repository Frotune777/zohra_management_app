import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db
import utils

utils.apply_styling()

st.header("Daily Sales & Expenses")

# Date selector
selected_date = st.date_input("Select Date", datetime.now())
date_str = selected_date.strftime("%Y-%m-%d")

tab1, tab2, tab3 = st.tabs(["Sales Entry", "Expense Entry", "Summary"])

with tab1:
    st.subheader("Daily Sales")
    
    conn = utils.get_db_connection()
    cursor = conn.cursor()
    
    # Check if sales table exists, create if not
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS DailySales (
            ID INTEGER PRIMARY KEY,
            Date TEXT NOT NULL,
            DineIn REAL DEFAULT 0,
            Takeaway REAL DEFAULT 0,
            Online REAL DEFAULT 0,
            Total REAL DEFAULT 0,
            UNIQUE(Date)
        )
    """)
    conn.commit()
    
    # Load existing sales
    cursor.execute("SELECT DineIn, Takeaway, Online FROM DailySales WHERE Date = ?", (date_str,))
    existing_sales = cursor.fetchone()
    conn.close()
    
    dinein_val = existing_sales[0] if existing_sales else 0.0
    takeaway_val = existing_sales[1] if existing_sales else 0.0
    online_val = existing_sales[2] if existing_sales else 0.0
    
    with st.form("sales_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            dinein = st.number_input("Dine-In Sales", min_value=0.0, value=dinein_val, step=100.0)
        with col2:
            takeaway = st.number_input("Takeaway Sales", min_value=0.0, value=takeaway_val, step=100.0)
        with col3:
            online = st.number_input("Online Sales", min_value=0.0, value=online_val, step=100.0)
        
        total = dinein + takeaway + online
        st.metric("Total Sales", f"₹{total:,.2f}")
        
        if st.form_submit_button("Save Sales", type="primary"):
            try:
                conn = utils.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO DailySales (Date, DineIn, Takeaway, Online, Total)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(Date) DO UPDATE SET 
                        DineIn=excluded.DineIn, 
                        Takeaway=excluded.Takeaway, 
                        Online=excluded.Online, 
                        Total=excluded.Total
                """, (date_str, dinein, takeaway, online, total))
                conn.commit()
                conn.close()
                st.success(f"Sales for {date_str} saved successfully!")
            except Exception as e:
                st.error(f"Error saving sales: {e}")

with tab2:
    st.subheader("Daily Expenses")
    
    conn = utils.get_db_connection()
    cursor = conn.cursor()
    
    # Create expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Expenses (
            ID INTEGER PRIMARY KEY,
            Date TEXT NOT NULL,
            Category TEXT NOT NULL,
            Amount REAL NOT NULL,
            Description TEXT,
            PaymentMode TEXT
        )
    """)
    conn.commit()
    
    # Load existing expenses for the date
    df_expenses = pd.read_sql_query(
        "SELECT ID, Category, Amount, Description, PaymentMode FROM Expenses WHERE Date = ?",
        conn,
        params=(date_str,)
    )
    conn.close()
    
    # If no data, create template
    if df_expenses.empty:
        df_expenses = pd.DataFrame({
            "ID": [None] * 5,
            "Category": ["", "", "", "", ""],
            "Amount": [0.0] * 5,
            "Description": ["", "", "", "", ""],
            "PaymentMode": ["Cash"] * 5
        })
    
    st.markdown("### Enter Expenses (Grid)")
    edited_expenses = st.data_editor(
        df_expenses,
        column_config={
            "ID": st.column_config.NumberColumn(disabled=True),
            "Category": st.column_config.SelectboxColumn(
                options=["Rent", "Electricity", "Gas", "Salaries", "Raw Material", "Repairs", "Misc", "Other"],
                required=True
            ),
            "Amount": st.column_config.NumberColumn(min_value=0.0, step=10.0, format="₹%.2f"),
            "Description": st.column_config.TextColumn(),
            "PaymentMode": st.column_config.SelectboxColumn(options=["Cash", "Bank Transfer", "UPI", "Card"])
        },
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key="expense_editor"
    )
    
    total_expenses = edited_expenses["Amount"].sum()
    st.metric("Total Expenses", f"₹{total_expenses:,.2f}")
    
    if st.button("Save Expenses", type="primary"):
        try:
            conn = utils.get_db_connection()
            cursor = conn.cursor()
            
            # Delete existing for this date
            cursor.execute("DELETE FROM Expenses WHERE Date = ?", (date_str,))
            
            # Insert new entries
            entries = []
            for _, row in edited_expenses.iterrows():
                if row["Category"] and row["Amount"] > 0:
                    entries.append((
                        date_str,
                        row["Category"],
                        row["Amount"],
                        row["Description"],
                        row["PaymentMode"]
                    ))
            
            if entries:
                cursor.executemany("""
                    INSERT INTO Expenses (Date, Category, Amount, Description, PaymentMode)
                    VALUES (?, ?, ?, ?, ?)
                """, entries)
                conn.commit()
                st.success(f"Expenses for {date_str} saved successfully!")
            else:
                st.warning("No valid expenses to save.")
            
            conn.close()
        except Exception as e:
            st.error(f"Error saving expenses: {e}")

with tab3:
    st.subheader("Summary")
    
    # Date range selector
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("From", datetime.now().replace(day=1))
    with col_d2:
        end_date = st.date_input("To", datetime.now())
    
    start_str = start_date.strftime("%Y-%m-%d")
    end_str = end_date.strftime("%Y-%m-%d")
    
    conn = utils.get_db_connection()
    
    # Sales summary
    df_sales = pd.read_sql_query("""
        SELECT Date, DineIn, Takeaway, Online, Total
        FROM DailySales
        WHERE Date BETWEEN ? AND ?
        ORDER BY Date DESC
    """, conn, params=(start_str, end_str))
    
    # Expense summary
    df_exp_summary = pd.read_sql_query("""
        SELECT Date, Category, SUM(Amount) as Total
        FROM Expenses
        WHERE Date BETWEEN ? AND ?
        GROUP BY Date, Category
        ORDER BY Date DESC
    """, conn, params=(start_str, end_str))
    
    conn.close()
    
    col_s1, col_s2 = st.columns(2)
    
    with col_s1:
        st.markdown("#### Sales")
        if not df_sales.empty:
            st.dataframe(df_sales, hide_index=True, width="stretch")
            st.metric("Total Sales", f"₹{df_sales['Total'].sum():,.2f}")
        else:
            st.info("No sales data for this period.")
    
    with col_s2:
        st.markdown("#### Expenses")
        if not df_exp_summary.empty:
            st.dataframe(df_exp_summary, hide_index=True, width="stretch")
            st.metric("Total Expenses", f"₹{df_exp_summary['Total'].sum():,.2f}")
        else:
            st.info("No expense data for this period.")
