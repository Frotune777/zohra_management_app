import streamlit as st
import pandas as pd
import sqlite3
import chicken_db
import numpy as np
from datetime import datetime, timedelta

def get_db_connection():
    return sqlite3.connect(chicken_db.DB_NAME)

def render():
    st.header("Dashboard")
    
    tab1, tab2, tab3 = st.tabs(["Overview & Trends", "Variance Analysis", "Historical Data"])
    
    with tab1:
        render_overview_tab()
        
    with tab2:
        render_variance_tab()
        
    with tab3:
        render_history_tab()

def render_overview_tab():
    st.subheader("Financial Overview")
    
    conn = get_db_connection()
    
    # 1. Summary Metrics
    suppliers = pd.read_sql_query("SELECT SupplierName FROM Suppliers", conn)
    
    total_due = 0.0
    
    if not suppliers.empty:
        for vendor in suppliers['SupplierName']:
            cursor = conn.cursor()
            cursor.execute("SELECT IFNULL(SUM(Qty * VendorRate), 0.0) FROM BillEntries WHERE SupplierName = ?", (vendor,))
            bill_total = cursor.fetchone()[0]
            cursor.execute("SELECT IFNULL(SUM(Amount), 0.0) FROM VendorLedger WHERE SupplierName = ?", (vendor,))
            payment_total = cursor.fetchone()[0]
            total_due += (bill_total + payment_total)
    
    col1, col2 = st.columns(2)
    col1.metric("Total Outstanding Dues", f"₹{total_due:,.2f}")
    col2.metric("Active Suppliers", len(suppliers))
    
    st.divider()
    
    # 2. Rate Trends
    st.subheader("Daily Rate Trends")
    df_rates = pd.read_sql_query("SELECT Date, TandoorRate, BoilerRate, EggRate FROM RawData ORDER BY Date", conn)
    
    if not df_rates.empty:
        df_rates['Date'] = pd.to_datetime(df_rates['Date'])
        st.line_chart(df_rates, x='Date', y=['TandoorRate', 'BoilerRate', 'EggRate'])
        
        # 3. Advanced Prediction (Polynomial Regression)
        st.subheader("Rate Prediction (Next Day)")
        
        # Prepare data for prediction
        df_rates['DateOrdinal'] = df_rates['Date'].map(pd.Timestamp.toordinal)
        
        # We need enough data points
        if len(df_rates) >= 5:
            X = df_rates['DateOrdinal'].values
            next_day_ordinal = (df_rates['Date'].max() + timedelta(days=1)).toordinal()
            
            def predict_next(y_values):
                # Fit a 2nd degree polynomial
                coeffs = np.polyfit(X, y_values, 2)
                poly = np.poly1d(coeffs)
                return poly(next_day_ordinal)

            pred_tandoor = predict_next(df_rates['TandoorRate'].values)
            pred_boiler = predict_next(df_rates['BoilerRate'].values)
            pred_egg = predict_next(df_rates['EggRate'].values)
            
            p_col1, p_col2, p_col3 = st.columns(3)
            p_col1.metric("Predicted Tandoor", f"₹{pred_tandoor:.2f}")
            p_col2.metric("Predicted Boiler", f"₹{pred_boiler:.2f}")
            p_col3.metric("Predicted Egg", f"₹{pred_egg:.2f}")
            st.caption("Prediction based on Polynomial Regression (Degree 2). Model updates automatically with new data.")
        else:
            st.warning("Need at least 5 days of data for accurate prediction.")
    else:
        st.info("No rate data available for trends.")
        
    conn.close()

def render_variance_tab():
    st.subheader("Variance & Pilferage Analysis")
    
    conn = get_db_connection()
    
    # Fetch all bill entries with variance
    query = """
        SELECT Date, SupplierName, ItemName, ExpectedRate, VendorRate, Variance, (Variance/ExpectedRate)*100 as VariancePct
        FROM BillEntries 
        WHERE Variance != 0
        ORDER BY Date DESC
    """
    df_var = pd.read_sql_query(query, conn)
    conn.close()
    
    if df_var.empty:
        st.info("No variance records found.")
        return
        
    # Filter options
    vendors = df_var['SupplierName'].unique()
    selected_vendor = st.selectbox("Filter by Vendor", ["All"] + list(vendors))
    
    if selected_vendor != "All":
        df_var = df_var[df_var['SupplierName'] == selected_vendor]
        
    # Chart
    st.bar_chart(df_var, x='Date', y='Variance', color='SupplierName')
    
    # Detailed Table
    st.dataframe(
        df_var,
        column_config={
            "Variance": st.column_config.NumberColumn(format="₹%.2f"),
            "VariancePct": st.column_config.NumberColumn("Variance %", format="%.1f%%"),
            "ExpectedRate": st.column_config.NumberColumn(format="₹%.2f"),
            "VendorRate": st.column_config.NumberColumn(format="₹%.2f"),
        },
        use_container_width=True,
        hide_index=True
    )

def render_history_tab():
    st.subheader("Historical Rate Data")
    st.info("You can edit historical rates here. Note: This does NOT automatically recalculate old bills.")
    
    conn = get_db_connection()
    df_history = pd.read_sql_query("SELECT Date, TandoorRate, BoilerRate, EggRate FROM RawData ORDER BY Date DESC", conn)
    conn.close()
    
    edited_history = st.data_editor(
        df_history,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="history_editor"
    )
    
    if st.button("Save Historical Data"):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Full replace strategy for simplicity
            cursor.execute("DELETE FROM RawData")
            
            data_to_insert = []
            for _, row in edited_history.iterrows():
                if row['Date']:
                    data_to_insert.append((
                        row['Date'], row['TandoorRate'], row['BoilerRate'], row['EggRate']
                    ))
            
            cursor.executemany("INSERT INTO RawData (Date, TandoorRate, BoilerRate, EggRate) VALUES (?, ?, ?, ?)", data_to_insert)
            conn.commit()
            conn.close()
            st.success("Historical data updated.")
            st.rerun()
        except Exception as e:
            st.error(f"Error saving history: {e}")
