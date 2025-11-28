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
selected_date = st.date_input("Select Date", datetime.now(), key="sales_entry_date")
date_str = selected_date.strftime("%Y-%m-%d")

tab1, tab2, tab3, tab4 = st.tabs(["Sales Entry", "Expense Entry", "Summary", "Cash Closing"])

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
            CashAmount REAL DEFAULT 0,
            UPIAmount REAL DEFAULT 0,
            CardAmount REAL DEFAULT 0,
            UNIQUE(Date)
        )
    """)
    conn.commit()
    
    # Load existing data
    existing = pd.read_sql_query("SELECT * FROM DailySales WHERE Date = ?", conn, params=(date_str,))
    conn.close()
    
    default_dine = 0.0
    default_takeaway = 0.0
    default_online = 0.0
    default_cash = 0.0
    default_upi = 0.0
    default_card = 0.0
    
    if not existing.empty:
        default_dine = existing.iloc[0]['DineIn']
        default_takeaway = existing.iloc[0]['Takeaway']
        default_online = existing.iloc[0]['Online']
        # Handle new columns if they exist in dataframe, else 0.0
        if 'CashAmount' in existing.columns: default_cash = existing.iloc[0]['CashAmount']
        if 'UPIAmount' in existing.columns: default_upi = existing.iloc[0]['UPIAmount']
        if 'CardAmount' in existing.columns: default_card = existing.iloc[0]['CardAmount']
    
    with st.form("sales_form"):
        col1, col2 = st.columns(2) # Changed to 2 columns
        
        with col1:
            st.markdown("### By Channel") # Added sub-heading
            dine_in = st.number_input("Dine-In Sales", min_value=0.0, value=default_dine, step=100.0) # Renamed variable
            takeaway = st.number_input("Takeaway Sales", min_value=0.0, value=default_takeaway, step=100.0) # Renamed variable
            online = st.number_input("Online Sales", min_value=0.0, value=default_online, step=100.0) # Renamed variable
            
        with col2:
            st.markdown("### By Payment Mode") # Added sub-heading
            cash_amt = st.number_input("Cash Amount", min_value=0.0, value=default_cash, step=100.0)
            upi_amt = st.number_input("UPI Amount", min_value=0.0, value=default_upi, step=100.0)
            card_amt = st.number_input("Card Amount", min_value=0.0, value=default_card, step=100.0)
        
        total_channel = dine_in + takeaway + online
        total_mode = cash_amt + upi_amt + card_amt
        
        st.markdown("---")
        c1, c2 = st.columns(2)
        c1.metric("Total (Channels)", f"₹{total_channel:,.2f}")
        c2.metric("Total (Modes)", f"₹{total_mode:,.2f}", delta=total_mode-total_channel, delta_color="off")
        
        if st.form_submit_button("Save Sales", type="primary"):
            if abs(total_channel - total_mode) > 1.0: # Allow small float diff for validation
                st.error(f"Mismatch! Channels: {total_channel}, Modes: {total_mode}. Difference: {total_channel - total_mode}")
            else:
                conn = utils.get_db_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute("""
                        INSERT INTO DailySales (Date, DineIn, Takeaway, Online, Total, CashAmount, UPIAmount, CardAmount)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(Date) DO UPDATE SET
                            DineIn=excluded.DineIn,
                            Takeaway=excluded.Takeaway,
                            Online=excluded.Online,
                            Total=excluded.Total,
                            CashAmount=excluded.CashAmount,
                            UPIAmount=excluded.UPIAmount,
                            CardAmount=excluded.CardAmount
                    """, (date_str, dine_in, takeaway, online, total_channel, cash_amt, upi_amt, card_amt))
                    conn.commit()
                    st.success("Sales saved successfully!")
                except Exception as e:
                    st.error(f"Error saving sales: {e}")
                finally:
                    conn.close()

# --- TAB 2: EXPENSE ENTRY ---
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
    expenses_df = pd.read_sql_query( # Renamed df_expenses to expenses_df
        "SELECT ID, Category, Amount, Description, PaymentMode FROM Expenses WHERE Date = ?",
        conn,
        params=(date_str,)
    )
    
    # If no data, create template (removed old template logic, data_editor handles new rows)
    
    st.markdown("### Enter Expenses (Grid)")
    edited_expenses = st.data_editor(
        expenses_df, # Used expenses_df
        column_config={
            "ID": st.column_config.NumberColumn(disabled=True),
            "Category": st.column_config.SelectboxColumn(
                "Category", # Changed label
                options=["Inventory", "Staff", "Utilities", "Maintenance", "Marketing", "Other"], # Updated options
                required=True
            ),
            "Amount": st.column_config.NumberColumn("Amount", min_value=0, step=10.0, format="₹%d"), # Changed format
            "Description": st.column_config.TextColumn(),
            "PaymentMode": st.column_config.SelectboxColumn(
                "Payment Mode", # Changed label
                options=["Cash", "Bank", "UPI"], # Updated options
                required=True,
                default="Cash" # Added default
            )
        },
        num_rows="dynamic",
        hide_index=True,
        width="stretch",
        key="expense_editor"
    )
    
    total_expenses = edited_expenses["Amount"].sum()
    st.metric("Total Expenses", f"₹{total_expenses:,.2f}")
    
    if st.button("Save Expenses", type="primary"): # Changed button label
        try:
            # conn = utils.get_db_connection() # Connection already open
            # cursor = conn.cursor() # Cursor already open
            
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
                        row.get("Description", ""),
                        row.get("PaymentMode", "Cash")
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
        start_date = st.date_input("From", datetime.now().replace(day=1), key="sales_report_start")
    with col_d2:
        end_date = st.date_input("To", datetime.now(), key="sales_report_end")
    
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

# --- TAB 4: CASH CLOSING ---
with tab4:
    st.subheader("Daily Cash Closing")
    
    from datetime import timedelta
    
    conn = utils.get_db_connection()
    cursor = conn.cursor()
    
    # Ensure CashClosing table exists (already created in chicken_db.initialize_db())
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS CashClosing (
            Date TEXT PRIMARY KEY,
            OpeningCash REAL DEFAULT 0,
            TotalCashIn REAL DEFAULT 0,
            TotalCashOut REAL DEFAULT 0,
            ExpectedClosing REAL DEFAULT 0,
            ActualClosing REAL DEFAULT 0,
            Difference REAL DEFAULT 0,
            Remarks TEXT
        )
    """)
    conn.commit()
    
    # Get Opening Cash (from previous day's ActualClosing)
    prev_date = (selected_date - timedelta(days=1)).strftime("%Y-%m-%d")
    cursor.execute("SELECT ActualClosing FROM CashClosing WHERE Date = ?", (prev_date,))
    prev_result = cursor.fetchone()
    opening_cash = prev_result[0] if prev_result else 0.0
    
    # Calculate Cash In (from DailySales.CashAmount)
    cursor.execute("SELECT IFNULL(CashAmount, 0) FROM DailySales WHERE Date = ?", (date_str,))
    sales_result = cursor.fetchone()
    cash_in = sales_result[0] if sales_result else 0.0
    
    # Calculate Cash Out
    # 1. Expenses with PaymentMode='Cash'
    cursor.execute("SELECT IFNULL(SUM(Amount), 0) FROM Expenses WHERE Date = ? AND PaymentMode = 'Cash'", (date_str,))
    expense_cash = cursor.fetchone()[0]
    
    # 2. Vendor Payments with PaymentMode='Cash' (Amount is negative in ledger, so we negate it)
    cursor.execute("""
        SELECT IFNULL(SUM(ABS(Amount)), 0) FROM VendorLedger 
        WHERE Date = ? AND TransactionType = 'Payment' AND PaymentMode = 'Cash'
    """, (date_str,))
    vendor_cash = cursor.fetchone()[0]
    
    # 3. Salary Advances with PaymentMode='Cash'
    cursor.execute("SELECT IFNULL(SUM(Amount), 0) FROM SalaryAdvances WHERE Date = ? AND PaymentMode = 'Cash'", (date_str,))
    advance_cash = cursor.fetchone()[0]
    
    cash_out = expense_cash + vendor_cash + advance_cash
    
    # Expected Closing
    expected_closing = opening_cash + cash_in - cash_out
    
    # Load existing closing data if any
    cursor.execute("SELECT ActualClosing, Remarks FROM CashClosing WHERE Date = ?", (date_str,))
    existing = cursor.fetchone()
    default_actual = existing[0] if existing else expected_closing
    default_remarks = existing[1] if existing else ""
    
    # Display Summary
    st.markdown("### Cash Flow Summary")
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    col_c1.metric("Opening Cash", f"₹{opening_cash:,.2f}")
    col_c2.metric("Cash In (Sales)", f"₹{cash_in:,.2f}")
    col_c3.metric("Cash Out", f"₹{cash_out:,.2f}")
    col_c4.metric("Expected Closing", f"₹{expected_closing:,.2f}")
    
    # Breakdown of Cash Out
    with st.expander("Cash Out Breakdown"):
        st.write(f"**Expenses (Cash):** ₹{expense_cash:,.2f}")
        st.write(f"**Vendor Payments (Cash):** ₹{vendor_cash:,.2f}")
        st.write(f"**Salary Advances (Cash):** ₹{advance_cash:,.2f}")
    
    # Closing Entry Form
    st.markdown("### Record Closing")
    with st.form("cash_closing_form"):
        actual_closing = st.number_input("Actual Cash in Hand", value=float(default_actual), step=100.0)
        remarks = st.text_area("Remarks (if any discrepancy)", value=default_remarks)
        
        difference = actual_closing - expected_closing
        
        if difference != 0:
            st.warning(f"**Discrepancy Detected:** ₹{abs(difference):,.2f} {'Excess' if difference > 0 else 'Shortage'}")
        
        if st.form_submit_button("Save Closing", type="primary"):
            try:
                cursor.execute("""
                    INSERT INTO CashClosing (Date, OpeningCash, TotalCashIn, TotalCashOut, ExpectedClosing, ActualClosing, Difference, Remarks)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(Date) DO UPDATE SET
                        OpeningCash=excluded.OpeningCash,
                        TotalCashIn=excluded.TotalCashIn,
                        TotalCashOut=excluded.TotalCashOut,
                        ExpectedClosing=excluded.ExpectedClosing,
                        ActualClosing=excluded.ActualClosing,
                        Difference=excluded.Difference,
                        Remarks=excluded.Remarks
                """, (date_str, opening_cash, cash_in, cash_out, expected_closing, actual_closing, difference, remarks))
                conn.commit()
                st.success("Cash closing saved successfully!")
            except Exception as e:
                st.error(f"Error saving closing: {e}")
    
    # Historical Closings
    st.markdown("### Recent Closings")
    df_closings = pd.read_sql_query("""
        SELECT Date, OpeningCash, TotalCashIn, TotalCashOut, ExpectedClosing, ActualClosing, Difference, Remarks
        FROM CashClosing
        ORDER BY Date DESC
        LIMIT 10
    """, conn)
    
    if not df_closings.empty:
        # Format currency columns
        for col in ['OpeningCash', 'TotalCashIn', 'TotalCashOut', 'ExpectedClosing', 'ActualClosing', 'Difference']:
            df_closings[col] = df_closings[col].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(df_closings, hide_index=True, width="stretch")
    else:
        st.info("No closing records yet.")
    
    conn.close()
