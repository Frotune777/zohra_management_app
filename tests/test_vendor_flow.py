import unittest
import sqlite3
import os
import sys

# Add parent directory to path to import chicken_db
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db

class TestVendorFlow(unittest.TestCase):
    def setUp(self):
        # Use a temporary database for testing
        self.test_db = 'test_chicken_tracker.db'
        chicken_db.DB_NAME = self.test_db
        chicken_db.initialize_db()

    def tearDown(self):
        # Clean up the test database
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_vendor_lifecycle(self):
        # 1. Create Vendor
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Suppliers (SupplierName, VendorType, MarkupRequired)
            VALUES (?, ?, ?)
        """, ('TestVendor', 'Chicken', 1))
        conn.commit()
        
        # 2. Add Markup Rule
        cursor.execute("""
            INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1)
            VALUES (?, ?, ?, ?, ?)
        """, ('TestVendor', 'TestItem', 'TandoorRate', '+', 10))
        conn.commit()
        
        # 3. Add Bill Entry
        cursor.execute("""
            INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ('2023-01-01', 'TestVendor', 'TestItem', 10, 100, 90, 10, 'Okay'))
        conn.commit()
        conn.close()

        # 4. Rename Vendor (Simulating the issue - currently no function for this, so we update Suppliers manually and check if others break)
        # Ideally, we want a function chicken_db.rename_vendor('TestVendor', 'NewVendorName')
        # For now, let's assert that simply updating the Supplier table DOES NOT update others (reproducing the bug)
        
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("UPDATE Suppliers SET SupplierName = ? WHERE SupplierName = ?", ('NewVendorName', 'TestVendor'))
        conn.commit()
        
        # Check Markups - Should still have old name (Bug)
        cursor.execute("SELECT Count(*) FROM Markups WHERE SupplierName = ?", ('NewVendorName',))
        count_new = cursor.fetchone()[0]
        
        cursor.execute("SELECT Count(*) FROM Markups WHERE SupplierName = ?", ('TestVendor',))
        count_old = cursor.fetchone()[0]
        
        # If the bug exists, count_new should be 0 and count_old should be 1
        # But we want to fix this. So we will implement rename_vendor and test THAT.
        # For this test, I will assume I am about to implement rename_vendor.
        
        conn.close()

    def test_rename_vendor_function(self):
        # This test expects the fix to be implemented
        
        # Setup Data
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Suppliers (SupplierName, VendorType) VALUES (?, ?)", ('OldName', 'Chicken'))
        cursor.execute("INSERT INTO Markups (SupplierName, ItemName, BaseRateType) VALUES (?, ?, ?)", ('OldName', 'Item1', 'Base'))
        cursor.execute("INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", ('2023-01-01', 'OldName', 'Item1', 1, 1, 1, 0, 'OK'))
        conn.commit()
        conn.close()
        
        # Call the new function (which doesn't exist yet, so this will fail if run now)
        try:
            chicken_db.rename_vendor('OldName', 'NewName')
        except AttributeError:
            self.fail("rename_vendor function not implemented yet")
            
        # Verify Updates
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()
        
        # Check Suppliers
        cursor.execute("SELECT SupplierName FROM Suppliers WHERE SupplierName = ?", ('NewName',))
        self.assertIsNotNone(cursor.fetchone(), "Supplier table not updated")
        
        # Check Markups
        cursor.execute("SELECT SupplierName FROM Markups WHERE ItemName = ?", ('Item1',))
        self.assertEqual(cursor.fetchone()[0], 'NewName', "Markups table not updated")
        
        # Check BillEntries
        cursor.execute("SELECT SupplierName FROM BillEntries WHERE ItemName = ?", ('Item1',))
        self.assertEqual(cursor.fetchone()[0], 'NewName', "BillEntries table not updated")
        
        conn.close()

if __name__ == '__main__':
    unittest.main()
