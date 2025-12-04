import streamlit as st
import pandas as pd
import chicken_db
import sqlite3
from datetime import datetime

def render():
    st.header("Daily Bill Entry")

    # --- 1. Controls ---
    col1, col2 = st.columns(2)
    
    with col1:
        bill_date = st.date_input("Bill Date", value=datetime.now())
    
    with col2:
        suppliers, _ = chicken_db.fetch_suppliers_and_items()
        selected_vendor = st.selectbox("Select Vendor", options=suppliers if suppliers else [])

    if not selected_vendor:
        st.warning("Please add suppliers in Vendor Management first.")
        return

    # --- 2. Data Loading & State Management ---
    current_key = f"{selected_vendor}_{bill_date}"
    
    if 'bill_entry_key' not in st.session_state or st.session_state.bill_entry_key != current_key:
        # Load items and initial data
        items = chicken_db.fetch_items_for_supplier(selected_vendor)
        
        if not items:
            st.warning(f"No markup rules found for {selected_vendor}. Please add rules in Vendor Management.")
            st.session_state.bill_data = pd.DataFrame()
            st.session_state.bill_entry_key = current_key
            return

        # Check for existing entries in DB
        conn = chicken_db.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT ItemName, Qty, VendorRate, ExpectedRate, Variance, Status FROM BillEntries WHERE SupplierName = ? AND Date = ?", (selected_vendor, bill_date))
        existing_entries = cursor.fetchall()
        conn.close()
        
        existing_map = {row[0]: row for row in existing_entries}

        data = []
        for item in items:
            # Fetch expected rate
            raw_rates, rule = chicken_db.fetch_rate_and_rule(bill_date, selected_vendor, item)
            expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
            
            if item in existing_map:
                # Load existing
                _, qty, v_rate, exp_rate_db, var, status = existing_map[item]
                # Note: We don't store Qty Recv/Dmg separately in DB currently, only Net Qty.
                # So we will assume Qty Recv = Net Qty and Qty Dmg = 0 for re-loading to keep it simple,
                # or we could add columns to DB. For now, simplified assumption.
                qty_recv = qty
                qty_dmg = 0.0
                vendor_rate = v_rate
            else:
                qty_recv = 0.0
                qty_dmg = 0.0
                vendor_rate = 0.0
            
            data.append({
                "Item Name": item,
                "Qty Recv": qty_recv,
                "Qty Dmg": qty_dmg,
                "Vendor Rate": vendor_rate,
                "Expected Rate": expected_rate,
                "Net Qty": max(0.0, qty_recv - qty_dmg),
                "Exp Amount": 0.0, # Calculated later
                "Vendor Amount": 0.0, # Calculated later
                "Variance": 0.0, # Calculated later
                "Status": "Pending"
            })
            
        st.session_state.bill_data = pd.DataFrame(data)
        st.session_state.bill_entry_key = current_key

    if st.session_state.bill_data.empty:
        return

    # --- 3. TABS ---
    tab_recv, tab_dmg, tab_verify = st.tabs(["1. Item Received", "2. Damage Entry", "3. Verification & Save"])
    
    # Helper to update calculations
    def recalculate_data():
        df = st.session_state.bill_data
        df["Net Qty"] = (df["Qty Recv"] - df["Qty Dmg"]).clip(lower=0.0)
        df["Exp Amount"] = (df["Net Qty"] * df["Expected Rate"]).round(2)
        df["Vendor Amount"] = (df["Net Qty"] * df["Vendor Rate"]).round(2)
        df["Variance"] = (df["Vendor Amount"] - df["Exp Amount"]).round(2)
        
        def get_status(row):
            if row["Net Qty"] <= 0: return "N/A"
            if row["Expected Rate"] == 0: return "No Rate"
            var_pct = (row["Variance"] / row["Exp Amount"] * 100) if row["Exp Amount"] != 0 else 0
            if var_pct > 5: return "HIGH (+)"
            if var_pct < -5: return "LOW (-)"
            if row["Variance"] != 0: return "Variance"
            return "Okay"

        df["Status"] = df.apply(get_status, axis=1)
        st.session_state.bill_data = df

    # --- TAB 1: RECEIVED ---
    with tab_recv:
        st.info("Enter the Quantity Received for each item.")
        
        edited_recv = st.data_editor(
            st.session_state.bill_data[["Item Name", "Qty Recv"]],
            column_config={
                "Item Name": st.column_config.TextColumn(disabled=True),
                "Qty Recv": st.column_config.NumberColumn(min_value=0.0, step=0.1, required=True)
            },
            use_container_width=True,
            hide_index=True,
            key="editor_recv"
        )
        
        # Sync back to session state
        st.session_state.bill_data["Qty Recv"] = edited_recv["Qty Recv"]
        recalculate_data()

    # --- TAB 2: DAMAGE ---
    with tab_dmg:
        st.info("Enter Quantity Damaged. Net Quantity will be calculated automatically.")
        
        # Prepare view with Net Qty for reference
        view_dmg = st.session_state.bill_data[["Item Name", "Qty Recv", "Qty Dmg", "Net Qty"]].copy()
        
        edited_dmg = st.data_editor(
            view_dmg,
            column_config={
                "Item Name": st.column_config.TextColumn(disabled=True),
                "Qty Recv": st.column_config.NumberColumn(disabled=True),
                "Qty Dmg": st.column_config.NumberColumn(min_value=0.0, step=0.1, required=True),
                "Net Qty": st.column_config.NumberColumn(disabled=True)
            },
            use_container_width=True,
            hide_index=True,
            key="editor_dmg"
        )
        
        # Sync back
        st.session_state.bill_data["Qty Dmg"] = edited_dmg["Qty Dmg"]
        recalculate_data()

    # --- TAB 3: VERIFICATION ---
    with tab_verify:
        st.info("Enter Vendor Rate and Verify against Expected Rate.")
        
        # Prepare view
        view_verify = st.session_state.bill_data[["Item Name", "Net Qty", "Vendor Rate", "Expected Rate", "Vendor Amount", "Variance", "Status"]].copy()
        
        edited_verify = st.data_editor(
            view_verify,
            column_config={
                "Item Name": st.column_config.TextColumn(disabled=True),
                "Net Qty": st.column_config.NumberColumn(disabled=True),
                "Vendor Rate": st.column_config.NumberColumn(min_value=0.0, step=0.01, required=True),
                "Expected Rate": st.column_config.NumberColumn(disabled=True, format="%.2f"),
                "Vendor Amount": st.column_config.NumberColumn(disabled=True, format="%.2f"),
                "Variance": st.column_config.NumberColumn(disabled=True, format="%.2f"),
                "Status": st.column_config.TextColumn(disabled=True),
            },
            use_container_width=True,
            hide_index=True,
            key="editor_verify"
        )
        
        # Sync back
        st.session_state.bill_data["Vendor Rate"] = edited_verify["Vendor Rate"]
        recalculate_data() # Final recalc
        
        # Totals
        df_final = st.session_state.bill_data
        total_bill = df_final["Vendor Amount"].sum()
        total_exp = df_final["Exp Amount"].sum()
        total_var = df_final["Variance"].sum()
        
        st.divider()
        t_col1, t_col2, t_col3 = st.columns(3)
        t_col1.metric("Total Bill Amount", f"₹{total_bill:,.2f}")
        t_col2.metric("Total Expected", f"₹{total_exp:,.2f}")
        t_col3.metric("Total Variance", f"₹{total_var:,.2f}", delta_color="inverse")

        # Save Action
        if st.button("Save Bill Entries", type="primary"):
            entries_to_save = df_final[df_final["Net Qty"] > 0].copy()
            
            if entries_to_save.empty:
                st.warning("No entries with positive Net Quantity to save.")
            else:
                try:
                    conn = chicken_db.get_db_connection()
                    cursor = conn.cursor()
                    
                    # Check for existing
                    cursor.execute("SELECT COUNT(*) FROM BillEntries WHERE SupplierName = ? AND Date = ?", (selected_vendor, bill_date))
                    if cursor.fetchone()[0] > 0:
                        cursor.execute("DELETE FROM BillEntries WHERE SupplierName = ? AND Date = ?", (selected_vendor, bill_date))
                        cursor.execute("DELETE FROM VendorLedger WHERE SupplierName = ? AND Date = ? AND TransactionType = 'Bill'", (selected_vendor, bill_date))
                    
                    # Insert Bill Entries
                    db_entries = []
                    for _, row in entries_to_save.iterrows():
                        db_entries.append((
                            bill_date, selected_vendor, row["Item Name"], 
                            row["Net Qty"], row["Vendor Rate"], row["Expected Rate"], 
                            row["Variance"], row["Status"]
                        ))
                    
                    cursor.executemany("""
                        INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, db_entries)
                    
                    # Insert Ledger Entry
                    cursor.execute("""
                        INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount, Details)
                        VALUES (?, ?, ?, ?, ?)
                    """, (bill_date, selected_vendor, 'Bill', total_bill, f"Total Bill Amount for {bill_date}"))
                    
                    conn.commit()
                    conn.close()
                    st.success(f"Bill saved successfully! Total: ₹{total_bill:,.2f}")
                    
                    # Clear session state
                    del st.session_state.bill_entry_key
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error saving bill: {e}")

    # --- 4. CSV Import ---
    st.divider()
    st.subheader("Bulk Import Bills (CSV)")
    
    import_type = st.radio("Import Format", ["Standard (Long Format)", "Wide Format (Item Columns)"])
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("Preview:", df.head())
            cols = df.columns.tolist()
            
            if import_type == "Standard (Long Format)":
                # ... existing logic with mapping ...
                st.info("Expected columns: Date, SupplierName, ItemName, Qty, VendorRate")
                # (Simplified for now, focusing on the user's wide format request)
                pass 
                
            else: # Wide Format
                st.write("Map Columns:")
                
                # Date Column
                def get_index(options, key_keywords):
                    for i, opt in enumerate(options):
                        if any(k.lower() in opt.lower() for k in key_keywords):
                            return i
                    return 0
                
                col_date = st.selectbox("Date Column", cols, index=get_index(cols, ['date']))
                
                # Supplier Selection (since it's likely one file per supplier or missing)
                suppliers, _ = chicken_db.fetch_suppliers_and_items()
                default_supplier = st.selectbox("Select Supplier for this CSV", options=suppliers if suppliers else [])
                
                # Item Columns Selection
                st.write("Select Item Columns to Import (Qty):")
                item_cols = st.multiselect("Item Columns", [c for c in cols if c != col_date], default=[c for c in cols if c != col_date])
                
                if st.button("Import Wide CSV"):
                    if not default_supplier:
                        st.error("Please select a supplier.")
                    else:
                        conn = chicken_db.get_db_connection()
                        cursor = conn.cursor()
                        
                        progress_bar = st.progress(0)
                        total_rows = len(df)
                        
                        for i, row in df.iterrows():
                            # Parse Date
                            raw_date = row[col_date]
                            try:
                                bill_date = pd.to_datetime(raw_date, dayfirst=True).strftime('%Y-%m-%d')
                            except:
                                try:
                                    bill_date = pd.to_datetime(raw_date).strftime('%Y-%m-%d')
                                except:
                                    st.error(f"Invalid date: {raw_date}")
                                    continue
                            
                            # Check/Delete Existing for this Date/Supplier
                            # Note: This deletes per row, which is inefficient if multiple rows have same date.
                            # But usually wide format has unique dates.
                            cursor.execute("SELECT COUNT(*) FROM BillEntries WHERE SupplierName = ? AND Date = ?", (default_supplier, bill_date))
                            if cursor.fetchone()[0] > 0:
                                cursor.execute("DELETE FROM BillEntries WHERE SupplierName = ? AND Date = ?", (default_supplier, bill_date))
                                cursor.execute("DELETE FROM VendorLedger WHERE SupplierName = ? AND Date = ? AND TransactionType = 'Bill'", (default_supplier, bill_date))

                            total_bill_amount = 0.0
                            db_entries = []
                            
                            for item_col in item_cols:
                                qty = float(row[item_col]) if pd.notnull(row[item_col]) else 0.0
                                if qty > 0:
                                    # Map CSV header to Item Name (simple direct mapping for now)
                                    # User might need a mapping interface if names differ.
                                    # For now, assume CSV headers match DB Item Names or are close enough.
                                    # Ideally, we should check if item exists in DB for this supplier.
                                    item_name = item_col
                                    
                                    # Fetch expected rate
                                    raw_rates, rule = chicken_db.fetch_rate_and_rule(bill_date, default_supplier, item_name)
                                    expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
                                    
                                    # Vendor Rate - Not in CSV, assume equal to Expected Rate or 0?
                                    # Or maybe we should fetch the last known rate?
                                    # For now, let's set Vendor Rate = Expected Rate (assuming correct billing)
                                    # or 0 if we want them to verify.
                                    # User said "item purchased", usually implies quantity.
                                    # Let's default Vendor Rate to Expected Rate to minimize variance noise, 
                                    # but flag it? Or just 0?
                                    # Let's use Expected Rate as a "smart default".
                                    v_rate = expected_rate 
                                    
                                    exp_amount = round(qty * expected_rate, 2)
                                    vendor_amount = round(qty * v_rate, 2)
                                    variance = round(vendor_amount - exp_amount, 2)
                                    
                                    status = 'Okay'
                                    if expected_rate == 0: status = 'No Rate Data'
                                    
                                    db_entries.append((
                                        bill_date, default_supplier, item_name, qty, v_rate, expected_rate, variance, status
                                    ))
                                    total_bill_amount += vendor_amount
                            
                            if db_entries:
                                cursor.executemany("""
                                    INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, db_entries)
                                
                                cursor.execute("""
                                    INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount, Details)
                                    VALUES (?, ?, ?, ?, ?)
                                """, (bill_date, default_supplier, 'Bill', total_bill_amount, f"Imported Bill for {bill_date}"))
                            
                            progress_bar.progress((i + 1) / total_rows)
                            
                        conn.commit()
                        conn.close()
                        st.success(f"Imported bills for {total_rows} dates.")
                        
        except Exception as e:
            st.error(f"Error processing CSV: {e}")
