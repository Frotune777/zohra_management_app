# Version History

## v1.1.0 (Current)
- **New Feature**: Added "Dashboard & Reports" tab.
  - Rate Trend Chart (Last 30 days).
  - Vendor Due Balance Chart.
- **UI Improvements**:
  - Applied `Segoe UI` font theme.
  - Improved styling for Treeviews and Frames.
- **Refactoring**:
  - Added `fetch_rate_history` and `fetch_vendor_dues` to `chicken_db.py`.
  - Fixed recursion bug in data synchronization between tabs.
  - Fixed UI bug where dropdowns in Markup Management were not saving/closing correctly.
- **UX Improvements**:
  - Added scrollbars to Markup Management table.
  - Removed blocking "Success" popups for smoother data entry.
  - Improved alignment and styling of input fields in tables.
- **Migration**:
  - Migrated application to **Streamlit** for a modern, web-based UI.
  - Added virtual environment support.
  - Implemented modern CSS styling (Inter font, custom colors, card-like metrics).
  - Refactored to **multi-page app structure** with separate pages for each module.
  - Added comprehensive documentation in `docs/` folder.


## v1.0.0
- Initial Release.
- Features:
  - Daily Rate Entry.
  - Daily Bill Entry.
  - Vendor Management (CRUD).
  - SQLite Database Integration.
