# Implementation Plan - Dashboard & Reports

## Goal Description
Add a Dashboard & Reports tab to visualize rate trends and vendor dues using matplotlib charts.

## Proposed Changes

### UI Layer (`chicken_app.py`)
- [MODIFY] Add "Dashboard & Reports" tab
- [NEW] Implement `_setup_dashboard_tab` method
- [NEW] Implement `_refresh_dashboard` method
- [MODIFY] `_on_tab_change` to refresh dashboard when selected

### Database Layer (`chicken_db.py`)
- [NEW] `fetch_rate_history(limit=30)`: Retrieve daily rates for charting
- [NEW] `fetch_vendor_dues()`: Calculate total amounts due for each vendor

## Verification Plan
- Verify charts display correctly
- Check data accuracy
