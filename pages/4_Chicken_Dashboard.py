import streamlit as st
import pandas as pd
import sys
import os

# Add parent directory to path to import chicken_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db
import utils

# Apply styling
utils.apply_styling()

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
