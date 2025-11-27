"""
Unit tests for utils.py module
Tests database connection and utility functions
"""

import unittest
import sqlite3
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db
import utils


class TestDatabaseConnection(unittest.TestCase):
    """Test database connection utilities"""
    
    def setUp(self):
        """Set up test database"""
        self.test_db = 'test_chicken_tracker.db'
        chicken_db.DB_NAME = self.test_db
        chicken_db.initialize_db()
        
    def tearDown(self):
        """Clean up test database"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
    
    def test_get_db_connection_returns_connection(self):
        """Test that get_db_connection returns a valid SQLite connection"""
        conn = utils.get_db_connection()
        
        self.assertIsInstance(conn, sqlite3.Connection)
        
        # Test that we can execute a query
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        self.assertGreater(len(tables), 0)
        
        conn.close()
    
    def test_get_db_connection_uses_correct_database(self):
        """Test that get_db_connection uses the correct database file"""
        conn = utils.get_db_connection()
        
        # Check that the connection is to our test database
        cursor = conn.cursor()
        cursor.execute("PRAGMA database_list")
        db_info = cursor.fetchone()
        
        # The database name should contain our test db name
        self.assertIn('test_chicken_tracker', db_info[2])
        
        conn.close()


if __name__ == '__main__':
    unittest.main()
