# Implementation Plan - Data Consistency & Testing

## Goal Description
Fix the issue where updating a supplier's name does not update related records in other tables. Add a `LastUpdated` field to track changes. Implement comprehensive unit tests for the vendor lifecycle.

## User Review Required
> [!IMPORTANT]
> Modified database schema to add `LastUpdated` column and implemented transactional rename function.

## Proposed Changes

### Database Layer (`chicken_db.py`)
- [MODIFY] `initialize_db`: Add `LastUpdated` column to `Suppliers` table
- [NEW] `rename_vendor(old_name, new_name)`: Transactional function to:
    1. Update `Suppliers`
    2. Update `Markups`
    3. Update `BillEntries`
    4. Update `VendorLedger`
- [MODIFY] `update_supplier`: Update `LastUpdated` timestamp

### UI Layer (`streamlit_app.py`)
- [MODIFY] Update "Save Changes" logic in Vendor Management to use `rename_vendor`
- [MODIFY] Display `LastUpdated` in supplier table

### Testing
- [NEW] `tests/test_vendor_flow.py`: Unit tests
    - Test Case 1: Create Vendor
    - Test Case 2: Add Markups
    - Test Case 3: Rename Vendor → Verify cascading updates
    - Test Case 4: Delete Vendor → Verify cleanup

## Verification Plan
- Run `python3 -m unittest tests/test_vendor_flow.py`
- Manually rename a vendor and verify bill history is preserved
