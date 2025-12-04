import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import sqlite3
from datetime import datetime

# Placeholder for tkcalendar import
try:
    from tkcalendar import Calendar 
except ImportError:
    pass # Assumed to be available in the main environment

from chicken_db import (
    DB_NAME,
    fetch_items_for_supplier,
    fetch_rate_and_rule,
    calculate_expected_rate
)

# Global cache for expected rates to improve performance during row edits
# Key: (date, supplier_name, item_name) -> Value: expected_rate
RATE_CACHE = {} 

class BillEntryManager:
    """Manages the Daily Bill Entry functionality."""

    def __init__(self, master_app, notebook_frame, suppliers, update_app_data_callback):
        self.master_app = master_app
        self.frame = notebook_frame
        self.suppliers = suppliers
        self.update_app_data_callback = update_app_data_callback
        
        # State variables
        self.expected_rates = {} # Cache for current grid calculation
        self.total_bill_amount_var = tk.StringVar(value="Total Bill: ₹0.00")
        
        self._setup_bill_entry_tab()

    # --- Calendar Widget Helper ---
    def _open_calendar_popup(self, date_var):
        """Opens a Toplevel window with a calendar for date selection."""
        try:
            from tkcalendar import Calendar 
        except ImportError:
            messagebox.showerror("Error", "tkcalendar not found.")
            return

        top = Toplevel(self.frame)
        top.title("Select Date")
        top.grab_set()

        def set_date():
            selected_date = cal.selection_get().strftime("%Y-%m-%d")
            date_var.set(selected_date)
            top.destroy()
            self._load_bill_grid() # Reload grid when date changes
        
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


    # --- UI Setup ---
    def _setup_bill_entry_tab(self):
        # Control Frame (Vendor and Date Selection)
        control_frame = ttk.Frame(self.frame)
        control_frame.pack(fill='x', pady=10, padx=10)

        # Date Selection
        ttk.Label(control_frame, text="Bill Date:").pack(side=tk.LEFT, padx=5)
        self.bill_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(control_frame, textvariable=self.bill_date_var, width=12, state='readonly').pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="📅", command=lambda: self._open_calendar_popup(self.bill_date_var)).pack(side=tk.LEFT, padx=5)

        # Vendor Selection
        ttk.Label(control_frame, text="Select Vendor:").pack(side=tk.LEFT, padx=(30, 5))
        self.bill_vendor_var = tk.StringVar()
        self.bill_vendor_combo = ttk.Combobox(control_frame, textvariable=self.bill_vendor_var, state='readonly', width=20)
        self.bill_vendor_combo.pack(side=tk.LEFT, padx=5)
        self.bill_vendor_combo.bind('<<ComboboxSelected>>', self._load_bill_grid)
        
        # Set initial vendor list
        self.bill_vendor_combo['values'] = self.suppliers
        if self.suppliers:
            self.bill_vendor_var.set(self.suppliers[0])
            # NOTE: We DO NOT call _load_bill_grid here yet.

        # Separator
        ttk.Separator(self.frame, orient='horizontal').pack(fill='x', pady=5)
        
        # Grid Frame
        grid_frame = ttk.Frame(self.frame)
        grid_frame.pack(fill='both', expand=True, padx=10)
        
        # Treeview for Bill Entries (Initialization)
        columns = ('Item', 'Q_Rec', 'Q_Dmg', 'Net_Q', 'E_Rate', 'V_Rate', 'E_Amt', 'V_Amt', 'Var_Amt', 'Status')
        self.bill_tree = ttk.Treeview(grid_frame, columns=columns, show='headings', selectmode='browse')
        
        # Define Headings and Columns
        self.bill_tree.heading('Item', text='Item Name')
        self.bill_tree.heading('Q_Rec', text='Qty Recv.')
        self.bill_tree.heading('Q_Dmg', text='Qty Dmg.')
        self.bill_tree.heading('Net_Q', text='Net Qty')
        self.bill_tree.heading('E_Rate', text='Exp. Rate')
        self.bill_tree.heading('V_Rate', text='Vendor Rate')
        self.bill_tree.heading('E_Amt', text='Exp. Amount')
        self.bill_tree.heading('V_Amt', text='Vendor Amount')
        self.bill_tree.heading('Var_Amt', text='Variance')
        self.bill_tree.heading('Status', text='Status')
        
        # Column width configuration
        for col in columns:
            self.bill_tree.column(col, anchor='center', width=70)
        self.bill_tree.column('Item', width=100, anchor='w')
        self.bill_tree.column('Status', width=80, anchor='center')
        
        self.bill_tree.pack(side=tk.LEFT, fill='both', expand=True)
        
        # Scrollbar
        vsb = ttk.Scrollbar(grid_frame, orient="vertical", command=self.bill_tree.yview)
        vsb.pack(side=tk.RIGHT, fill='y')
        self.bill_tree.configure(yscrollcommand=vsb.set)
        
        # Bind double-click for editing input cells
        self.bill_tree.bind('<Double-1>', self._start_bill_edit)
        
        # Bottom controls (Save and Total)
        bottom_frame = ttk.Frame(self.frame)
        bottom_frame.pack(fill='x', pady=10, padx=10)
        
        ttk.Label(bottom_frame, textvariable=self.total_bill_amount_var, font=('Arial', 12, 'bold'), foreground='blue').pack(side=tk.LEFT)
        ttk.Button(bottom_frame, text="Save Bill Entries", command=self._save_bill).pack(side=tk.RIGHT, padx=5)

        # --- FIX: Initial Load moved here, after self.bill_tree is defined ---
        if self.suppliers:
            self._load_bill_grid()


    # --- Data Handling and Calculation ---
    
    def _fetch_expected_rate(self, date, supplier_name, item_name):
        """Fetches/calculates the expected rate using caching."""
        global RATE_CACHE
        cache_key = (date, supplier_name, item_name)
        
        if cache_key in RATE_CACHE:
            return RATE_CACHE[cache_key]

        paper_rates, rule = fetch_rate_and_rule(date, supplier_name, item_name)
        
        if paper_rates and rule:
            expected_rate = calculate_expected_rate(paper_rates, rule)
            RATE_CACHE[cache_key] = expected_rate
            return expected_rate
        
        # If rates or rule are missing, return 0.0
        RATE_CACHE[cache_key] = 0.0 
        return 0.0

    def _load_bill_grid(self, event=None):
        """Loads items for the selected vendor and calculates their expected rates."""
        vendor = self.bill_vendor_var.get()
        bill_date = self.bill_date_var.get()
        
        if not vendor: return

        # Clear existing data and cache
        self.bill_tree.delete(*self.bill_tree.get_children())
        self.expected_rates = {}
        global RATE_CACHE
        RATE_CACHE = {} 
        self.total_bill_amount_var.set("Total Bill: ₹0.00")

        # 1. Fetch Items
        items = fetch_items_for_supplier(vendor)
        
        if not items:
            messagebox.showwarning("No Markups", f"No markup rules found for vendor '{vendor}'. Cannot enter bill.")
            return

        # 2. Populate Grid and Calculate Initial Expected Rates
        for item in items:
            expected_rate = self._fetch_expected_rate(bill_date, vendor, item)
            self.expected_rates[item] = expected_rate
            
            # Initial row values (Net_Q, Exp_Amt, Ven_Amt, Var_Amt are 0.00)
            values = (item, 0.0, 0.0, 0.0, f"{expected_rate:,.2f}", 0.0, 0.0, 0.0, 0.0, 'N/A')
            self.bill_tree.insert('', tk.END, iid=item, values=values)
            
            if expected_rate == 0.0:
                 self.bill_tree.item(item, tags=('no_rate',))
                 self.bill_tree.set(item, 'Status', 'No Rate Data')
            else:
                 self.bill_tree.item(item, tags=('okay',))
                 self.bill_tree.set(item, 'Status', 'Okay')


        # Configure tags for visual feedback
        self.bill_tree.tag_configure('okay', foreground='black')
        self.bill_tree.tag_configure('no_rate', foreground='gray')
        self.bill_tree.tag_configure('high_var', foreground='red', font=('Arial', 9, 'bold'))
        self.bill_tree.tag_configure('low_var', foreground='orange')

    def _start_bill_edit(self, event):
        """Allows in-place editing of Qty Received, Qty Damaged, and Vendor Rate."""
        if not self.bill_tree.selection(): return
        
        item_id = self.bill_tree.selection()[0] # item_id is the Item Name (string)
        column = self.bill_tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        # Only Qty Received (1), Qty Damaged (2), and Vendor Rate (5) are editable
        editable_cols = [1, 2, 5]
        
        if column_index in editable_cols:
            x, y, width, height = self.bill_tree.bbox(item_id, column)
            current_value = self.bill_tree.item(item_id, 'values')[column_index]
            
            entry = ttk.Entry(self.bill_tree)
            entry.insert(0, str(current_value))
            entry.place(x=x, y=y, width=width, height=height, anchor='nw')
            entry.focus()
            
            def save_edit(event):
                if not entry.winfo_exists(): return
                
                new_value = entry.get().strip()
                try:
                    # Input columns must be numeric (floats)
                    numeric_value = float(new_value)
                    if numeric_value < 0:
                        raise ValueError("Quantity and Rate cannot be negative.")
                except ValueError as e:
                    messagebox.showerror("Input Error", f"Value must be a positive number. {e}")
                    entry.destroy()
                    return

                current_values = list(self.bill_tree.item(item_id, 'values'))
                current_values[column_index] = numeric_value
                
                # Update the treeview with the new value
                self.bill_tree.item(item_id, values=current_values)
                entry.destroy()
                
                # Recalculate the entire row
                self._recalculate_row(item_id)
            
            entry.bind('<Return>', save_edit)
            entry.bind('<FocusOut>', save_edit) 

    def _recalculate_row(self, item_name):
        """Performs all calculations for a single row based on user input."""
        current_values = list(self.bill_tree.item(item_name, 'values'))
        
        # Columns indices: 0:Item, 1:Q_Rec, 2:Q_Dmg, 3:Net_Q, 4:E_Rate, 5:V_Rate, 6:E_Amt, 7:V_Amt, 8:Var_Amt, 9:Status
        
        # 1. Parse inputs
        try:
            q_recv = float(current_values[1])
            q_dmg = float(current_values[2])
            v_rate = float(current_values[5])
            e_rate_display = current_values[4].replace(',', '') # Remove formatting for calculation
            e_rate = float(e_rate_display)
        except ValueError:
            # Should not happen if input validation is correct, but handles initial 'N/A' or bad data
            self.bill_tree.set(item_name, 'Status', 'Input Error')
            return

        # 2. Calculations
        net_qty = max(0.0, q_recv - q_dmg)
        exp_amount = round(net_qty * e_rate, 2)
        vendor_amount = round(net_qty * v_rate, 2)
        variance_amount = round(vendor_amount - exp_amount, 2)
        
        # 3. Status Determination
        status = 'N/A'
        tags = ('okay',)
        
        # Only calculate status if there is a positive net quantity
        if net_qty > 0.0 and e_rate > 0.0:
            variance_pct = (variance_amount / exp_amount) * 100 if exp_amount else 0.0
            
            if variance_pct > 5.0:
                status = 'HIGH (+)'
                tags = ('high_var',)
            elif variance_pct < -5.0:
                status = 'LOW (-)'
                tags = ('low_var',)
            elif variance_amount != 0.0:
                status = 'Variance'
            else:
                status = 'Okay'
        elif e_rate == 0.0:
            status = 'No Rate Data'
            tags = ('no_rate',)
            
        # 4. Update row values and tags
        current_values[3] = f"{net_qty:,.2f}"
        current_values[6] = f"{exp_amount:,.2f}"
        current_values[7] = f"{vendor_amount:,.2f}"
        current_values[8] = f"{variance_amount:,.2f}"
        current_values[9] = status
        
        self.bill_tree.item(item_name, values=current_values, tags=tags)
        
        # 5. Update total bill amount
        self._update_total_bill()

    def _update_total_bill(self):
        """Sums up the Vendor Amount (column 7) for all rows."""
        total = 0.0
        for item_id in self.bill_tree.get_children():
            values = self.bill_tree.item(item_id, 'values')
            if len(values) > 7:
                try:
                    # Column 7 (Vendor Amount) is stored as a formatted string, remove comma for calculation
                    v_amt_str = str(values[7]).replace(',', '') 
                    total += float(v_amt_str)
                except ValueError:
                    continue
        
        self.total_bill_amount_var.set(f"Total Bill: ₹{total:,.2f}")


    def _save_bill(self):
        """Saves all entries with Net Qty > 0 to BillEntries and updates the VendorLedger."""
        vendor = self.bill_vendor_var.get()
        bill_date = self.bill_date_var.get()
        total_bill_amount = 0.0
        entries_to_save = []
        
        if not vendor:
            messagebox.showwarning("Warning", "Please select a vendor.")
            return

        if not messagebox.askyesno("Confirm Save", f"Confirm saving bill for {vendor} on {bill_date}?"):
            return

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        try:
            # Check for existing bill entries for this vendor/date combination
            cursor.execute("SELECT COUNT(*) FROM BillEntries WHERE SupplierName = ? AND Date = ?", (vendor, bill_date))
            if cursor.fetchone()[0] > 0:
                 if not messagebox.askyesno("Overwrite Warning", 
                                            f"Bill entries already exist for {vendor} on {bill_date}. Do you want to **overwrite** them?"):
                     conn.close()
                     return
                 
                 # Delete existing entries first
                 cursor.execute("DELETE FROM BillEntries WHERE SupplierName = ? AND Date = ?", (vendor, bill_date))
                 # Also remove the previous bill entry from the ledger to prevent double-billing
                 cursor.execute("DELETE FROM VendorLedger WHERE SupplierName = ? AND Date = ? AND TransactionType = 'Bill'", (vendor, bill_date))


            # 1. Prepare and Validate Entries
            for item_id in self.bill_tree.get_children():
                values = self.bill_tree.item(item_id, 'values')
                
                # Values: 0:Item, 1:Q_Rec, 2:Q_Dmg, 3:Net_Q, 4:E_Rate, 5:V_Rate, 6:E_Amt, 7:V_Amt, 8:Var_Amt, 9:Status
                
                # Parse all calculated/input fields
                try:
                    item_name = str(values[0])
                    net_qty = float(str(values[3]).replace(',', ''))
                    e_rate = float(str(values[4]).replace(',', ''))
                    v_rate = float(values[5])
                    variance = float(str(values[8]).replace(',', ''))
                    status = str(values[9])
                except (ValueError, IndexError):
                    messagebox.showerror("Save Error", f"Data error in row for {values[0]}. Please check inputs.")
                    conn.rollback()
                    return

                if net_qty > 0.0:
                    entries_to_save.append((
                        bill_date, vendor, item_name, net_qty, v_rate, e_rate, variance, status
                    ))
                    total_bill_amount += round(net_qty * v_rate, 2) # Summing up the Vendor Amount

            if not entries_to_save:
                messagebox.showwarning("Warning", "No entries with positive net quantity to save.")
                conn.close()
                return

            # 2. Insert into BillEntries
            bill_entry_query = """
                INSERT INTO BillEntries (Date, SupplierName, ItemName, Qty, VendorRate, ExpectedRate, Variance, Status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
            cursor.executemany(bill_entry_query, entries_to_save)

            # 3. Insert/Update VendorLedger (Bill is a positive amount)
            ledger_entry_query = """
                INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount, Details)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(ledger_entry_query, (
                bill_date, vendor, 'Bill', total_bill_amount, f"Total Bill Amount for {bill_date}"
            ))

            conn.commit()
            messagebox.showinfo("Success", f"Bill entries for {vendor} on {bill_date} saved successfully.\nTotal Bill: ₹{total_bill_amount:,.2f}")
            self._load_bill_grid() # Reload the grid/reset entries
            self.update_app_data_callback() # Notify main app to update ledger/due balance views

        except Exception as e:
            messagebox.showerror("Database Error", f"An error occurred while saving the bill: {e}")
            conn.rollback()
        finally:
            conn.close()