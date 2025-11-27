import streamlit as st
import utils

# --- Page Config ---
st.set_page_config(
    page_title="Zohra Management App",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="collapsed"
)

utils.apply_styling()

# Custom CSS for better dark theme visibility and horizontal navigation
st.markdown("""
<style>
    /* Hide sidebar */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Improve text visibility in dark theme */
    .stMarkdown, .stText, p, span, div {
        color: #e0e0e0 !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    
    /* Better contrast for metrics */
    [data-testid="stMetricLabel"] {
        color: #b0b0b0 !important;
    }
    
    [data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    
    /* Improve form labels */
    label {
        color: #e0e0e0 !important;
    }
    
    /* Better table text */
    .dataframe {
        color: #e0e0e0 !important;
    }
</style>
""", unsafe_allow_html=True)

st.title("🐔 Zohra Restaurant Management")

# Horizontal Navigation
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs([
    "🏠 Home",
    "📊 Chicken Rates",
    "🧾 Bill Entry",
    "👥 Vendors",
    "📈 Chicken Dashboard",
    "💰 Sales & Expenses",
    "👤 Attendance",
    "💵 Salary & Advances",
    "💼 P&L Dashboard"
])

with tab1:
    st.markdown("""
    ### Welcome to Zohra Restaurant Management System!
    
    This comprehensive system helps you manage all aspects of your restaurant operations:
    
    #### 📊 Chicken Management
    - **Daily Rates**: Track market rates for Tandoor, Boiler, and Egg
    - **Bill Entry**: Record purchases with automatic variance calculation
    - **Vendor Management**: Manage suppliers and markup rules
    - **Dashboard**: Visualize trends and outstanding dues
    
    #### 💼 Restaurant Operations
    - **Sales & Expenses**: Track daily sales and expenses
    - **Attendance**: Manage employee attendance
    - **Salary & Advances**: Calculate salaries with 28-day delay rule
    - **P&L Dashboard**: Comprehensive profit & loss analysis
    
    **Select a tab above to get started!**
    """)

with tab2:
    exec(open("pages/1_Chicken_Rates.py").read())

with tab3:
    exec(open("pages/2_Bill_Entry.py").read())

with tab4:
    exec(open("pages/3_Vendor_Management.py").read())

with tab5:
    exec(open("pages/4_Chicken_Dashboard.py").read())

with tab6:
    exec(open("pages/5_Daily_Sales_Expense.py").read())

with tab7:
    exec(open("pages/6_Attendance.py").read())

with tab8:
    exec(open("pages/8_Salary_Advances.py").read())

with tab9:
    exec(open("pages/7_PnL_Dashboard.py").read())
