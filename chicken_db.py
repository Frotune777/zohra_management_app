import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

DB_NAME = 'chicken_tracker.db'

def get_db_connection():
    return sqlite3.connect(DB_NAME)

def initialize_db():
    """Ensures all necessary tables exist in the database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Suppliers Table (Renamed from Vendors to match vendor_management.py)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Suppliers (
            SupplierID INTEGER PRIMARY KEY,
            SupplierName TEXT UNIQUE NOT NULL,
            PhoneNumber TEXT,
            PreferredPaymentType TEXT,
            PaymentFrequency TEXT,
            VendorType TEXT NOT NULL,
            MarkupRequired INTEGER DEFAULT 1,
            LastUpdated TEXT
        )
    """)

    # 2. MarkupRules Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Markups (
            ItemID INTEGER PRIMARY KEY,
            SupplierName TEXT NOT NULL,
            ItemName TEXT NOT NULL,
            BaseRateType TEXT NOT NULL, -- e.g., 'TandoorRate'
            MarkupOperator1 TEXT, -- '+', '-', '*', '/'
            MarkupValue1 REAL,
            MarkupOperator2 TEXT, 
            MarkupValue2 REAL,
            UNIQUE (SupplierName, ItemName),
            FOREIGN KEY (SupplierName) REFERENCES Suppliers(SupplierName)
        )
    """)

    # 3. RawData Table (Daily Paper Rates)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS RawData (
            Date TEXT PRIMARY KEY,
            TandoorRate REAL NOT NULL,
            BoilerRate REAL NOT NULL,
            EggRate REAL NOT NULL
        )
    """)
    
    # 4. BillEntries Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS BillEntries (
            ID INTEGER PRIMARY KEY,
            Date TEXT NOT NULL,
            SupplierName TEXT NOT NULL,
            ItemName TEXT NOT NULL,
            Qty REAL NOT NULL,
            VendorRate REAL NOT NULL,
            ExpectedRate REAL NOT NULL,
            Variance REAL NOT NULL,
            Status TEXT NOT NULL,
            FOREIGN KEY (SupplierName) REFERENCES Suppliers(SupplierName),
            UNIQUE (Date, SupplierName, ItemName)
        )
    """)

    # 5. VendorLedger Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS VendorLedger (
            ID INTEGER PRIMARY KEY,
            Date TEXT NOT NULL,
            SupplierName TEXT NOT NULL,
            TransactionType TEXT NOT NULL,
            Amount REAL NOT NULL,
            Details TEXT,
            FOREIGN KEY (SupplierName) REFERENCES Suppliers(SupplierName)
        )
    """)

    conn.commit()
    conn.close()

# --- Vendor/Supplier Utilities ---

def fetch_suppliers_and_items():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Changed table name to Suppliers
    cursor.execute("SELECT SupplierName FROM Suppliers ORDER BY SupplierName")
    suppliers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return suppliers, {}

def fetch_vendor_type(vendor_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Changed table name to Suppliers and column to VendorType
    cursor.execute("SELECT VendorType FROM Suppliers WHERE SupplierName = ?", (vendor_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def delete_vendor_and_cleanup(supplier_id, supplier_name):
    """
    Deletes a vendor and cascades the deletion to Markups, BillEntries, 
    and VendorLedger to maintain DB integrity.
    """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        # 1. Delete Ledger Entries
        cursor.execute("DELETE FROM VendorLedger WHERE SupplierName = ?", (supplier_name,))
        # 2. Delete Bill Entries
        cursor.execute("DELETE FROM BillEntries WHERE SupplierName = ?", (supplier_name,))
        # 3. Delete Markup Rules
        cursor.execute("DELETE FROM Markups WHERE SupplierName = ?", (supplier_name,))
        # 4. Delete the Supplier
        cursor.execute("DELETE FROM Suppliers WHERE SupplierID = ?", (supplier_id,))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting vendor: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def insert_default_markups(vendor_name, default_rules):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    rules_to_insert = []
    # Adapting default rules to the schema used in vendor_management.py
    # Schema: SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2
    for rule in default_rules:
        # rule structure from vendor_management: (ItemName, BaseRateType, Op1, Val1, Op2, Val2)
        rules_to_insert.append((
            vendor_name, 
            rule[0], # ItemName
            rule[1], # BaseRateType
            rule[2], # Op1
            rule[3], # Val1
            rule[4], # Op2
            rule[5]  # Val2
        ))

    try:
        cursor.executemany("""
            INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rules_to_insert)
        conn.commit()
        return True
    except Exception as e:
        print(f"Error inserting default markups: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def fetch_items_for_supplier(supplier_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT ItemName FROM Markups WHERE SupplierName = ? ORDER BY ItemName", (supplier_name,))
    items = [row[0] for row in cursor.fetchall()]
    conn.close()
    return items

# --- Rate Calculation Utilities ---

def fetch_rate_and_rule(date, supplier_name, item_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # 1. Fetch Raw Rates
    cursor.execute("SELECT TandoorRate, BoilerRate, EggRate FROM RawData WHERE Date = ?", (date,))
    raw_rates = cursor.fetchone() 

    # 2. Fetch Markup Rule (Matching schema in vendor_management.py)
    cursor.execute("""
        SELECT BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2
        FROM Markups 
        WHERE SupplierName = ? AND ItemName = ?
    """, (supplier_name, item_name))
    rule = cursor.fetchone() 

    conn.close()
    return raw_rates, rule

def calculate_expected_rate(raw_rates, rule):
    """
    Calculates rate based on dynamic operators.
    raw_rates: (Tandoor, Boiler, Egg)
    rule: (BaseType, Op1, Val1, Op2, Val2)
    """
    if not raw_rates or not rule:
        return 0.0

    Tandoor, Boiler, Egg = raw_rates
    BaseType, Op1, Val1, Op2, Val2 = rule
    
    # Determine Base
    rate = 0.0
    if BaseType == 'TandoorRate': rate = Tandoor
    elif BaseType == 'BoilerRate': rate = Boiler
    elif BaseType == 'EggRate': rate = Egg
    
    # Helper to apply math
    def apply_op(current_val, op, operand):
        if operand is None: return current_val
        if op == '+': return current_val + operand
        if op == '-': return current_val - operand
        if op == '*': return current_val * operand
        if op == '/': return current_val / operand if operand != 0 else current_val
        return current_val

    # Apply Op1
    rate = apply_op(rate, Op1, Val1)
    
    # Apply Op2 (if exists)
    if Op2 and Val2 is not None:
        rate = apply_op(rate, Op2, Val2)

    return round(max(0.0, rate), 2)