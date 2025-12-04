import streamlit as st
import pandas as pd
import chicken_db
import sqlite3
from datetime import datetime

# Default rules for new Chicken vendors
DEFAULT_CHICKEN_MARKUP_RULES = [
    ('Tandoori', 'TandoorRate', '+', 20.0, None, None),
    ('Boiler', 'BoilerRate', '+', 25.0, None, None),
    ('Egg', 'EggRate', '/', 10.0, '+', 5.0),
    ('Spl Leg', 'TandoorRate', '+', 25.0, None, None),
    ('Boneless', 'TandoorRate', '+', 95.0, None, None),
    ('Full Leg', 'TandoorRate', '+', 18.0, None, None),
    ('Wings', 'TandoorRate', '+', 15.0, None, None),
]

def render():
    st.header("Vendor Management")
    
    tab1, tab2, tab3 = st.tabs(["Suppliers", "Markup Rules", "Payments & Ledger"])
    
    # --- TAB 1: SUPPLIERS ---
    with tab1:
        render_suppliers_tab()

    # --- TAB 2: MARKUP RULES ---
    with tab2:
        render_markups_tab()

    # --- TAB 3: PAYMENTS & LEDGER ---
    with tab3:
        render_ledger_tab()

def get_db_connection():
    return sqlite3.connect(chicken_db.DB_NAME)

# -----------------------------------------------------------------------------
# TAB 1: SUPPLIERS
# -----------------------------------------------------------------------------
def render_suppliers_tab():
    st.subheader("Manage Suppliers")
    
    # 1. List Existing Suppliers
    conn = get_db_connection()
    df_suppliers = pd.read_sql_query("SELECT * FROM Suppliers", conn)
    conn.close()
    
    st.dataframe(df_suppliers, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # 2. Add / Edit Form
    st.subheader("Add / Update Supplier")
    
    with st.form("supplier_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Supplier Name")
            phone = st.text_input("Phone Number")
            vendor_type = st.selectbox("Vendor Type", ["Chicken", "Vegetable", "Other"])
        with col2:
            pay_type = st.selectbox("Preferred Payment", ["Cash", "Bank Transfer", "Cheque", "Credit"])
            freq = st.selectbox("Payment Frequency", ["Daily", "Weekly", "Monthly", "Upon Bill"])
            markup_req = st.checkbox("Markup Required (Price Validation)", value=True)
            
        submitted = st.form_submit_button("Save Supplier")
        
        if submitted:
            if not name:
                st.error("Supplier Name is required.")
            else:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    
                    # Upsert logic (simplified: Insert or Replace)
                    # Note: Replace might change ID, so better to check existence
                    cursor.execute("SELECT SupplierID FROM Suppliers WHERE SupplierName = ?", (name,))
                    existing = cursor.fetchone()
                    
                    if existing:
                        cursor.execute("""
                            UPDATE Suppliers SET PhoneNumber=?, PreferredPaymentType=?, PaymentFrequency=?, VendorType=?, MarkupRequired=?
                            WHERE SupplierName=?
                        """, (phone, pay_type, freq, vendor_type, 1 if markup_req else 0, name))
                        st.success(f"Supplier '{name}' updated.")
                    else:
                        cursor.execute("""
                            INSERT INTO Suppliers (SupplierName, PhoneNumber, PreferredPaymentType, PaymentFrequency, VendorType, MarkupRequired)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (name, phone, pay_type, freq, vendor_type, 1 if markup_req else 0))
                        st.success(f"Supplier '{name}' added.")
                        
                        # Auto-populate defaults for Chicken
                        if vendor_type == 'Chicken' and markup_req:
                             chicken_db.insert_default_markups(name, DEFAULT_CHICKEN_MARKUP_RULES)
                             st.info("Default markup rules added.")

                    conn.commit()
                    conn.close()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving supplier: {e}")

    # 3. Delete
    with st.expander("Delete Supplier"):
        del_name = st.selectbox("Select Supplier to Delete", options=df_suppliers['SupplierName'].tolist() if not df_suppliers.empty else [])
        if st.button("Delete Supplier", type="primary"):
            if del_name:
                try:
                    # We need the ID for the delete function
                    supplier_id = df_suppliers[df_suppliers['SupplierName'] == del_name]['SupplierID'].values[0]
                    if chicken_db.delete_vendor_and_cleanup(supplier_id, del_name):
                        st.success(f"Supplier '{del_name}' deleted.")
                        st.rerun()
                    else:
                        st.error("Failed to delete.")
                except Exception as e:
                    st.error(f"Error: {e}")

# -----------------------------------------------------------------------------
# TAB 2: MARKUP RULES
# -----------------------------------------------------------------------------
def render_markups_tab():
    st.subheader("Markup Rules")
    
    suppliers, _ = chicken_db.fetch_suppliers_and_items()
    selected_vendor = st.selectbox("Select Vendor for Rules", options=suppliers if suppliers else [], key="markup_vendor")
    
    if not selected_vendor:
        return

    # Load Rules
    conn = get_db_connection()
    df_rules = pd.read_sql_query("""
        SELECT ItemID, ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2 
        FROM Markups WHERE SupplierName = ?
    """, conn, params=(selected_vendor,))
    conn.close()
    
    # If empty, we might want to show an empty structure for editing
    if df_rules.empty:
        # Create empty DF with correct columns
        df_rules = pd.DataFrame(columns=['ItemID', 'ItemName', 'BaseRateType', 'MarkupOperator1', 'MarkupValue1', 'MarkupOperator2', 'MarkupValue2'])

    # Configure Editor
    column_config = {
        "ItemID": None, # Hide ID
        "ItemName": st.column_config.TextColumn("Item Name", required=True),
        "BaseRateType": st.column_config.SelectboxColumn("Base Rate", options=["TandoorRate", "BoilerRate", "EggRate"], required=True),
        "MarkupOperator1": st.column_config.SelectboxColumn("Op 1", options=["+", "-", "*", "/", ""]),
        "MarkupValue1": st.column_config.NumberColumn("Val 1", step=0.1),
        "MarkupOperator2": st.column_config.SelectboxColumn("Op 2", options=["+", "-", "*", "/", ""]),
        "MarkupValue2": st.column_config.NumberColumn("Val 2", step=0.1),
    }
    
    st.info("You can add new rows or delete existing ones (select row and press Delete key).")
    
    edited_df = st.data_editor(
        df_rules,
        column_config=column_config,
        num_rows="dynamic", # Allows adding/deleting rows
        key="markup_editor",
        use_container_width=True,
        hide_index=True
    )
    
    if st.button("Save Markup Rules"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Full Replace Strategy
            cursor.execute("DELETE FROM Markups WHERE SupplierName = ?", (selected_vendor,))
            
            rules_to_insert = []
            for _, row in edited_df.iterrows():
                if row['ItemName']: # Skip empty rows
                    rules_to_insert.append((
                        selected_vendor,
                        row['ItemName'],
                        row['BaseRateType'],
                        row['MarkupOperator1'],
                        row['MarkupValue1'],
                        row['MarkupOperator2'],
                        row['MarkupValue2']
                    ))
            
            cursor.executemany("""
                INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, rules_to_insert)
            
            conn.commit()
            conn.close()
            st.success("Markup rules saved successfully.")
            st.rerun()
            
        except Exception as e:
            st.error(f"Error saving rules: {e}")

# -----------------------------------------------------------------------------
# TAB 3: PAYMENTS & LEDGER
# -----------------------------------------------------------------------------
def render_ledger_tab():
    st.subheader("Payments & Ledger")
    
    suppliers, _ = chicken_db.fetch_suppliers_and_items()
    selected_vendor = st.selectbox("Select Vendor for Ledger", options=suppliers if suppliers else [], key="ledger_vendor")
    
    if not selected_vendor:
        return
        
    # 1. Record Payment
    with st.expander("Record New Payment", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            pay_amount = st.number_input("Amount Paid", min_value=0.0, step=100.0)
        with col2:
            pay_date = st.date_input("Payment Date", value=datetime.now(), key="pay_date")
        with col3:
            pay_details = st.text_input("Details (Optional)", value="Payment")
            
        if st.button("Record Payment"):
            if pay_amount > 0:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount, Details)
                        VALUES (?, ?, ?, ?, ?)
                    """, (pay_date, selected_vendor, 'Payment', -abs(pay_amount), pay_details))
                    conn.commit()
                    conn.close()
                    st.success(f"Payment of ₹{pay_amount} recorded.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Enter a valid amount.")

    st.divider()

    # 2. View Ledger
    conn = get_db_connection()
    
    # Fetch Bills (aggregated)
    df_bills = pd.read_sql_query("""
        SELECT Date, 'Bill' AS TransactionType, SUM(Qty * VendorRate) AS Amount, 'Bill Total' AS Details
        FROM BillEntries WHERE SupplierName = ?
        GROUP BY Date
    """, conn, params=(selected_vendor,))
    
    # Fetch Payments
    df_payments = pd.read_sql_query("""
        SELECT Date, TransactionType, Amount, Details FROM VendorLedger WHERE SupplierName = ?
    """, conn, params=(selected_vendor,))
    
    conn.close()
    
    # Combine
    df_ledger = pd.concat([df_bills, df_payments], ignore_index=True)
    if not df_ledger.empty:
        df_ledger['Date'] = pd.to_datetime(df_ledger['Date'])
        df_ledger = df_ledger.sort_values(by='Date', ascending=False)
        df_ledger['Date'] = df_ledger['Date'].dt.strftime('%Y-%m-%d')
        
        # Calculate Balance
        balance = df_ledger['Amount'].sum()
        
        # Display Balance
        if balance > 0:
            st.metric("Net Due", f"₹{balance:,.2f}", delta="Payable")
        else:
            st.metric("Net Due", f"₹{balance:,.2f}", delta="Overpaid/Clear", delta_color="inverse")
            
        # Display Table
        st.dataframe(
            df_ledger, 
            column_config={
                "Amount": st.column_config.NumberColumn("Amount", format="₹%.2f")
            },
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.info("No transactions found for this vendor.")
