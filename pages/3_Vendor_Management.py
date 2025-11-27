import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

# Add parent directory to path to import chicken_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db
import utils

# Apply styling
utils.apply_styling()

def load_data(query, params=None):
    conn = utils.get_db_connection()
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

st.header("Vendor Management")

v_tab1, v_tab2 = st.tabs(["Suppliers", "Markup Rules"])

with v_tab1:
    # Load Suppliers
    df_suppliers = load_data("SELECT * FROM Suppliers")
    
    st.markdown("### Existing Suppliers")
    edited_suppliers = st.data_editor(
        df_suppliers,
        num_rows="dynamic",
        key="supplier_editor",
        use_container_width=True
    )
    
    if st.button("Save Changes (Suppliers)"):
        try:
            conn = utils.get_db_connection()
            cursor = conn.cursor()
            
            changes_count = 0
            
            for index, row in edited_suppliers.iterrows():
                supplier_id = row['SupplierID']
                new_name = row['SupplierName']
                new_phone = row['PhoneNumber']
                new_pay = row['PreferredPaymentType']
                new_freq = row['PaymentFrequency']
                new_type = row['VendorType']
                new_markup = 1 if row['MarkupRequired'] else 0
                
                # Fetch current state from DB
                cursor.execute("SELECT * FROM Suppliers WHERE SupplierID = ?", (supplier_id,))
                current = cursor.fetchone()
                
                if current:
                    # Current: ID, Name, Phone, Pay, Freq, Type, Markup, LastUpdated
                    old_name = current[1]
                    
                    # Check for Rename
                    if old_name != new_name:
                        if chicken_db.rename_vendor(old_name, new_name):
                            st.toast(f"Renamed '{old_name}' to '{new_name}' and updated related records.")
                            changes_count += 1
                        else:
                            st.error(f"Failed to rename '{old_name}'. Name might already exist.")
                            continue
                    
                    # Check for other updates
                    cursor.execute("""
                        UPDATE Suppliers 
                        SET PhoneNumber=?, PreferredPaymentType=?, PaymentFrequency=?, VendorType=?, MarkupRequired=?, LastUpdated=?
                        WHERE SupplierID=?
                    """, (new_phone, new_pay, new_freq, new_type, new_markup, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), supplier_id))
                    if cursor.rowcount > 0:
                        changes_count += 1
            
            conn.commit()
            conn.close()
            
            if changes_count > 0:
                st.success("Supplier details updated successfully!")
                chicken_db.fetch_suppliers_and_items.clear() # Clear cache
                st.rerun()
            else:
                st.info("No changes detected.")
                
        except Exception as e:
            st.error(f"Error updating suppliers: {e}")
    
    with st.expander("Add New Supplier"):
        with st.form("add_vendor"):
            new_name = st.text_input("Supplier Name")
            new_phone = st.text_input("Phone")
            new_type = st.selectbox("Type", ["Chicken", "Vegetable", "Other"])
            new_pay = st.selectbox("Payment", ["Cash", "Bank Transfer", "Cheque"])
            new_freq = st.selectbox("Frequency", ["Daily", "Weekly", "Monthly"])
            new_markup = st.checkbox("Markup Required", value=True)
            
            if st.form_submit_button("Add Supplier"):
                try:
                    conn = utils.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO Suppliers (SupplierName, PhoneNumber, PreferredPaymentType, PaymentFrequency, VendorType, MarkupRequired, LastUpdated)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (new_name, new_phone, new_pay, new_freq, new_type, 1 if new_markup else 0, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.commit()
                    conn.close()
                    st.success(f"Supplier {new_name} added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding supplier: {e}")

with v_tab2:
    suppliers, _ = chicken_db.fetch_suppliers_and_items()
    markup_vendor = st.selectbox("Select Vendor for Rules", suppliers, key="markup_vendor_select")
    
    if markup_vendor:
        df_markups = load_data("SELECT * FROM Markups WHERE SupplierName = ?", params=(markup_vendor,))
        
        st.markdown(f"### Markup Rules for {markup_vendor}")
        edited_markups = st.data_editor(
            df_markups,
            num_rows="dynamic",
            column_config={
                "ItemID": st.column_config.NumberColumn(disabled=True),
                "SupplierName": st.column_config.TextColumn(disabled=True),
                "BaseRateType": st.column_config.SelectboxColumn(options=["TandoorRate", "BoilerRate", "EggRate"]),
                "MarkupOperator1": st.column_config.SelectboxColumn(options=["+", "-", "*", "/"]),
                "MarkupOperator2": st.column_config.SelectboxColumn(options=["+", "-", "*", "/"]),
            },
            use_container_width=True,
            key="markup_editor"
        )
        
        if st.button("Save Rules"):
            # Basic save logic: Delete all for vendor and re-insert (simplest for full sync)
            try:
                conn = utils.get_db_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM Markups WHERE SupplierName = ?", (markup_vendor,))
                
                rules = []
                for _, row in edited_markups.iterrows():
                    if row["ItemName"]:
                        rules.append((
                            markup_vendor, row["ItemName"], row["BaseRateType"],
                            row["MarkupOperator1"], row["MarkupValue1"],
                            row["MarkupOperator2"], row["MarkupValue2"]
                        ))
                
                if rules:
                    cursor.executemany("""
                        INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, rules)
                
                conn.commit()
                conn.close()
                st.success("Rules updated!")
            except Exception as e:
                st.error(f"Error saving rules: {e}")
