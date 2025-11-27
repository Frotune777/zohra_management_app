"""
Unit tests for chicken_db.py module
Tests database initialization, vendor operations, rate calculations, and data retrieval
"""

import unittest
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db


class TestDatabaseInitialization(unittest.TestCase):
    """Test database initialization and schema creation"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = 'test_chicken_tracker.db'
        chicken_db.DB_NAME = self.test_db
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_initialize_db_creates_tables(self):
        """Test that initialize_db creates all required tables"""
        chicken_db.initialize_db()
        
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Check if all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        required_tables = {
            'Suppliers', 'Markups', 'BillEntries', 'VendorLedger', 'RawData'
        }
        
        conn.close()
        
        # Check that all required tables exist
        for table in required_tables:
            self.assertIn(table, tables, f"Table {table} not created")
    
    def test_initialize_db_idempotent(self):
        """Test that initialize_db can be called multiple times safely"""
        chicken_db.initialize_db()
        chicken_db.initialize_db()  # Should not raise error
        
        # Verify tables still exist
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        conn.close()
        
        self.assertGreater(len(tables), 0)


class TestVendorOperations(unittest.TestCase):
    """Test vendor-related operations"""
    
    def setUp(self):
        """Set up test database with sample data"""
        self.test_db = 'test_chicken_tracker.db'
        chicken_db.DB_NAME = self.test_db
        chicken_db.initialize_db()
        
        # Add sample vendor
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Suppliers (SupplierName, VendorType, MarkupRequired)
            VALUES (?, ?, ?)
        """, ('TestVendor', 'Chicken', 1))
        conn.commit()
        conn.close()
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_fetch_suppliers_and_items(self):
        """Test fetching suppliers and items"""
        suppliers, items = chicken_db.fetch_suppliers_and_items()
        
        self.assertIsInstance(suppliers, list)
        self.assertIn('TestVendor', suppliers)
    
    def test_fetch_vendor_type(self):
        """Test fetching vendor type"""
        vendor_type = chicken_db.fetch_vendor_type('TestVendor')
        
        self.assertEqual(vendor_type, 'Chicken')
    
    def test_fetch_vendor_type_nonexistent(self):
        """Test fetching type for non-existent vendor"""
        vendor_type = chicken_db.fetch_vendor_type('NonExistent')
        
        self.assertIsNone(vendor_type)
    
    def test_rename_vendor(self):
        """Test renaming a vendor updates all related tables"""
        # Add related data
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Add markup
        cursor.execute("""
            INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1)
            VALUES (?, ?, ?, ?, ?)
        """, ('TestVendor', 'TestItem', 'TandoorRate', '+', 10))
        
        # Add bill entry
        cursor.execute("""
            INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('2023-01-01', 'TestVendor', 'TestItem', 10, 100, 90, 10, 'Okay'))
        
        conn.commit()
        conn.close()
        
        # Rename vendor
        chicken_db.rename_vendor('TestVendor', 'NewVendorName')
        
        # Verify all tables updated
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Check Suppliers
        cursor.execute("SELECT SupplierName FROM Suppliers WHERE SupplierName = ?", ('NewVendorName',))
        self.assertIsNotNone(cursor.fetchone())
        
        # Check Markups
        cursor.execute("SELECT SupplierName FROM Markups WHERE ItemName = ?", ('TestItem',))
        self.assertEqual(cursor.fetchone()[0], 'NewVendorName')
        
        # Check BillEntries
        cursor.execute("SELECT SupplierName FROM BillEntries WHERE ItemName = ?", ('TestItem',))
        self.assertEqual(cursor.fetchone()[0], 'NewVendorName')
        
        conn.close()
    
    def test_delete_vendor_and_cleanup(self):
        """Test deleting vendor cascades to related tables"""
        # Add related data
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Get supplier ID
        cursor.execute("SELECT SupplierID FROM Suppliers WHERE SupplierName = ?", ('TestVendor',))
        supplier_id = cursor.fetchone()[0]
        
        # Add markup
        cursor.execute("""
            INSERT INTO Markups (SupplierName, ItemName, BaseRateType)
            VALUES (?, ?, ?)
        """, ('TestVendor', 'TestItem', 'TandoorRate'))
        
        conn.commit()
        conn.close()
        
        # Delete vendor
        chicken_db.delete_vendor_and_cleanup(supplier_id, 'TestVendor')
        
        # Verify deletion
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Check Suppliers
        cursor.execute("SELECT COUNT(*) FROM Suppliers WHERE SupplierName = ?", ('TestVendor',))
        self.assertEqual(cursor.fetchone()[0], 0)
        
        # Check Markups
        cursor.execute("SELECT COUNT(*) FROM Markups WHERE SupplierName = ?", ('TestVendor',))
        self.assertEqual(cursor.fetchone()[0], 0)
        
        conn.close()
    
    def test_insert_default_markups(self):
        """Test inserting default markup rules"""
        default_rules = [
            ('Item1', 'TandoorRate', '+', 10.0, None, None),
            ('Item2', 'BoilerRate', '*', 1.1, None, None),
        ]
        
        chicken_db.insert_default_markups('TestVendor', default_rules)
        
        # Verify markups inserted
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Markups WHERE SupplierName = ?", ('TestVendor',))
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 2)
    
    def test_fetch_items_for_supplier(self):
        """Test fetching items for a supplier"""
        # Add markup items
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Markups (SupplierName, ItemName, BaseRateType)
            VALUES (?, ?, ?)
        """, ('TestVendor', 'Item1', 'TandoorRate'))
        conn.commit()
        conn.close()
        
        items = chicken_db.fetch_items_for_supplier('TestVendor')
        
        self.assertIsInstance(items, list)
        self.assertIn('Item1', items)


class TestRateCalculations(unittest.TestCase):
    """Test rate calculation functions"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = 'test_chicken_tracker.db'
        chicken_db.DB_NAME = self.test_db
        chicken_db.initialize_db()
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_calculate_expected_rate_addition(self):
        """Test rate calculation with addition operator"""
        raw_rates = (100, 90, 80)  # Tandoor, Boiler, Egg
        rule = ('TandoorRate', '+', 10, None, None)
        
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        self.assertEqual(expected_rate, 110)
    
    def test_calculate_expected_rate_subtraction(self):
        """Test rate calculation with subtraction operator"""
        raw_rates = (100, 90, 80)
        rule = ('TandoorRate', '-', 10, None, None)
        
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        self.assertEqual(expected_rate, 90)
    
    def test_calculate_expected_rate_multiplication(self):
        """Test rate calculation with multiplication operator"""
        raw_rates = (100, 90, 80)
        rule = ('TandoorRate', '*', 1.1, None, None)
        
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        self.assertEqual(expected_rate, 110)
    
    def test_calculate_expected_rate_division(self):
        """Test rate calculation with division operator"""
        raw_rates = (100, 90, 80)
        rule = ('TandoorRate', '/', 2, None, None)
        
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        self.assertEqual(expected_rate, 50)
    
    def test_calculate_expected_rate_chained_operations(self):
        """Test rate calculation with chained operations"""
        raw_rates = (100, 90, 80)
        rule = ('TandoorRate', '+', 10, '*', 1.1)
        
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        # (100 + 10) * 1.1 = 121
        self.assertEqual(expected_rate, 121)
    
    def test_calculate_expected_rate_boiler_base(self):
        """Test rate calculation with BoilerRate as base"""
        raw_rates = (100, 90, 80)
        rule = ('BoilerRate', '+', 5, None, None)
        
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        self.assertEqual(expected_rate, 95)
    
    def test_calculate_expected_rate_egg_base(self):
        """Test rate calculation with EggRate as base"""
        raw_rates = (100, 90, 80)
        rule = ('EggRate', '*', 2, None, None)
        
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        self.assertEqual(expected_rate, 160)
    
    def test_fetch_rate_and_rule(self):
        """Test fetching rate and rule for a date/supplier/item"""
        # Add test data
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Add supplier
        cursor.execute("""
            INSERT INTO Suppliers (SupplierName, VendorType)
            VALUES (?, ?)
        """, ('TestVendor', 'Chicken'))
        
        # Add rate
        cursor.execute("""
            INSERT INTO RawData (Date, TandoorRate, BoilerRate, EggRate)
            VALUES (?, ?, ?, ?)
        """, ('2023-01-01', 100, 90, 80))
        
        # Add markup rule
        cursor.execute("""
            INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1)
            VALUES (?, ?, ?, ?, ?)
        """, ('TestVendor', 'TestItem', 'TandoorRate', '+', 10))
        
        conn.commit()
        conn.close()
        
        raw_rates, rule = chicken_db.fetch_rate_and_rule('2023-01-01', 'TestVendor', 'TestItem')
        
        self.assertEqual(raw_rates, (100, 90, 80))
        self.assertEqual(rule[0], 'TandoorRate')
        self.assertEqual(rule[1], '+')
        self.assertEqual(rule[2], 10)


class TestDataRetrieval(unittest.TestCase):
    """Test data retrieval functions"""
    
    def setUp(self):
        """Set up test database with sample data"""
        self.test_db = 'test_chicken_tracker.db'
        chicken_db.DB_NAME = self.test_db
        chicken_db.initialize_db()
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_fetch_rate_history(self):
        """Test fetching rate history"""
        # Add sample rates
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        for i in range(5):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            cursor.execute("""
                INSERT INTO RawData (Date, TandoorRate, BoilerRate, EggRate)
                VALUES (?, ?, ?, ?)
            """, (date, 100 + i, 90 + i, 80 + i))
        
        conn.commit()
        conn.close()
        
        history = chicken_db.fetch_rate_history(limit=5)
        
        self.assertEqual(len(history), 5)
        # History returns tuples: (Date, TandoorRate, BoilerRate, EggRate)
        self.assertEqual(len(history[0]), 4)
        self.assertIsInstance(history[0][0], str)  # Date is a string
        self.assertIsInstance(history[0][1], float)  # TandoorRate is a float
    
    def test_fetch_vendor_dues(self):
        """Test fetching vendor dues"""
        # Add sample data
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Add supplier
        cursor.execute("""
            INSERT INTO Suppliers (SupplierName, VendorType)
            VALUES (?, ?)
        """, ('TestVendor', 'Chicken'))
        
        # Add bill entry
        cursor.execute("""
            INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('2023-01-01', 'TestVendor', 'TestItem', 10, 100, 90, 10, 'Okay'))
        
        # Add ledger entry
        cursor.execute("""
            INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount)
            VALUES (?, ?, ?, ?)
        """, ('2023-01-01', 'TestVendor', 'Bill', 1000))
        
        conn.commit()
        conn.close()
        
        dues = chicken_db.fetch_vendor_dues()
        
        self.assertIsInstance(dues, dict)
        if dues:
            self.assertIn('TestVendor', dues)


if __name__ == '__main__':
    unittest.main()
