# API Reference - chicken_db.py

This document provides detailed API documentation for the `chicken_db.py` module, which serves as the core database layer for the Zohra Restaurant Management System.

## Database Configuration

```python
DB_NAME = 'chicken_tracker.db'
```

The default database file name. Can be modified for testing or multi-instance deployments.

---

## Database Initialization

### `initialize_db()`

Initializes the database schema by creating all required tables.

**Returns**: None

**Side Effects**: Creates tables in the SQLite database if they don't exist

**Tables Created**:
- Suppliers
- Markups
- RawData
- BillEntries
- VendorLedger

**Example**:
```python
import chicken_db
chicken_db.initialize_db()
```

**Notes**:
- Idempotent: Safe to call multiple times
- Uses `CREATE TABLE IF NOT EXISTS`
- Handles schema migrations (e.g., adding LastUpdated column)

---

## Vendor/Supplier Operations

### `fetch_suppliers_and_items()`

Fetches all suppliers from the database.

**Returns**: `tuple(list, dict)`
- `list`: List of supplier names (sorted alphabetically)
- `dict`: Empty dictionary (legacy compatibility)

**Caching**: Uses `@st.cache_data` decorator

**Example**:
```python
suppliers, _ = chicken_db.fetch_suppliers_and_items()
# suppliers = ['Vendor A', 'Vendor B', 'Vendor C']
```

---

### `fetch_vendor_type(vendor_name: str)`

Retrieves the vendor type for a specific vendor.

**Parameters**:
- `vendor_name` (str): Name of the vendor

**Returns**: `str | None`
- Vendor type (e.g., 'Chicken', 'Other')
- `None` if vendor not found

**Caching**: Uses `@st.cache_data` decorator

**Example**:
```python
vendor_type = chicken_db.fetch_vendor_type('ABC Poultry')
# vendor_type = 'Chicken'
```

---

### `rename_vendor(old_name: str, new_name: str)`

Renames a vendor and updates all related tables transactionally.

**Parameters**:
- `old_name` (str): Current vendor name
- `new_name` (str): New vendor name

**Returns**: `bool`
- `True` if successful
- `False` if error occurred

**Tables Updated**:
1. Suppliers
2. Markups
3. BillEntries
4. VendorLedger

**Transaction**: All updates are atomic (rolled back on error)

**Example**:
```python
success = chicken_db.rename_vendor('Old Vendor', 'New Vendor')
if success:
    print("Vendor renamed successfully")
```

---

### `delete_vendor_and_cleanup(supplier_id: int, supplier_name: str)`

Deletes a vendor and cascades the deletion to all related tables.

**Parameters**:
- `supplier_id` (int): Supplier's database ID
- `supplier_name` (str): Supplier's name

**Returns**: `bool`
- `True` if successful
- `False` if error occurred

**Deletion Order** (to maintain referential integrity):
1. VendorLedger entries
2. BillEntries
3. Markups
4. Supplier record

**Transaction**: All deletions are atomic

**Example**:
```python
success = chicken_db.delete_vendor_and_cleanup(5, 'Vendor Name')
```

**Warning**: This operation is irreversible. All historical data for the vendor will be deleted.

---

### `insert_default_markups(vendor_name: str, default_rules: list)`

Inserts default markup rules for a vendor.

**Parameters**:
- `vendor_name` (str): Vendor name
- `default_rules` (list): List of tuples with markup rule data

**Rule Tuple Format**:
```python
(ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2)
```

**Returns**: `bool`
- `True` if successful
- `False` if error occurred

**Example**:
```python
default_rules = [
    ('Boneless', 'TandoorRate', '+', 95.0, None, None),
    ('Full Leg', 'TandoorRate', '+', 18.0, '*', 1.05),
]
success = chicken_db.insert_default_markups('ABC Poultry', default_rules)
```

---

### `fetch_items_for_supplier(supplier_name: str)`

Fetches all items associated with a supplier.

**Parameters**:
- `supplier_name` (str): Supplier name

**Returns**: `list[str]`
- List of item names (sorted alphabetically)

**Example**:
```python
items = chicken_db.fetch_items_for_supplier('ABC Poultry')
# items = ['Boneless', 'Full Chicken', 'Wings']
```

---

## Rate Calculation Operations

### `fetch_rate_and_rule(date: str, supplier_name: str, item_name: str)`

Fetches raw market rates and markup rule for a specific date, supplier, and item.

**Parameters**:
- `date` (str): Date in 'YYYY-MM-DD' format
- `supplier_name` (str): Supplier name
- `item_name` (str): Item name

**Returns**: `tuple(tuple, tuple)`
- First tuple: `(TandoorRate, BoilerRate, EggRate)` or `None`
- Second tuple: `(BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2)` or `None`

**Example**:
```python
raw_rates, rule = chicken_db.fetch_rate_and_rule('2023-01-15', 'ABC Poultry', 'Boneless')
# raw_rates = (100.0, 90.0, 80.0)
# rule = ('TandoorRate', '+', 95.0, None, None)
```

---

### `calculate_expected_rate(raw_rates: tuple, rule: tuple)`

Calculates the expected rate based on raw rates and markup rule.

**Parameters**:
- `raw_rates` (tuple): `(TandoorRate, BoilerRate, EggRate)`
- `rule` (tuple): `(BaseRateType, Op1, Val1, Op2, Val2)`

**Returns**: `float`
- Calculated expected rate (rounded to 2 decimals)
- Returns `0.0` if inputs are invalid

**Calculation Steps**:
1. Select base rate based on `BaseRateType`
2. Apply first operation: `rate = rate Op1 Val1`
3. Apply second operation if exists: `rate = rate Op2 Val2`
4. Round to 2 decimal places
5. Ensure non-negative result

**Supported Operators**:
- `+`: Addition
- `-`: Subtraction
- `*`: Multiplication
- `/`: Division (with zero-division protection)

**Example**:
```python
raw_rates = (100, 90, 80)
rule = ('TandoorRate', '+', 10, '*', 1.1)
expected = chicken_db.calculate_expected_rate(raw_rates, rule)
# Calculation: (100 + 10) * 1.1 = 121.0
```

**Edge Cases**:
- Division by zero: Returns current value unchanged
- Negative result: Returns 0.0
- None values: Returns 0.0

---

## Data Retrieval Operations

### `fetch_rate_history(limit: int = 30)`

Fetches historical rate data for charting.

**Parameters**:
- `limit` (int, optional): Number of days to fetch (default: 30)

**Returns**: `list[tuple]`
- List of tuples: `(Date, TandoorRate, BoilerRate, EggRate)`
- Ordered from oldest to newest

**Example**:
```python
history = chicken_db.fetch_rate_history(limit=7)
# history = [
#     ('2023-01-08', 98.0, 88.0, 78.0),
#     ('2023-01-09', 99.0, 89.0, 79.0),
#     ...
# ]
```

**Usage**: Typically used for line charts showing rate trends

---

### `fetch_vendor_dues()`

Calculates total outstanding dues for each vendor.

**Returns**: `dict`
- Key: Vendor name (str)
- Value: Total due amount (float)

**Calculation**:
```
Total Due = SUM(Bill Amounts) + SUM(Ledger Amounts)
```

**Note**: 
- Bill amounts are always positive
- Ledger amounts can be positive (bills) or negative (payments)

**Example**:
```python
dues = chicken_db.fetch_vendor_dues()
# dues = {
#     'ABC Poultry': 15000.50,
#     'XYZ Suppliers': -500.00,  # Negative = overpaid
#     'Fresh Chicken': 8200.00
# }
```

---

## Database Schema Reference

### Suppliers Table

```sql
CREATE TABLE Suppliers (
    SupplierID INTEGER PRIMARY KEY,
    SupplierName TEXT UNIQUE NOT NULL,
    PhoneNumber TEXT,
    PreferredPaymentType TEXT,
    PaymentFrequency TEXT,
    VendorType TEXT NOT NULL,
    MarkupRequired INTEGER DEFAULT 1,
    LastUpdated TEXT
)
```

### Markups Table

```sql
CREATE TABLE Markups (
    ItemID INTEGER PRIMARY KEY,
    SupplierName TEXT NOT NULL,
    ItemName TEXT NOT NULL,
    BaseRateType TEXT NOT NULL,
    MarkupOperator1 TEXT,
    MarkupValue1 REAL,
    MarkupOperator2 TEXT,
    MarkupValue2 REAL,
    UNIQUE (SupplierName, ItemName),
    FOREIGN KEY (SupplierName) REFERENCES Suppliers(SupplierName)
)
```

### RawData Table

```sql
CREATE TABLE RawData (
    Date TEXT PRIMARY KEY,
    TandoorRate REAL NOT NULL,
    BoilerRate REAL NOT NULL,
    EggRate REAL NOT NULL
)
```

### BillEntries Table

```sql
CREATE TABLE BillEntries (
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
```

### VendorLedger Table

```sql
CREATE TABLE VendorLedger (
    ID INTEGER PRIMARY KEY,
    Date TEXT NOT NULL,
    SupplierName TEXT NOT NULL,
    TransactionType TEXT NOT NULL,
    Amount REAL NOT NULL,
    Details TEXT,
    FOREIGN KEY (SupplierName) REFERENCES Suppliers(SupplierName)
)
```

---

## Error Handling

All functions that modify data return boolean values:
- `True`: Operation successful
- `False`: Operation failed (error logged to console)

Functions that retrieve data:
- Return `None` or empty collections if no data found
- Return actual data if found

**Best Practices**:
```python
# For modification operations
success = chicken_db.rename_vendor('Old', 'New')
if not success:
    st.error("Failed to rename vendor")

# For retrieval operations
vendor_type = chicken_db.fetch_vendor_type('ABC')
if vendor_type is None:
    st.warning("Vendor not found")
```

---

## Performance Considerations

### Caching

Functions decorated with `@st.cache_data`:
- `fetch_suppliers_and_items()`
- `fetch_vendor_type()`

**Cache Invalidation**:
```python
# Clear specific cache
chicken_db.fetch_suppliers_and_items.clear()

# Clear all Streamlit caches
st.cache_data.clear()
```

### Database Connections

- Always close connections after use
- Use context managers when possible:
  ```python
  conn = sqlite3.connect(chicken_db.DB_NAME)
  try:
      # Database operations
      pass
  finally:
      conn.close()
  ```

---

## Testing

See `tests/test_chicken_db.py` for comprehensive unit tests covering all functions.

Run tests:
```bash
python -m unittest tests.test_chicken_db
```
