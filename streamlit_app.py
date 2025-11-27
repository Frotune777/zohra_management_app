import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import chicken_db

# --- Page Config ---
st.set_page_config(
    page_title="Chicken Tracker",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Styling ---
# --- Styling ---
st.markdown("""
<style>
    /* Import Google Font */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap');

    html, body, [class*="css"]  {
        font-family: 'Inter', sans-serif;
    }

    /* Main Container */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max_width: 1200px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #f8f9fa;
        border-right: 1px solid #e9ecef;
    }
    [data-testid="stSidebar"] h1 {
        color: #1f2937;
        font-weight: 700;
        font-size: 1.5rem;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
        border-bottom: 1px solid #e5e7eb;
        padding-bottom: 0px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 45px;
        white-space: pre-wrap;
        background-color: transparent;
        border-radius: 6px 6px 0px 0px;
        gap: 1px;
        padding: 10px 20px;
        color: #6b7280;
        font-weight: 600;
        border: none;
        transition: all 0.2s ease;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background-color: #f3f4f6;
        color: #374151;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        color: #ef4444 !important; /* Red accent */
        border-bottom: 2px solid #ef4444;
        box-shadow: none;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e5e7eb;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricLabel"] {
        color: #6b7280;
        font-size: 0.875rem;
    }
    [data-testid="stMetricValue"] {
        color: #111827;
        font-weight: 700;
    }

    /* Buttons */
    .stButton button {
        background-color: #ef4444;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: background-color 0.2s;
    }
    .stButton button:hover {
        background-color: #dc2626;
        color: white;
        border: none;
    }
    /* Secondary/Form Buttons */
    div[data-testid="stForm"] .stButton button {
        width: 100%;
    }

    /* Inputs */
    .stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] {
        border-radius: 6px;
        border: 1px solid #d1d5db;
    }
    .stTextInput input:focus, .stNumberInput input:focus {
        border-color: #ef4444;
        box-shadow: 0 0 0 1px #ef4444;
    }

    /* Data Editor/Tables */
    [data-testid="stDataFrame"] {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Headers */
    h1, h2, h3 {
        color: #111827;
        font-weight: 700;
    }
    h2 {
        font-size: 1.5rem;
        margin-top: 1rem;
        margin-bottom: 1rem;
    }
    h3 {
        font-size: 1.1rem;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
    }
    
    /* Alerts */
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
st.sidebar.title("🐔 Chicken Tracker")
st.sidebar.markdown("---")
st.sidebar.info("Manage daily rates, bills, and vendors efficiently.")

# --- Helper Functions ---
def get_db_connection():
    return sqlite3.connect(chicken_db.DB_NAME)

def load_data(query, params=None):
    conn = get_db_connection()
    if params:
        df = pd.read_sql_query(query, conn, params=params)
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["Daily Rates", "Bill Entry", "Vendor Management", "Dashboard"])

# ==========================
# TAB 1: DAILY RATES
# ==========================
with tab1:
    st.header("Daily Rate Entry")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        date_val = st.date_input("Select Date", datetime.now())
        date_str = date_val.strftime("%Y-%m-%d")
        
        # Load existing rates
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT TandoorRate, BoilerRate, EggRate FROM RawData WHERE Date = ?", (date_str,))
        existing = cursor.fetchone()
        conn.close()
        
        tandoor_default = existing[0] if existing else 0.0
        boiler_default = existing[1] if existing else 0.0
        egg_default = existing[2] if existing else 0.0
        
        with st.form("rate_form"):
            tandoor = st.number_input("Tandoor Rate", min_value=0.0, value=tandoor_default, step=1.0)
            boiler = st.number_input("Boiler Rate", min_value=0.0, value=boiler_default, step=1.0)
            egg = st.number_input("Egg Rate", min_value=0.0, value=egg_default, step=0.1)
            
            submitted = st.form_submit_button("Save Rates", type="primary")
            
            if submitted:
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO RawData (Date, TandoorRate, BoilerRate, EggRate) VALUES (?, ?, ?, ?)
                        ON CONFLICT(Date) DO UPDATE SET TandoorRate=excluded.TandoorRate, BoilerRate=excluded.BoilerRate, EggRate=excluded.EggRate
                    """, (date_str, tandoor, boiler, egg))
                    conn.commit()
                    conn.close()
                    st.success(f"Rates for {date_str} saved successfully!")
                    chicken_db.fetch_rate_history.clear() # Clear cache
                except Exception as e:
                    st.error(f"Error saving rates: {e}")

# ==========================
# TAB 2: BILL ENTRY
# ==========================
with tab2:
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
                width=True,
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
                        conn = get_db_connection()
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

# ==========================
# TAB 3: VENDOR MANAGEMENT
# ==========================
with tab3:
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
            width=True
        )
        
        if st.button("Save Changes (Suppliers)"):
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Detect Changes
                # We iterate through the edited dataframe and compare with original (re-fetched to be safe)
                # Note: This simple logic assumes SupplierID is constant.
                
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
                        # We update everything else regardless if name changed (safe)
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
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        cursor.execute("""
                            INSERT INTO Suppliers (SupplierName, PhoneNumber, PreferredPaymentType, PaymentFrequency, VendorType, MarkupRequired)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (new_name, new_phone, new_pay, new_freq, new_type, 1 if new_markup else 0))
                        conn.commit()
                        conn.close()
                        st.success(f"Supplier {new_name} added!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding supplier: {e}")

    with v_tab2:
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
                width=True,
                key="markup_editor"
            )
            
            if st.button("Save Rules"):
                # Basic save logic: Delete all for vendor and re-insert (simplest for full sync)
                try:
                    conn = get_db_connection()
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

# ==========================
# TAB 4: DASHBOARD
# ==========================
with tab4:
    st.header("Dashboard")
    
    # Metrics
    dues = chicken_db.fetch_vendor_dues()
    total_due = sum(dues.values())
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("Total Outstanding Dues", f"₹{total_due:,.2f}")
    
    # Rate Trends
    st.subheader("Rate Trends (Last 30 Days)")
    history = chicken_db.fetch_rate_history(30)
    if history:
        df_hist = pd.DataFrame(history, columns=["Date", "Tandoor", "Boiler", "Egg"])
        df_hist["Date"] = pd.to_datetime(df_hist["Date"])
        df_hist.set_index("Date", inplace=True)
        st.line_chart(df_hist)
    else:
        st.info("No rate data available.")
        
    # Vendor Dues Chart
    st.subheader("Vendor Dues")
    if dues:
        df_dues = pd.DataFrame(list(dues.items()), columns=["Vendor", "Amount"])
        df_dues.set_index("Vendor", inplace=True)
        st.bar_chart(df_dues)
    else:
        st.info("No due data available.")
