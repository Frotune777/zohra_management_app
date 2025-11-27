# Developer Guide

This guide provides information for developers working on the Zohra Restaurant Management System.

## Table of Contents
- [Development Setup](#development-setup)
- [Code Structure](#code-structure)
- [Development Workflow](#development-workflow)
- [Adding New Features](#adding-new-features)
- [Database Migrations](#database-migrations)
- [Testing Guidelines](#testing-guidelines)
- [Coding Standards](#coding-standards)
- [Debugging](#debugging)

---

## Development Setup

### Environment Setup

1. **Clone and setup**:
   ```bash
   git clone \u003crepository-url\u003e
   cd management_app
   python -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Development dependencies** (optional):
   ```bash
   pip install pytest pytest-cov black flake8
   ```

3. **IDE Configuration**:
   - Recommended: VS Code with Python extension
   - Configure Python interpreter to use venv
   - Install Streamlit extension for better development experience

---

## Code Structure

### Module Organization

```
management_app/
├── Home.py                    # Entry point - minimal logic
├── pages/                     # Feature modules
│   └── [N]_[Feature].py      # Self-contained feature pages
├── chicken_db.py             # Database layer - all DB operations
├── utils.py                  # Shared utilities
└── tests/                    # Test suite
```

### Design Principles

1. **Separation of Concerns**:
   - UI logic in page modules
   - Database operations in `chicken_db.py`
   - Shared utilities in `utils.py`

2. **Single Responsibility**:
   - Each page module handles one feature
   - Each function does one thing well

3. **DRY (Don't Repeat Yourself)**:
   - Common database operations in `chicken_db.py`
   - Common styling in `utils.py`

---

## Development Workflow

### Running in Development Mode

```bash
# Run with auto-reload
streamlit run Home.py

# Run with specific port
streamlit run Home.py --server.port 8502

# Run with debug mode
streamlit run Home.py --logger.level=debug
```

### Hot Reload

Streamlit automatically reloads when you save files. However:
- Database schema changes require app restart
- `chicken_db.py` changes may need cache clearing

**Clear cache**:
```python
# In any page
st.cache_data.clear()
```

---

## Adding New Features

### Adding a New Page Module

1. **Create page file**:
   ```bash
   touch pages/9_New_Feature.py
   ```

2. **Basic template**:
   ```python
   import streamlit as st
   import sys
   import os
   
   sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   
   import chicken_db
   import utils
   
   utils.apply_styling()
   
   st.header("New Feature")
   
   # Your feature code here
   ```

3. **Add to navigation** in `Home.py`:
   ```python
   tab1, tab2, ..., tab_new = st.tabs([
       "🏠 Home",
       # ... existing tabs
       "🆕 New Feature"
   ])
   
   with tab_new:
       exec(open("pages/9_New_Feature.py").read())
   ```

### Adding Database Tables

1. **Update `chicken_db.py`**:
   ```python
   def initialize_db():
       # ... existing tables
       
       cursor.execute("""
           CREATE TABLE IF NOT EXISTS NewTable (
               ID INTEGER PRIMARY KEY,
               Field1 TEXT NOT NULL,
               Field2 REAL,
               CreatedAt TEXT DEFAULT CURRENT_TIMESTAMP
           )
       """)
   ```

2. **Add helper functions**:
   ```python
   def fetch_new_data():
       conn = sqlite3.connect(DB_NAME)
       cursor = conn.cursor()
       cursor.execute("SELECT * FROM NewTable")
       data = cursor.fetchall()
       conn.close()
       return data
   ```

3. **Update tests**:
   ```python
   # In tests/test_chicken_db.py
   def test_new_table_creation(self):
       chicken_db.initialize_db()
       conn = sqlite3.connect(self.test_db)
       cursor = conn.cursor()
       cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='NewTable'")
       self.assertIsNotNone(cursor.fetchone())
       conn.close()
   ```

---

## Database Migrations

### Adding Columns to Existing Tables

**Pattern used in `initialize_db()`**:
```python
# Check if column exists
cursor.execute("PRAGMA table_info(TableName)")
columns = [info[1] for info in cursor.fetchall()]

if 'NewColumn' not in columns:
    cursor.execute("ALTER TABLE TableName ADD COLUMN NewColumn TEXT")
```

### Migration Best Practices

1. **Always use IF NOT EXISTS** for table creation
2. **Check column existence** before adding
3. **Preserve existing data**
4. **Test migrations** on a copy of production database
5. **Document migrations** in CHANGELOG.md

### Example Migration

```python
def migrate_add_email_to_employees():
    """Migration: Add Email column to Employees table"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(Employees)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'Email' not in columns:
        cursor.execute("ALTER TABLE Employees ADD COLUMN Email TEXT")
        conn.commit()
        print("Migration completed: Added Email to Employees")
    else:
        print("Migration skipped: Email column already exists")
    
    conn.close()
```

---

## Testing Guidelines

### Writing Unit Tests

1. **Test file naming**: `test_[module_name].py`

2. **Test class naming**: `Test[FeatureName]`

3. **Test method naming**: `test_[what_it_tests]`

4. **Test structure**:
   ```python
   class TestNewFeature(unittest.TestCase):
       def setUp(self):
           """Setup test database"""
           self.test_db = 'test_chicken_tracker.db'
           chicken_db.DB_NAME = self.test_db
           chicken_db.initialize_db()
       
       def tearDown(self):
           """Cleanup test database"""
           if os.path.exists(self.test_db):
               os.remove(self.test_db)
       
       def test_feature_works(self):
           """Test that feature works correctly"""
           # Arrange
           # Act
           # Assert
   ```

### Running Tests

```bash
# Run all tests
python tests/run_tests.py

# Run specific test file
python -m unittest tests.test_chicken_db

# Run specific test class
python -m unittest tests.test_chicken_db.TestVendorOperations

# Run specific test method
python -m unittest tests.test_chicken_db.TestVendorOperations.test_rename_vendor

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Test Coverage Goals

- **Minimum**: 70% code coverage
- **Target**: 85% code coverage
- **Critical paths**: 100% coverage (database operations, calculations)

---

## Coding Standards

### Python Style Guide

Follow PEP 8 with these specifics:

1. **Indentation**: 4 spaces
2. **Line length**: 100 characters (flexible for readability)
3. **Imports**: Grouped and sorted
   ```python
   # Standard library
   import os
   import sys
   
   # Third-party
   import streamlit as st
   import pandas as pd
   
   # Local
   import chicken_db
   import utils
   ```

4. **Naming conventions**:
   - Functions: `snake_case`
   - Classes: `PascalCase`
   - Constants: `UPPER_SNAKE_CASE`
   - Private: `_leading_underscore`

### Documentation

1. **Module docstrings**:
   ```python
   """
   Module for managing vendor operations.
   
   This module provides functions for CRUD operations on vendors,
   markup rule management, and ledger tracking.
   """
   ```

2. **Function docstrings**:
   ```python
   def calculate_expected_rate(raw_rates, rule):
       """
       Calculate expected rate based on raw rates and markup rule.
       
       Args:
           raw_rates (tuple): (TandoorRate, BoilerRate, EggRate)
           rule (tuple): (BaseType, Op1, Val1, Op2, Val2)
       
       Returns:
           float: Calculated expected rate rounded to 2 decimals
       
       Example:
           >>> calculate_expected_rate((100, 90, 80), ('TandoorRate', '+', 10, None, None))
           110.0
       """
   ```

3. **Inline comments**: Explain "why", not "what"
   ```python
   # Good
   # Use 28-day delay as per company policy
   payment_date = month_end + timedelta(days=28)
   
   # Bad
   # Add 28 days to month end
   payment_date = month_end + timedelta(days=28)
   ```

### Code Formatting

Use `black` for automatic formatting:
```bash
black *.py pages/*.py tests/*.py
```

### Linting

Use `flake8` for linting:
```bash
flake8 *.py pages/*.py tests/*.py
```

---

## Debugging

### Streamlit Debugging

1. **Print debugging**:
   ```python
   st.write("Debug:", variable)
   st.json(data_dict)
   ```

2. **Exception display**:
   ```python
   try:
       # code
   except Exception as e:
       st.exception(e)  # Shows full traceback
   ```

3. **Session state inspection**:
   ```python
   st.write("Session State:", st.session_state)
   ```

### Database Debugging

1. **Query inspection**:
   ```python
   query = "SELECT * FROM Suppliers WHERE SupplierName = ?"
   st.code(query, language="sql")
   ```

2. **SQLite browser**: Use DB Browser for SQLite
   ```bash
   # Install
   sudo apt install sqlitebrowser  # Linux
   brew install --cask db-browser-for-sqlite  # Mac
   
   # Open database
   sqlitebrowser chicken_tracker.db
   ```

3. **Query results**:
   ```python
   conn = utils.get_db_connection()
   df = pd.read_sql_query("SELECT * FROM Suppliers", conn)
   st.dataframe(df)
   conn.close()
   ```

### Performance Debugging

1. **Timing operations**:
   ```python
   import time
   
   start = time.time()
   # operation
   st.write(f"Took {time.time() - start:.2f} seconds")
   ```

2. **Cache statistics**:
   ```python
   st.write("Cache info:", chicken_db.fetch_suppliers_and_items.cache_info())
   ```

---

## Common Patterns

### Form Submission Pattern

```python
with st.form("my_form"):
    field1 = st.text_input("Field 1")
    field2 = st.number_input("Field 2")
    
    submitted = st.form_submit_button("Submit")
    
    if submitted:
        # Validation
        if not field1:
            st.error("Field 1 is required")
            return
        
        # Database operation
        try:
            conn = utils.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO Table (Col1, Col2) VALUES (?, ?)", (field1, field2))
            conn.commit()
            conn.close()
            st.success("Saved successfully!")
        except Exception as e:
            st.error(f"Error: {e}")
```

### Data Editor Pattern

```python
# Load data
conn = utils.get_db_connection()
df = pd.read_sql_query("SELECT * FROM Table", conn)
conn.close()

# Edit
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    column_config={
        "Status": st.column_config.SelectboxColumn(
            options=["Active", "Inactive"]
        )
    }
)

# Save
if st.button("Save Changes"):
    conn = utils.get_db_connection()
    cursor = conn.cursor()
    
    # Delete all and re-insert (simple approach)
    cursor.execute("DELETE FROM Table")
    
    for _, row in edited_df.iterrows():
        cursor.execute("INSERT INTO Table VALUES (?, ?)", (row['Col1'], row['Col2']))
    
    conn.commit()
    conn.close()
    st.success("Changes saved!")
```

---

## Deployment

### Production Checklist

- [ ] All tests passing
- [ ] Database migrations tested
- [ ] Error handling implemented
- [ ] Input validation added
- [ ] Performance optimized
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version number bumped

### Environment Variables

For production deployment, consider using environment variables:

```python
import os

DB_NAME = os.getenv('DB_PATH', 'chicken_tracker.db')
DEBUG = os.getenv('DEBUG', 'False') == 'True'
```

---

## Troubleshooting

### Common Issues

**Issue**: Streamlit cache not clearing
```python
# Solution
st.cache_data.clear()
# Or restart the app
```

**Issue**: Database locked
```python
# Solution: Ensure connections are closed
conn = utils.get_db_connection()
try:
    # operations
finally:
    conn.close()  # Always close
```

**Issue**: Import errors
```python
# Solution: Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

---

## Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Pandas Documentation](https://pandas.pydata.org/docs/)
- [Python Testing](https://docs.python.org/3/library/unittest.html)

---

## Getting Help

1. Check existing documentation
2. Review similar code in the codebase
3. Check test files for examples
4. Consult API reference
5. Ask the team

---

## Contributing

See main README.md for contribution guidelines.
