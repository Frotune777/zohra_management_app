import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
from datetime import datetime
import sqlite3
import pandas as pd
import numpy as np
import tkinter as tk



# Import all modules
import chicken_db
from vendor_management import VendorManager
from bill_entry import BillEntryManager # NEW IMPORT

# --- Main Application Class ---
class ChickenTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Chicken Rate & Bill Tracker")
        self.geometry("1000x750")
        
        # Initialize Database and Data
        chicken_db.initialize_db()
        self.suppliers, self.markup_map = chicken_db.fetch_suppliers_and_items()
        self.markup_rules_cache = {} # Cache for quick markup lookups
        
        # Styling
        self._setup_style()
        
        # Main UI Setup
        self._setup_main_ui()

    def _setup_style(self):
        """Configure application wide theme and styles."""
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Custom button style for action buttons
        style.configure('T.TButton', font=('Arial', 10, 'bold'), padding=6)
        style.map('T.TButton', background=[('active', 'lightblue')])
        
        # Treeview styling
        style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
        style.configure("Treeview", font=('Arial', 9))

    def _update_app_data(self, new_suppliers=None):
        """
        Refreshes supplier and item data across the application. 
        Called after CRUD operations in VendorManager.
        """
        self.suppliers, self.markup_map = chicken_db.fetch_suppliers_and_items()
        self.markup_rules_cache = {} # Clear cache on data update
        
        # Notify other managers to update their comboboxes/lists
        # This assumes all managers have a 'suppliers' list or similar to refresh
        if hasattr(self, 'vendor_manager') and not getattr(self, "_in_update", False):
            self._in_update = True
            self.vendor_manager.load_vendor_list()
            self._in_update = False
            # Re-runs fetch_suppliers_and_items internally
            
        # Update Bill Entry Manager's combobox
        if hasattr(self, 'bill_entry_manager'):
            self.bill_entry_manager.suppliers = self.suppliers
            self.bill_entry_manager.bill_vendor_combo['values'] = self.suppliers
            
    def _setup_main_ui(self):
        # Create a main notebook (tabs)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(pady=10, padx=10, expand=True, fill="both")

        # --- Tab 1: Rate Data Entry ---
        self.rate_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.rate_frame, text="Daily Rate Data Entry")
        self._setup_rate_entry_tab(self.rate_frame)

        # --- Tab 2: Daily Bill Entry (NEW) ---
        self.bill_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.bill_frame, text="Daily Bill Entry")
        self.bill_entry_manager = BillEntryManager(self, self.bill_frame, self.suppliers, self._update_app_data)

        # --- Tab 3: Vendor Management ---
        self.vendor_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.vendor_frame, text="Vendor Management")
        self.vendor_manager = VendorManager(self, self.vendor_frame, self.suppliers, self._update_app_data)
        
        # --- Tab 4: Dashboard/Reports ---
        self.dashboard_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.dashboard_frame, text="Dashboard & Reports")
        # Placeholder for future dashboard logic

        # Bind event to load/refresh data when a tab is switched to
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)
        
    def _on_tab_change(self, event):
        """Handle actions when a tab is selected."""
        selected_tab = self.notebook.index(self.notebook.select())
        
        # When Bill Entry tab is selected, refresh its vendor list and load grid if necessary
        if selected_tab == 1:
             if self.suppliers and not self.bill_entry_manager.bill_vendor_var.get():
                 self.bill_entry_manager.bill_vendor_var.set(self.suppliers[0])
             self.bill_entry_manager._load_bill_grid()
             
        # When Vendor Management tab is selected, ensure list is refreshed
        elif selected_tab == 2:
             self.vendor_manager.load_vendor_list()
             
        # Placeholder for Dashboard refresh if needed later
        elif selected_tab == 3:
             pass # self._load_dashboard() 

    # --- Rate Entry Tab Logic ---
    def _setup_rate_entry_tab(self, frame):
        # Date Selection (Calendar integration needed)
        date_frame = ttk.Frame(frame)
        date_frame.pack(fill='x', pady=5)
        
        ttk.Label(date_frame, text="Select Date:").pack(side=tk.LEFT, padx=5)
        self.rate_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.rate_date_entry = ttk.Entry(date_frame, textvariable=self.rate_date_var, width=12, state='readonly')
        self.rate_date_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(date_frame, text="📅", command=lambda: self._open_calendar_popup(self.rate_date_var)).pack(side=tk.LEFT, padx=5)

        # Rate Input Fields
        input_frame = ttk.LabelFrame(frame, text="Daily Paper Rates", padding="10")
        input_frame.pack(fill='x', pady=10)

        self.tandoor_var = tk.DoubleVar()
        self.boiler_var = tk.DoubleVar()
        self.egg_var = tk.DoubleVar()

        fields = [
            ("Tandoor Rate:", self.tandoor_var),
            ("Boiler Rate:", self.boiler_var),
            ("Egg Rate:", self.egg_var)
        ]

        for i, (label_text, var) in enumerate(fields):
            ttk.Label(input_frame, text=label_text).grid(row=0, column=i * 2, padx=10, pady=5, sticky="w")
            ttk.Entry(input_frame, textvariable=var, width=15).grid(row=0, column=i * 2 + 1, padx=10, pady=5, sticky="w")
        
        # Save Button
        ttk.Button(frame, text="Save Daily Rates", command=self._save_daily_rates, style='T.TButton').pack(pady=10)
        
        # Load rates for the current date on initialization
        self._load_daily_rates()
        
        # Bind rate date change to loading new rates
        self.rate_date_entry.bind('<Button-1>', lambda e: self._open_calendar_popup(self.rate_date_var, callback=self._load_daily_rates))


    def _open_calendar_popup(self, date_var, callback=None):
        """Opens a Toplevel window with a calendar for date selection."""
        try:
            from tkcalendar import Calendar 
        except ImportError:
            messagebox.showerror("Error", "tkcalendar not found.")
            return

        top = Toplevel(self)
        top.title("Select Date")
        top.grab_set()

        def set_date():
            selected_date = cal.selection_get().strftime("%Y-%m-%d")
            date_var.set(selected_date)
            top.destroy()
            if callback:
                callback()
        
        try:
            initial_date = datetime.strptime(date_var.get(), "%Y-%m-%d").date()
        except ValueError:
            initial_date = datetime.now().date()

        cal = Calendar(top, selectmode='day', 
                       year=initial_date.year, month=initial_date.month, day=initial_date.day,
                       date_pattern='yyyy-mm-dd')
        cal.pack(padx=10, pady=10)

        ttk.Button(top, text="Set Date", command=set_date).pack(pady=5)
        top.wait_window(top)
        
    def _load_daily_rates(self):
        """Loads rates from the DB for the selected date."""
        date = self.rate_date_var.get()
        conn = sqlite3.connect(chicken_db.DB_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT TandoorRate, BoilerRate, EggRate FROM RawData WHERE Date = ?", (date,))
            data = cursor.fetchone()
            
            if data:
                self.tandoor_var.set(data[0])
                self.boiler_var.set(data[1])
                self.egg_var.set(data[2])
            else:
                self.tandoor_var.set(0.0)
                self.boiler_var.set(0.0)
                self.egg_var.set(0.0)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load rates: {e}")
        finally:
            conn.close()


    def _save_daily_rates(self):
        """Saves or updates the daily rates in the RawData table."""
        date = self.rate_date_var.get()
        tandoor = self.tandoor_var.get()
        boiler = self.boiler_var.get()
        egg = self.egg_var.get()
        
        if tandoor <= 0 or boiler <= 0 or egg <= 0:
            if not messagebox.askyesno("Confirm Zero Entry", "Rates are zero or negative. Do you still want to save?"):
                return

        conn = sqlite3.connect(chicken_db.DB_NAME)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO RawData (Date, TandoorRate, BoilerRate, EggRate) VALUES (?, ?, ?, ?)
                ON CONFLICT(Date) DO UPDATE SET TandoorRate=excluded.TandoorRate, BoilerRate=excluded.BoilerRate, EggRate=excluded.EggRate
            """, (date, tandoor, boiler, egg))
            conn.commit()
            messagebox.showinfo("Success", f"Daily rates for {date} saved/updated successfully.")
            
            # Clear Rate Cache (Global scope for all calculations)
            global RATE_CACHE
            RATE_CACHE = {} 
            
            # Notify Bill Entry Manager to reload if it's visible and date matches
            if hasattr(self, 'bill_entry_manager') and self.bill_entry_manager.bill_date_var.get() == date:
                 self.bill_entry_manager._load_bill_grid()
                 
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save daily rates: {e}")
        finally:
            conn.close()

if __name__ == '__main__':
    app = ChickenTrackerApp()
    app.mainloop()