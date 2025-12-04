import streamlit as st
import pandas as pd
import chicken_db
import sqlite3
from datetime import datetime

def render():
    st.header("Daily Rates Entry")
    
    # Date Selection
    date = st.date_input("Select Date", value=datetime.now())
    
    # Pre-fill Logic
    conn = chicken_db.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT TandoorRate, BoilerRate, EggRate FROM RawData WHERE Date = ?", (date,))
    existing_data = cursor.fetchone()
    conn.close()
    
    default_tandoor = 0.0
    default_boiler = 0.0
    default_egg = 0.0
    
    if existing_data:
        default_tandoor = existing_data[0]
        default_boiler = existing_data[1]
        default_egg = existing_data[2]
        st.info(f"Loaded existing rates for {date}.")
    
    # Rate Inputs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        tandoor = st.number_input("Tandoor Rate", min_value=0.0, step=0.1, value=default_tandoor)
    with col2:
        boiler = st.number_input("Boiler Rate", min_value=0.0, step=0.1, value=default_boiler)
    with col3:
        egg = st.number_input("Egg Rate", min_value=0.0, step=0.1, value=default_egg)
        
    if st.button("Save Rates"):
        try:
            conn = chicken_db.get_db_connection()
            cursor = conn.cursor()
            
            # 1. Upsert Rates
            cursor.execute("""
                INSERT INTO RawData (Date, TandoorRate, BoilerRate, EggRate) VALUES (?, ?, ?, ?)
                ON CONFLICT(Date) DO UPDATE SET TandoorRate=excluded.TandoorRate, BoilerRate=excluded.BoilerRate, EggRate=excluded.EggRate
            """, (date, tandoor, boiler, egg))
            
            # 2. Update BillEntries
            updated_count = update_bill_entries_for_date(cursor, date, tandoor, boiler, egg)
            
            conn.commit()
            conn.close()
            st.success(f"Rates for {date} saved successfully! Updated {updated_count} bill entries.")
            
        except Exception as e:
            st.error(f"Error saving rates: {e}")

    st.divider()
    st.subheader("Bulk Import Rates (CSV)")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"], help="Upload daily rates CSV")
    
    if uploaded_file:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("Preview:", df.head())
            
            # Column Mapping
            st.write("Map Columns:")
            cols = df.columns.tolist()
            
            # Try to auto-select if names match
            def get_index(options, key_keywords):
                for i, opt in enumerate(options):
                    if any(k.lower() in opt.lower() for k in key_keywords):
                        return i
                return 0

            col_date = st.selectbox("Date Column", cols, index=get_index(cols, ['date']))
            col_tandoor = st.selectbox("Tandoor Rate Column", cols, index=get_index(cols, ['tandoor']))
            col_boiler = st.selectbox("Boiler Rate Column", cols, index=get_index(cols, ['boiler']))
            col_egg = st.selectbox("Egg Rate Column", cols, index=get_index(cols, ['egg']))
            
            if st.button("Import CSV Data"):
                conn = chicken_db.get_db_connection()
                cursor = conn.cursor()
                total_updated = 0
                
                progress_bar = st.progress(0)
                for i, row in df.iterrows():
                    # Handle Date Formats (d/m/Y or d/m/y)
                    raw_date = row[col_date]
                    try:
                        d_date = pd.to_datetime(raw_date, dayfirst=True).strftime('%Y-%m-%d')
                    except:
                        try:
                            d_date = pd.to_datetime(raw_date).strftime('%Y-%m-%d')
                        except:
                            st.error(f"Could not parse date: {raw_date}")
                            continue

                    d_tandoor = float(row[col_tandoor])
                    d_boiler = float(row[col_boiler])
                    d_egg = float(row[col_egg])
                    
                    cursor.execute("""
                        INSERT INTO RawData (Date, TandoorRate, BoilerRate, EggRate) VALUES (?, ?, ?, ?)
                        ON CONFLICT(Date) DO UPDATE SET TandoorRate=excluded.TandoorRate, BoilerRate=excluded.BoilerRate, EggRate=excluded.EggRate
                    """, (d_date, d_tandoor, d_boiler, d_egg))
                    
                    total_updated += update_bill_entries_for_date(cursor, d_date, d_tandoor, d_boiler, d_egg)
                    progress_bar.progress((i + 1) / len(df))
                
                conn.commit()
                conn.close()
                st.success(f"Imported {len(df)} rows. Updated {total_updated} related bill entries.")
        except Exception as e:
            st.error(f"Error processing CSV: {e}")

def update_bill_entries_for_date(cursor, date, tandoor, boiler, egg):
    """Recalculates ExpectedRate and Variance for all bills on a given date."""
    cursor.execute("SELECT SupplierName, ItemName, Qty, VendorRate FROM BillEntries WHERE Date = ?", (date,))
    entries = cursor.fetchall()
    
    updated_count = 0
    raw_rates = (tandoor, boiler, egg)
    
    for supplier, item, qty, vendor_rate in entries:
        cursor.execute("""
            SELECT BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2
            FROM Markups 
            WHERE SupplierName = ? AND ItemName = ?
        """, (supplier, item))
        rule = cursor.fetchone()
        
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        exp_amount = round(qty * expected_rate, 2)
        vendor_amount = round(qty * vendor_rate, 2)
        variance = round(vendor_amount - exp_amount, 2)
        
        status = 'Okay'
        if qty > 0 and expected_rate > 0:
            var_pct = (variance / exp_amount) * 100 if exp_amount else 0.0
            if var_pct > 5.0: status = 'HIGH (+)'
            elif var_pct < -5.0: status = 'LOW (-)'
            elif variance != 0.0: status = 'Variance'
        elif expected_rate == 0.0:
            status = 'No Rate Data'
        
        cursor.execute("""
            UPDATE BillEntries 
            SET ExpectedRate = ?, Variance = ?, Status = ?
            WHERE Date = ? AND SupplierName = ? AND ItemName = ?
        """, (expected_rate, variance, status, date, supplier, item))
        updated_count += 1
    return updated_count