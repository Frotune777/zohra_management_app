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

st.header("Daily Bill Entry")

col_b1, col_b2 = st.columns(2)
with col_b1:
    bill_date = st.date_input("Bill Date", datetime.now(), key="bill_date")
    bill_date_str = bill_date.strftime("%Y-%m-%d")

with col_b2:
    suppliers, _ = chicken_db.fetch_suppliers_and_items()
    selected_vendor = st.selectbox("Select Vendor", suppliers)
    
if selected_vendor:
    # Load Items and Calculate Expected Rates
    items = chicken_db.fetch_items_for_supplier(selected_vendor)
    
    if not items:
        st.warning("No markup rules found for this vendor.")
    else:
        # Prepare Data for Editor
        data = []
        for item in items:
            raw_rates, rule = chicken_db.fetch_rate_and_rule(bill_date_str, selected_vendor, item)
            exp_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
            data.append({
                "Item": item,
                "Qty Recv": 0.0,
                "Qty Dmg": 0.0,
                "Vendor Rate": 0.0,
                "Expected Rate": exp_rate,
            })
        
        df_bill = pd.DataFrame(data)
        
        st.markdown("### Enter Bill Details")
        edited_df = st.data_editor(
            df_bill,
            column_config={
                "Item": st.column_config.TextColumn(disabled=True),
                "Expected Rate": st.column_config.NumberColumn(disabled=True, format="₹%.2f"),
                "Qty Recv": st.column_config.NumberColumn(min_value=0.0, step=1.0),
                "Qty Dmg": st.column_config.NumberColumn(min_value=0.0, step=1.0),
                "Vendor Rate": st.column_config.NumberColumn(min_value=0.0, step=1.0, format="₹%.2f"),
            },
            hide_index=True,
            width="stretch",
            key="bill_editor"
        )
        
        # Real-time Calculation Display
        if not edited_df.empty:
            edited_df["Net Qty"] = edited_df["Qty Recv"] - edited_df["Qty Dmg"]
            edited_df["Vendor Amount"] = edited_df["Net Qty"] * edited_df["Vendor Rate"]
            edited_df["Exp Amount"] = edited_df["Net Qty"] * edited_df["Expected Rate"]
            edited_df["Variance"] = edited_df["Vendor Amount"] - edited_df["Exp Amount"]
            
            total_bill = edited_df["Vendor Amount"].sum()
            st.metric("Total Bill Amount", f"₹{total_bill:,.2f}")
            
            if st.button("Save Bill Entry", type="primary"):
                try:
                    conn = utils.get_db_connection()
                    cursor = conn.cursor()
                    
                    # Cleanup existing
                    cursor.execute("DELETE FROM BillEntries WHERE SupplierName = ? AND Date = ?", (selected_vendor, bill_date_str))
                    cursor.execute("DELETE FROM VendorLedger WHERE SupplierName = ? AND Date = ? AND TransactionType = 'Bill'", (selected_vendor, bill_date_str))
                    
                    entries = []
                    for _, row in edited_df.iterrows():
                        if row["Net Qty"] > 0:
                            status = "Okay"
                            if row["Variance"] > 5: status = "HIGH (+)"
                            elif row["Variance"] < -5: status = "LOW (-)"
                            
                            entries.append((
                                bill_date_str, selected_vendor, row["Item"], 
                                row["Net Qty"], row["Vendor Rate"], row["Expected Rate"], 
                                row["Variance"], status
                            ))
                    
                    if entries:
                        cursor.executemany("""
                            INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, entries)
                        
                        # Ledger Entry
                        cursor.execute("""
                            INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount, Details)
                            VALUES (?, ?, ?, ?, ?)
                        """, (bill_date_str, selected_vendor, 'Bill', total_bill, f"Bill for {bill_date_str}"))
                        
                        conn.commit()
                        st.success("Bill saved successfully!")
                        chicken_db.fetch_vendor_dues.clear() # Clear cache
                    else:
                        st.warning("No valid entries to save (Net Qty > 0 required).")
                        
                    conn.close()
                except Exception as e:
                    st.error(f"Error saving bill: {e}")
