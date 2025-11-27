import streamlit as st
import utils

# --- Page Config ---
st.set_page_config(
    page_title="Zohra Management App",
    page_icon="🐔",
    layout="wide",
    initial_sidebar_state="expanded"
)

utils.apply_styling()

st.title("🐔 Zohra Management App")

st.markdown("""
### Welcome!
Select a module from the sidebar to get started.

#### Available Modules:
- **Chicken Rates**: Manage daily market rates.
- **Bill Entry**: Record daily purchases and verify variances.
- **Vendor Management**: Manage suppliers and markup rules.
- **Chicken Dashboard**: View trends and outstanding dues.

*More modules coming soon (Attendance, Salary, Sales & Expenses).*
""")

st.sidebar.success("Select a page above.")
