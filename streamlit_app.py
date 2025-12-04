import streamlit as st
import chicken_db

st.set_page_config(
    page_title="Chicken Rate & Bill Tracker",
    layout="wide"
)

# Initialize database
chicken_db.initialize_db()

st.title("🐔 Chicken Rate & Billing Tracker")

tabs = st.tabs([
    "Daily Rates",
    "Daily Bill Entry",
    "Vendor Management",
    "Dashboard / Reports"
])

with tabs[0]:
    import views.daily_rates as daily_rates
    daily_rates.render()

with tabs[1]:
    import views.bill_entry as bill_entry
    bill_entry.render()

with tabs[2]:
    import views.vendor_management as vendor_management
    vendor_management.render()

with tabs[3]:
    import views.dashboard as dashboard
    dashboard.render()
