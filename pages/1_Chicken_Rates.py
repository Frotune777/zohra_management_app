import streamlit as st
from datetime import datetime
import sys
import os

# Add parent directory to path to import chicken_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db
import utils

# Apply styling
utils.apply_styling()

st.header("Daily Rate Entry")

col1, col2 = st.columns([1, 2])

with col1:
    date_val = st.date_input("Select Date", datetime.now())
    date_str = date_val.strftime("%Y-%m-%d")
    
    # Load existing rates
    conn = utils.get_db_connection()
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
                conn = utils.get_db_connection()
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
