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

        /* Main Container - Clean white background */
        .main .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
            background-color: #ffffff;
        }

        /* Sidebar - Professional dark blue */
        [data-testid="stSidebar"] {
            background-color: #1a365d;
            border-right: 2px solid #2d3748;
        }
        [data-testid="stSidebar"] h1 {
            color: #ffffff;
            font-weight: 700;
            font-size: 1.5rem;
        }
        [data-testid="stSidebar"] .css-17lntkn {
            color: #ffffff;
        }
        [data-testid="stSidebar"] a {
            color: #ffffff !important;
            font-weight: 500;
        }
        [data-testid="stSidebar"] a:hover {
            color: #fbbf24 !important;
            background-color: #2c5282;
        }

        /* Tabs - Clear visual distinction */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #f7fafc;
            border-bottom: 3px solid #cbd5e0;
            padding-bottom: 0px;
        }
        .stTabs [data-baseweb="tab"] {
            height: 50px;
            white-space: pre-wrap;
            background-color: #e2e8f0;
            border-radius: 8px 8px 0px 0px;
            gap: 1px;
            padding: 12px 24px;
            color: #000000;
            font-weight: 600;
            font-size: 1rem;
            border: none;
            transition: all 0.2s ease;
        }
        .stTabs [data-baseweb="tab"]:hover {
            background-color: #cbd5e0;
            color: #000000;
        }
        .stTabs [aria-selected="true"] {
            background-color: #2b6cb0 !important;
            color: #ffffff !important;
            border-bottom: 4px solid #1a365d;
            box-shadow: 0 4px 12px rgba(43, 108, 176, 0.4);
            font-weight: 700;
        }

        /* Metrics - High contrast cards */
        [data-testid="stMetric"] {
            background-color: #ffffff;
            padding: 20px;
            border-radius: 12px;
            border: 2px solid #cbd5e0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        [data-testid="stMetricLabel"] {
            color: #2d3748;
            font-size: 1rem;
            font-weight: 600;
        }
        [data-testid="stMetricValue"] {
            color: #000000;
            font-weight: 700;
            font-size: 1.75rem;
        }

        /* Buttons - Vibrant and clear */
        .stButton button {
            background-color: #2b6cb0;
            color: #ffffff;
            border: none;
            border-radius: 8px;
            padding: 0.75rem 1.75rem;
            font-weight: 700;
            font-size: 1rem;
            transition: all 0.2s;
            box-shadow: 0 4px 10px rgba(43, 108, 176, 0.3);
        }
        .stButton button:hover {
            background-color: #1a365d;
            color: #ffffff;
            border: none;
            box-shadow: 0 6px 16px rgba(43, 108, 176, 0.5);
            transform: translateY(-2px);
        }
        /* Primary Buttons - Green for success actions */
        .stButton button[kind="primary"] {
            background-color: #38a169;
            box-shadow: 0 4px 10px rgba(56, 161, 105, 0.3);
        }
        .stButton button[kind="primary"]:hover {
            background-color: #2f855a;
            box-shadow: 0 6px 16px rgba(56, 161, 105, 0.5);
        }
        /* Form Buttons */
        div[data-testid="stForm"] .stButton button {
            width: 100%;
        }

        /* Inputs - Clear borders and dark text */
        .stTextInput input, .stNumberInput input, .stDateInput input, .stSelectbox div[data-baseweb="select"] {
            border-radius: 8px;
            border: 2px solid #cbd5e0;
            font-size: 1rem;
            color: #000000;
            background-color: #ffffff;
            font-weight: 500;
        }
        .stTextInput input:focus, .stNumberInput input:focus {
            border-color: #2b6cb0;
            box-shadow: 0 0 0 3px rgba(43, 108, 176, 0.2);
        }
        .stTextInput label, .stNumberInput label, .stDateInput label, .stSelectbox label {
            color: #000000;
            font-weight: 700;
            font-size: 1rem;
        }

        /* Data Editor/Tables - Dark headers, readable content */
        [data-testid="stDataFrame"] {
            border: 2px solid #cbd5e0;
            border-radius: 10px;
            overflow: hidden;
        }
        [data-testid="stDataFrame"] th {
            background-color: #1a365d !important;
            color: #ffffff !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
        }
        [data-testid="stDataFrame"] td {
            color: #000000 !important;
            font-weight: 500 !important;
        }
        
        /* Headers - Strong black text */
        h1, h2, h3 {
            color: #000000;
            font-weight: 700;
        }
        h1 {
            font-size: 2.25rem;
            border-bottom: 4px solid #2b6cb0;
            padding-bottom: 0.75rem;
            margin-bottom: 1.5rem;
        }
        h2 {
            font-size: 1.75rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            color: #1a202c;
        }
        h3 {
            font-size: 1.35rem;
            margin-top: 1.25rem;
            margin-bottom: 0.75rem;
            color: #2d3748;
        }
        
        /* Alerts - High contrast with dark text */
        .stAlert {
            border-radius: 10px;
            border-left: 5px solid;
            font-weight: 600;
            color: #000000;
        }
        div[data-baseweb="notification"][kind="info"] {
            background-color: #bee3f8;
            border-left-color: #2b6cb0;
            color: #1a365d;
        }
        div[data-baseweb="notification"][kind="success"] {
            background-color: #c6f6d5;
            border-left-color: #38a169;
            color: #22543d;
        }
        div[data-baseweb="notification"][kind="warning"] {
            background-color: #feebc8;
            border-left-color: #dd6b20;
            color: #7c2d12;
        }
        div[data-baseweb="notification"][kind="error"] {
            background-color: #fed7d7;
            border-left-color: #e53e3e;
            color: #742a2a;
        }

        /* Expander - Clear contrast */
        .streamlit-expanderHeader {
            background-color: #edf2f7;
            border: 2px solid #cbd5e0;
            border-radius: 8px;
            color: #000000;
            font-weight: 700;
        }
        .streamlit-expanderHeader:hover {
            background-color: #e2e8f0;
        }

        /* General text - Ensure all text is dark */
        p, span, div {
            color: #1a202c;
        }
    </style>
    """, unsafe_allow_html=True)


