"""
Integration tests for business logic
Tests bill entry workflow and vendor ledger integration
"""

import unittest
import sqlite3
import os
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db


class TestBillEntryWorkflow(unittest.TestCase):
    """Test bill entry workflow"""
    
    def setUp(self):
        """Set up test database with vendor and rates"""
        self.test_db = 'test_chicken_tracker.db'
        chicken_db.DB_NAME = self.test_db
        chicken_db.initialize_db()
        
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Add vendor
        cursor.execute("""
            INSERT INTO Suppliers (SupplierName, VendorType, MarkupRequired)
            VALUES (?, ?, ?)
        """, ('TestVendor', 'Chicken', 1))
        
        # Add rate
        cursor.execute("""
            INSERT INTO RawData (Date, TandoorRate, BoilerRate, EggRate)
            VALUES (?, ?, ?, ?)
        """, ('2023-01-01', 100, 90, 80))
        
        # Add markup rule
        cursor.execute("""
            INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1)
            VALUES (?, ?, ?, ?, ?)
        """, ('TestVendor', 'Chicken', 'TandoorRate', '+', 10))
        
        conn.commit()
        conn.close()
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_bill_entry_with_variance(self):
        """Test bill entry with variance calculation"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Calculate expected rate
        raw_rates, rule = chicken_db.fetch_rate_and_rule('2023-01-01', 'TestVendor', 'Chicken')
        expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
        
        # Add bill entry
        vendor_rate = 115
        variance = vendor_rate - expected_rate
        status = 'High' if variance > 5 else 'Okay'
        
        cursor.execute("""
            INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('2023-01-01', 'TestVendor', 'Chicken', 10, vendor_rate, expected_rate, variance, status))
        
        # Update vendor ledger
        total_amount = 10 * vendor_rate
        cursor.execute("""
            INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount)
            VALUES (?, ?, ?, ?)
        """, ('2023-01-01', 'TestVendor', 'Bill', total_amount))
        
        conn.commit()
        
        # Verify bill entry
        cursor.execute("""
            SELECT Variance, Status FROM BillEntries 
            WHERE Date = ? AND SupplierName = ?
        """, ('2023-01-01', 'TestVendor'))
        
        result = cursor.fetchone()
        
        self.assertEqual(result[0], 5)  # 115 - 110
        self.assertEqual(result[1], 'Okay')
        
        # Verify ledger
        cursor.execute("""
            SELECT Amount FROM VendorLedger 
            WHERE SupplierName = ? AND TransactionType = ?
        """, ('TestVendor', 'Bill'))
        
        ledger_result = cursor.fetchone()
        conn.close()
        
        self.assertEqual(ledger_result[0], 1150)  # 10 * 115
    
    def test_multiple_bill_entries_same_date(self):
        """Test multiple bill entries for different items on same date"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Add another markup rule
        cursor.execute("""
            INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1)
            VALUES (?, ?, ?, ?, ?)
        """, ('TestVendor', 'Boneless', 'TandoorRate', '+', 95))
        
        conn.commit()
        
        # Add bill entries for both items
        items = [
            ('Chicken', 10, 110),
            ('Boneless', 5, 200)
        ]
        
        for item_name, qty, vendor_rate in items:
            raw_rates, rule = chicken_db.fetch_rate_and_rule('2023-01-01', 'TestVendor', item_name)
            expected_rate = chicken_db.calculate_expected_rate(raw_rates, rule)
            variance = vendor_rate - expected_rate
            status = 'High' if abs(variance) > 5 else 'Okay'
            
            cursor.execute("""
                INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ('2023-01-01', 'TestVendor', item_name, qty, vendor_rate, expected_rate, variance, status))
        
        conn.commit()
        
        # Verify both entries exist
        cursor.execute("""
            SELECT COUNT(*) FROM BillEntries 
            WHERE Date = ? AND SupplierName = ?
        """, ('2023-01-01', 'TestVendor'))
        
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 2)
    
    def test_vendor_ledger_balance(self):
        """Test vendor ledger balance calculation"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Add bill entries
        cursor.execute("""
            INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('2023-01-01', 'TestVendor', 'Chicken', 10, 110, 110, 0, 'Okay'))
        
        # Add ledger entry for bill
        cursor.execute("""
            INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount)
            VALUES (?, ?, ?, ?)
        """, ('2023-01-01', 'TestVendor', 'Bill', 1100))
        
        # Add payment
        cursor.execute("""
            INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount)
            VALUES (?, ?, ?, ?)
        """, ('2023-01-02', 'TestVendor', 'Payment', -500))
        
        conn.commit()
        
        # Calculate balance
        cursor.execute("""
            SELECT SUM(Amount) FROM VendorLedger 
            WHERE SupplierName = ?
        """, ('TestVendor',))
        
        balance = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(balance, 600)  # 1100 - 500


if __name__ == '__main__':
    unittest.main()
