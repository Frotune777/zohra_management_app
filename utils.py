import streamlit as st
import sqlite3
import chicken_db

def get_db_connection():
    return sqlite3.connect(chicken_db.DB_NAME)

def apply_styling():
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
