import tkinter as tk
from tkinter import ttk, messagebox, Toplevel
import sqlite3
from datetime import datetime
# Import new utility functions from chicken_db
from chicken_db import (
    DB_NAME, 
    fetch_suppliers_and_items, 
    calculate_expected_rate, 
    delete_vendor_and_cleanup,
    fetch_vendor_type, # New Import
    insert_default_markups # New Import
)

# Placeholder for tkcalendar import (assumed to be available in the environment)
try:
    from tkcalendar import Calendar 
except ImportError:
    pass # Handled by chicken_app.py

# --- Default Rules Definition ---
# These rules will be automatically inserted for any new 'Chicken' vendor.
DEFAULT_CHICKEN_MARKUP_RULES = [
    # (ItemName, BaseRateType, Op1, Val1, Op2, Val2)
    ('Tandoori', 'TandoorRate', '+', 20.0, None, None),
    ('Boiler', 'BoilerRate', '+', 25.0, None, None),
    ('Egg', 'EggRate', '/', 10.0, '+', 5.0), # Example: (EggRate/10) + 5
    ('Spl Leg', 'TandoorRate', '+', 25.0, None, None),
    ('Boneless', 'TandoorRate', '+', 95.0, None, None),
    ('Full Leg', 'TandoorRate', '+', 18.0, None, None),
    ('Wings', 'TandoorRate', '+', 15.0, None, None),
]
# -------------------------------

class VendorManager:
    def __init__(self, master_app, notebook_frame, suppliers, update_app_data_callback):
        self.master_app = master_app
        self.frame = notebook_frame
        self.suppliers = suppliers
        self.update_app_data_callback = update_app_data_callback # Callback to refresh lists in chicken_app

        # Setup Tab Contents
        self._setup_vendor_management_tab()
        
    # --- Calendar Widget Helper ---
    def _open_calendar_popup(self, date_var):
        """Opens a Toplevel window with a calendar for date selection."""
        try:
            from tkcalendar import Calendar 
        except ImportError:
            messagebox.showerror("Error", "tkcalendar not found. Please install: pip install tkcalendar")
            return

        top = Toplevel(self.frame)
        top.title("Select Date")

        def set_date():
            selected_date = cal.selection_get().strftime("%Y-%m-%d")
            date_var.set(selected_date)
            top.destroy()
        
        try:
            initial_date = datetime.strptime(date_var.get(), "%Y-%m-%d").date()
        except ValueError:
            initial_date = datetime.now().date()

        cal = Calendar(top, selectmode='day', 
                       year=initial_date.year, month=initial_date.month, day=initial_date.day,
                       date_pattern='yyyy-mm-dd')
        cal.pack(padx=10, pady=10)

        ttk.Button(top, text="Set Date", command=set_date).pack(pady=5)

    # --- Vendor Management Tab Setup ---
    def _setup_vendor_management_tab(self):
        # Create a sub-notebook for organization
        vendor_notebook = ttk.Notebook(self.frame)
        vendor_notebook.pack(padx=10, pady=10, expand=True, fill="both")

        # 1. Vendor List & Details Frame (Combined Creation/Edit)
        vendor_details_frame = ttk.Frame(vendor_notebook, padding="10")
        vendor_notebook.add(vendor_details_frame, text="Vendor List & Details")
        self._setup_vendor_list_frame(vendor_details_frame)

        # 2. Markup Management Frame
        markup_frame = ttk.Frame(vendor_notebook, padding="10")
        vendor_notebook.add(markup_frame, text="Markup Rules Management")
        self._setup_markup_management_frame(markup_frame)
        
        # 3. Vendor Ledger Frame
        ledger_frame = ttk.Frame(vendor_notebook, padding="10")
        vendor_notebook.add(ledger_frame, text="Payments & Dues (Ledger)")
        self._setup_vendor_ledger_frame(ledger_frame)

    # --- Vendor List & Details (Creation/Edit) ---
    def _setup_vendor_list_frame(self, frame):
        # Left side: Vendor List
        list_frame = ttk.LabelFrame(frame, text="Existing Suppliers", padding="10")
        list_frame.pack(side=tk.LEFT, fill='y', padx=10, expand=True)
        
        # Updated Treeview setup with more columns
        self.vendor_tree = ttk.Treeview(list_frame, 
            columns=('Name', 'Type', 'Phone', 'PaymentType', 'Frequency', 'MarkupReq'), 
            show='headings', selectmode='browse')
            
        self.vendor_tree.heading('Name', text='Supplier Name')
        self.vendor_tree.heading('Type', text='Type')
        self.vendor_tree.heading('Phone', text='Phone')
        self.vendor_tree.heading('PaymentType', text='Pref. Payment')
        self.vendor_tree.heading('Frequency', text='Frequency')
        self.vendor_tree.heading('MarkupReq', text='Markup Req?')

        self.vendor_tree.column('Name', width=120, anchor='w')
        self.vendor_tree.column('Type', width=70, anchor='center')
        self.vendor_tree.column('Phone', width=100, anchor='center')
        self.vendor_tree.column('PaymentType', width=100, anchor='center')
        self.vendor_tree.column('Frequency', width=80, anchor='center')
        self.vendor_tree.column('MarkupReq', width=80, anchor='center')
        
        self.vendor_tree.pack(fill='both', expand=True)
        self.vendor_tree.bind('<<TreeviewSelect>>', self._update_due_display_and_load_edit)
        
        self.due_label_var = tk.StringVar(value="Select a vendor to view balance.")
        ttk.Label(list_frame, textvariable=self.due_label_var, foreground="blue", font=('Arial', 10, 'bold')).pack(pady=10)
        
        # Add Delete Vendor Button
        ttk.Button(list_frame, text="Remove Selected Vendor", command=self._delete_selected_vendor, style='T.TButton').pack(pady=10)
        
        # Right side: Add/Edit Vendor Details Form
        self.detail_frame = ttk.LabelFrame(frame, text="Add New Vendor", padding="10")
        self.detail_frame.pack(side=tk.LEFT, fill='y', padx=10)
        
        self._setup_vendor_detail_form(self.detail_frame)
        
        self.load_vendor_list() # Initial load

    def _setup_vendor_detail_form(self, frame):
        """Sets up the form fields for adding/editing a vendor."""
        # Variables for the form
        self.current_supplier_id = None
        self.detail_name_var = tk.StringVar()
        self.detail_phone_var = tk.StringVar()
        self.detail_payment_type_var = tk.StringVar(value='Cash')
        self.detail_payment_freq_var = tk.StringVar(value='Daily')
        self.detail_vendor_type_var = tk.StringVar(value="Chicken")
        self.detail_markup_req_var = tk.IntVar(value=1) # Default to 1 (True)
        self.detail_action_var = tk.StringVar(value="Add New Supplier")

        fields = [
            ("Name:", self.detail_name_var, "entry"),
            ("Phone Number:", self.detail_phone_var, "entry"),
            ("Vendor Type:", self.detail_vendor_type_var, "combo", ['Chicken', 'Vegetable', 'Other']),
            ("Pref. Payment:", self.detail_payment_type_var, "combo", ['Bank Transfer', 'Cash', 'Cheque', 'Credit']),
            ("Frequency:", self.detail_payment_freq_var, "combo", ['Daily', 'Weekly', 'Monthly', 'Upon Bill'])
        ]
        
        for i, (label_text, var, widget_type, *options) in enumerate(fields):
            ttk.Label(frame, text=label_text).grid(row=i, column=0, padx=5, pady=5, sticky="w")
            if widget_type == "entry":
                ttk.Entry(frame, textvariable=var, width=30).grid(row=i, column=1, padx=5, pady=5, sticky="w")
            elif widget_type == "combo":
                ttk.Combobox(frame, textvariable=var, values=options[0], state='readonly', width=27).grid(row=i, column=1, padx=5, pady=5, sticky="w")

        # Markup Required Checkbox
        ttk.Checkbutton(frame, text="Markup Required (Price Validation)", 
                        variable=self.detail_markup_req_var, onvalue=1, offvalue=0).grid(row=len(fields), column=0, columnspan=2, pady=10, sticky="w")

        # Action Button
        self.action_button = ttk.Button(frame, textvariable=self.detail_action_var, command=self._save_or_update_vendor)
        self.action_button.grid(row=len(fields) + 1, column=0, columnspan=2, pady=10)
        
        ttk.Button(frame, text="Clear Form (Add New)", command=self._clear_detail_form).grid(row=len(fields) + 2, column=0, columnspan=2, pady=5)
        
    def _clear_detail_form(self):
        """Resets the form for adding a new vendor."""
        self.current_supplier_id = None
        self.detail_name_var.set("")
        self.detail_phone_var.set("")
        self.detail_payment_type_var.set("Cash")
        self.detail_payment_freq_var.set("Daily")
        self.detail_vendor_type_var.set("Chicken")
        self.detail_markup_req_var.set(1)
        self.detail_action_var.set("Add New Supplier")
        self.detail_frame.config(text="Add New Vendor")
        if self.vendor_tree.selection():
            self.vendor_tree.selection_remove(self.vendor_tree.selection())

    def _load_vendor_details_into_form(self, vendor_data):
        """Loads data from a selected vendor into the form for editing."""
        self.current_supplier_id = vendor_data['SupplierID']
        self.detail_name_var.set(vendor_data['SupplierName'])
        self.detail_phone_var.set(vendor_data['PhoneNumber'] if vendor_data['PhoneNumber'] else "")
        self.detail_payment_type_var.set(vendor_data['PreferredPaymentType'])
        self.detail_payment_freq_var.set(vendor_data['PaymentFrequency'])
        self.detail_vendor_type_var.set(vendor_data['VendorType'])
        self.detail_markup_req_var.set(vendor_data['MarkupRequired'])
        self.detail_action_var.set("Update Vendor Details")
        self.detail_frame.config(text=f"Edit Vendor: {vendor_data['SupplierName']}")

    def _update_due_display_and_load_edit(self, event):
        """Handles vendor selection: updates due display and loads details for editing."""
        if not self.vendor_tree.selection(): 
             self.due_label_var.set("Select a vendor to view balance.")
             self._clear_detail_form()
             return
        
        selected_item = self.vendor_tree.selection()[0]
        vendor_name = self.vendor_tree.item(selected_item, 'values')[0]
        
        # 1. Update Due Display
        self._calculate_vendor_due(vendor_name)
        
        # 2. Load Details for Edit
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT SupplierID, SupplierName, PhoneNumber, PreferredPaymentType, PaymentFrequency, VendorType, MarkupRequired FROM Suppliers WHERE SupplierName = ?", (vendor_name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            vendor_data = {
                'SupplierID': row[0],
                'SupplierName': row[1],
                'PhoneNumber': row[2],
                'PreferredPaymentType': row[3],
                'PaymentFrequency': row[4],
                'VendorType': row[5],
                'MarkupRequired': row[6]
            }
            self._load_vendor_details_into_form(vendor_data)

    def _delete_selected_vendor(self):
        """Handles the deletion of the currently selected vendor."""
        if not self.vendor_tree.selection():
            messagebox.showwarning("Warning", "Please select a vendor to remove.")
            return

        selected_item = self.vendor_tree.selection()[0]
        vendor_name = self.vendor_tree.item(selected_item, 'values')[0]
        supplier_id = int(selected_item) # Treeview iid is the SupplierID
        
        confirmation = messagebox.askyesno(
            "Confirm Deletion",
            f"Are you absolutely sure you want to remove the vendor '{vendor_name}'?\n\n"
            "**WARNING:** This will permanently delete ALL associated bills, ledger entries, and markup rules!"
        )
        
        if confirmation:
            if delete_vendor_and_cleanup(supplier_id, vendor_name):
                messagebox.showinfo("Success", f"Vendor '{vendor_name}' and all associated data have been permanently removed.")
                self._clear_detail_form()
                self.load_vendor_list()
                self.master_app.markup_rules_cache = {} # Clear cache
            else:
                messagebox.showerror("Error", f"Failed to remove vendor '{vendor_name}'. Check database connection.")


    def _save_or_update_vendor(self):
        name = self.detail_name_var.get().strip()
        phone = self.detail_phone_var.get().strip()
        payment_type = self.detail_payment_type_var.get()
        frequency = self.detail_payment_freq_var.get()
        v_type = self.detail_vendor_type_var.get()
        markup_req = self.detail_markup_req_var.get()
        
        if not name:
            messagebox.showerror("Error", "Supplier name cannot be empty.")
            return

        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            if self.current_supplier_id is None: # Insert
                cursor.execute("""
                    INSERT INTO Suppliers (SupplierName, PhoneNumber, PreferredPaymentType, PaymentFrequency, VendorType, MarkupRequired) 
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (name, phone, payment_type, frequency, v_type, markup_req))
                messagebox.showinfo("Success", f"Supplier '{name}' added.")
            else: # Update
                # Check if the name has changed to prevent IntegrityError if it matches another existing name
                cursor.execute("SELECT SupplierName FROM Suppliers WHERE SupplierID = ?", (self.current_supplier_id,))
                old_name = cursor.fetchone()[0]
                if old_name != name:
                    cursor.execute("SELECT SupplierID FROM Suppliers WHERE SupplierName = ?", (name,))
                    if cursor.fetchone():
                        raise sqlite3.IntegrityError("Name clash during update.")
                        
                cursor.execute("""
                    UPDATE Suppliers SET SupplierName=?, PhoneNumber=?, PreferredPaymentType=?, PaymentFrequency=?, VendorType=?, MarkupRequired=?
                    WHERE SupplierID=?
                """, (name, phone, payment_type, frequency, v_type, markup_req, self.current_supplier_id))
                messagebox.showinfo("Success", f"Supplier '{name}' updated.")
                
            conn.commit()
            self._clear_detail_form()
            self.load_vendor_list() # Reload list and notify main app
            
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", f"Supplier name '{name}' already exists.")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save supplier: {e}")
        finally:
            conn.close()


    def load_vendor_list(self):
        """Loads all supplier names and details into the vendor list treeview."""
        # Fetch full details
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT SupplierID, SupplierName, PhoneNumber, PreferredPaymentType, PaymentFrequency, VendorType, MarkupRequired FROM Suppliers ORDER BY SupplierName")
        rows = cursor.fetchall()
        conn.close()
        
        self.suppliers = [row[1] for row in rows] # Update local list for comboboxes
        
        # Clear existing data
        self.vendor_tree.delete(*self.vendor_tree.get_children())
        
        for row in rows:
            supplier_id, name, phone, p_type, freq, v_type, markup_req = row
            markup_display = 'Yes' if markup_req == 1 else 'No'
            display_values = (name, v_type, phone if phone else 'N/A', p_type, freq, markup_display)
            self.vendor_tree.insert('', tk.END, iid=supplier_id, values=display_values)
            
        self.update_app_data_callback(self.suppliers) # Notify main app to update comboboxes
        
        # Update markup combo if it exists
        if hasattr(self, 'markup_vendor_combo'):
            self.markup_vendor_combo['values'] = self.suppliers
            if self.suppliers and not self.markup_vendor_var.get():
                self.markup_vendor_var.set(self.suppliers[0])
                self._load_markups_to_grid()

    # --- Markup Rules Management Changes ---
    def _setup_markup_management_frame(self, frame):
        # Controls (Supplier Selection)
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill='x', pady=5)
        
        ttk.Label(control_frame, text="Select Vendor:").pack(side=tk.LEFT, padx=5)
        self.markup_vendor_var = tk.StringVar()
        self.markup_vendor_combo = ttk.Combobox(control_frame, textvariable=self.markup_vendor_var, state='readonly', width=20)
        self.markup_vendor_combo.pack(side=tk.LEFT, padx=5)
        self.markup_vendor_combo.bind('<<ComboboxSelected>>', lambda e: self._load_markups_to_grid())
        
        self.add_markup_button = ttk.Button(control_frame, text="Add New Markup Rule", command=self._add_new_markup_rule)
        self.add_markup_button.pack(side=tk.RIGHT)
        
        # Treeview for Markups
        self.markup_tree = ttk.Treeview(frame, columns=('Item', 'Base', 'Op1', 'Val1', 'Op2', 'Val2'), show='headings', selectmode='browse')
        self.markup_tree.heading('Item', text='Item Name')
        self.markup_tree.heading('Base', text='Base Rate Type')
        self.markup_tree.heading('Op1', text='Op1')
        self.markup_tree.heading('Val1', text='Value1')
        self.markup_tree.heading('Op2', text='Op2')
        self.markup_tree.heading('Val2', text='Value2')
        self.markup_tree.pack(fill='both', expand=True, pady=10)
        
        # Set initial combo values
        self.markup_vendor_combo['values'] = self.suppliers
        if self.suppliers:
            self.markup_vendor_var.set(self.suppliers[0])
            self._load_markups_to_grid()

    def _load_markups_to_grid(self):
        """
        Loads markup rules for the selected vendor. 
        Auto-populates default rules if it's a new Chicken vendor.
        """
        vendor = self.markup_vendor_var.get()
        if not vendor: return

        # Get current rules and vendor type
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Check if markup is required and get vendor type
        cursor.execute("SELECT MarkupRequired, VendorType FROM Suppliers WHERE SupplierName = ?", (vendor,))
        markup_info = cursor.fetchone()
        
        is_required = markup_info and markup_info[0] == 1
        vendor_type = markup_info[1] if markup_info else "Unknown"
        
        # 1. Check if rules already exist for this vendor
        cursor.execute("SELECT COUNT(*) FROM Markups WHERE SupplierName = ?", (vendor,))
        rule_count = cursor.fetchone()[0]
        conn.close() # Close connection to perform potential database writes outside this fetch
        
        # 2. Automatically populate defaults if it's a Chicken vendor AND no rules exist
        if rule_count == 0 and vendor_type == 'Chicken' and is_required:
            if insert_default_markups(vendor, DEFAULT_CHICKEN_MARKUP_RULES):
                messagebox.showinfo("Auto-Populated", f"Default markup rules for 'Chicken' vendor '{vendor}' have been automatically created.")
                # We do not need to call fetch_vendor_type again as we know the type
        
        # Clear existing data in the grid
        self.markup_tree.delete(*self.markup_tree.get_children())
        
        if not is_required:
            self.markup_tree.insert('', tk.END, values=('N/A', f"Vendor Type: {vendor_type}", 'N/A', 'N/A', 'N/A', 'N/A'))
            self.markup_tree.bind('<Double-1>', lambda e: 'break') # Disable editing
            self.add_markup_button.config(state=tk.DISABLED)
            return

        self.markup_tree.bind('<Double-1>', self._start_markup_edit) # Re-enable editing
        self.add_markup_button.config(state=tk.NORMAL)
        
        # Original loading logic (or loading the newly inserted rules)
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        query = "SELECT ItemID, ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2 FROM Markups WHERE SupplierName = ?"
        cursor.execute(query, (vendor,))
        rows = cursor.fetchall()
        conn.close()

        for row in rows:
            item_id = row[0]
            values = row[1:]
            display_values = [str(v) if v is not None else '' for v in values]
            self.markup_tree.insert('', tk.END, iid=item_id, values=display_values)
        
        # Clear the calculation cache in the main app after loading new rules
        self.master_app.markup_rules_cache = {}

    def _start_markup_edit(self, event):
        """Allows in-place editing of markup rules. ItemName is now always editable."""
        if not self.markup_tree.selection(): return
        
        item_id = self.markup_tree.selection()[0]
        column = self.markup_tree.identify_column(event.x)
        column_index = int(column.replace('#', '')) - 1
        
        # 0:Item, 1:Base, 2:Op1, 3:Val1, 4:Op2, 5:Val2
        
        # All columns are editable now, but only 1, 2, 4 use a combobox. 0, 3, 5 use an entry.
        editable_cols = [0, 1, 2, 3, 4, 5]
        
        if column_index in editable_cols:
            x, y, width, height = self.markup_tree.bbox(item_id, column)
            current_value = self.markup_tree.item(item_id, 'values')[column_index]
            
            if column_index in [1, 2, 4]: 
                # Base Rate Type and Operators use a Combobox
                options = {
                    1: ['TandoorRate', 'BoilerRate', 'EggRate'],
                    2: ['+', '-', '*', '/', ''],
                    4: ['+', '-', '*', '/', '']
                }.get(column_index, [])
                self._create_markup_combobox_editor(item_id, column, column_index, x, y, width, height, current_value, options)
            else: 
                # Item Name, Value1, Value2 use an Entry
                self._create_markup_entry_editor(item_id, column, column_index, x, y, width, height, current_value)


    def _create_markup_combobox_editor(self, item_id, column, col_idx, x, y, w, h, value, options):
        combo = ttk.Combobox(self.markup_tree, values=options, state='readonly')
        combo.set(value)
        combo.place(x=x, y=y, width=w, height=h, anchor='nw')
        combo.focus()

        def save_edit(event):
            # Check if the widget still exists before trying to destroy and save
            if not combo.winfo_exists(): return 
            
            # Use 'break' to stop propagation if save is called due to selection or return, 
            # to prevent FocusOut from firing and saving twice
            if event.type == '5' or event.keysym == 'Return': 
                new_value = combo.get()
                current_values = list(self.markup_tree.item(item_id, 'values'))
                current_values[col_idx] = new_value if new_value else None
                self.markup_tree.item(item_id, values=current_values)
                self._save_markup_change(item_id, current_values)
                combo.destroy()
                return 'break'
            
            # If FocusOut (type 9), save and destroy
            elif event.type == '9': 
                new_value = combo.get()
                current_values = list(self.markup_tree.item(item_id, 'values'))
                current_values[col_idx] = new_value if new_value else None
                self.markup_tree.item(item_id, values=current_values)
                self._save_markup_change(item_id, current_values)
                combo.destroy()
            
        # FIX: Ensure saving on selection, return, and loss of focus
        combo.bind('<<ComboboxSelected>>', save_edit)
        combo.bind('<Return>', save_edit)
        combo.bind('<FocusOut>', save_edit) 

    def _create_markup_entry_editor(self, item_id, column, col_idx, x, y, w, h, value):
        # Used for ItemName, Value1, and Value2
        entry = ttk.Entry(self.markup_tree)
        entry.insert(0, value)
        entry.place(x=x, y=y, width=w, height=h, anchor='nw')
        entry.focus()
        
        def save_edit(event):
            # Check if the widget still exists before trying to destroy and save
            if not entry.winfo_exists(): return
            
            new_value = entry.get().strip()
            current_values = list(self.markup_tree.item(item_id, 'values'))
            
            try:
                # Value columns (3, 5) must be float or None
                if col_idx in [3, 5]: 
                    if new_value:
                        new_value = float(new_value)
                    else:
                        new_value = None
                # Item Name column (0) must be string
                elif col_idx == 0 and not new_value:
                    messagebox.showerror("Input Error", "Item Name cannot be empty.")
                    entry.destroy()
                    return

            except ValueError:
                messagebox.showerror("Input Error", "Markup values must be numbers.")
                entry.destroy()
                return

            current_values[col_idx] = new_value
            self.markup_tree.item(item_id, values=current_values)
            self._save_markup_change(item_id, current_values)
            entry.destroy()
        
        entry.bind('<Return>', save_edit)
        entry.bind('<FocusOut>', save_edit) 
        
    def _save_markup_change(self, item_id, values):
        """Persists the edited/new markup rule to the database."""
        vendor = self.markup_vendor_var.get()
        # Item, Base, Op1, Val1, Op2, Val2
        item, base, op1, val1, op2, val2 = [v if v != '' else None for v in values]
        
        # Convert float strings to float or keep as None
        val1_db = float(val1) if val1 is not None and val1 != 'None' else None
        val2_db = float(val2) if val2 is not None and val2 != 'None' else None
        op1_db = op1
        op2_db = op2
        item_db = item.strip() # Ensure item name is clean

        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            
            if not item_db:
                 raise ValueError("Item Name cannot be empty.")
            
            # Temporary rules (Item ID < 0) need to be treated as new insertions
            if int(item_id) > 0: # Existing rule (UPDATE)
                # Check for name change conflict only if item name actually changed
                # Note: We rely on the values already updated in the treeview for item_db
                cursor.execute("SELECT ItemName FROM Markups WHERE ItemID = ?", (item_id,))
                old_item_name = cursor.fetchone()[0]
                
                if old_item_name != item_db:
                    cursor.execute("SELECT ItemID FROM Markups WHERE SupplierName = ? AND ItemName = ? AND ItemID != ?", 
                                   (vendor, item_db, item_id))
                    if cursor.fetchone():
                        raise sqlite3.IntegrityError("Name clash during update.")
                
                cursor.execute("""
                    UPDATE Markups SET ItemName=?, BaseRateType=?, MarkupOperator1=?, MarkupValue1=?, MarkupOperator2=?, MarkupValue2=?
                    WHERE ItemID=? AND SupplierName=?
                """, (item_db, base, op1_db, val1_db, op2_db, val2_db, item_id, vendor))
            else: # New rule (INSERT)
                # Check for item existence
                cursor.execute("SELECT ItemID FROM Markups WHERE SupplierName = ? AND ItemName = ?", (vendor, item_db))
                if cursor.fetchone():
                    raise sqlite3.IntegrityError("A rule for this Item/Vendor combination already exists.")
                        
                cursor.execute("""
                    INSERT INTO Markups (SupplierName, ItemName, BaseRateType, MarkupOperator1, MarkupValue1, MarkupOperator2, MarkupValue2)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (vendor, item_db, base, op1_db, val1_db, op2_db, val2_db))
            
            conn.commit()
            self.update_app_data_callback() # Refresh item list in main app
            self._load_markups_to_grid() # Reload grid
            messagebox.showinfo("Success", f"Markup for '{item_db}' updated/saved.")
            self.master_app.markup_rules_cache = {} # Clear cache
            
        except sqlite3.IntegrityError as se:
            messagebox.showerror("Error", f"A rule conflict occurred: {se}")
        except ValueError as ve:
             messagebox.showerror("Input Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save markup: {e}")
        finally:
            conn.close()

    def _add_new_markup_rule(self):
        """Adds a temporary row to the markup grid for a new entry."""
        vendor = self.markup_vendor_var.get()
        if not vendor:
            messagebox.showwarning("Warning", "Please select a vendor first.")
            return

        # Use a negative ID to denote a temporary, unsaved row
        temp_id = -(len(self.markup_tree.get_children()) + 1)
        # Default values for a new rule, Item Name starts as empty editable string
        self.markup_tree.insert('', 0, iid=temp_id, values=['', 'TandoorRate', '+', 0.0, '', ''])
        self.markup_tree.selection_set(temp_id)
        self.markup_tree.focus(temp_id)
        
    # --- Vendor Ledger & Dues (Remaining methods are the same) ---
    def _setup_vendor_ledger_frame(self, frame):
        # Top: Due Balance Display
        self.ledger_due_var = tk.StringVar(value="Select a Vendor to calculate balance.")
        ttk.Label(frame, textvariable=self.ledger_due_var, font=('Arial', 12, 'bold'), foreground='red').pack(pady=10)

        # Middle: Payment Entry
        payment_frame = ttk.LabelFrame(frame, text="Record Vendor Payment", padding="10")
        payment_frame.pack(fill='x', pady=10)
        
        ttk.Label(payment_frame, text="Vendor:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.payment_vendor_var = tk.StringVar()
        self.payment_vendor_combo = ttk.Combobox(payment_frame, textvariable=self.payment_vendor_var, values=self.suppliers, state='readonly', width=20)
        self.payment_vendor_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(payment_frame, text="Amount Paid:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.payment_amount_var = tk.DoubleVar()
        ttk.Entry(payment_frame, textvariable=self.payment_amount_var, width=15).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ttk.Label(payment_frame, text="Date:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.payment_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        ttk.Entry(payment_frame, textvariable=self.payment_date_var, width=15, state='readonly').grid(row=2, column=1, padx=5, pady=5, sticky="w")
        ttk.Button(payment_frame, text="📅", command=lambda: self._open_calendar_popup(self.payment_date_var)).grid(row=2, column=2, padx=5, pady=5)
        
        ttk.Button(payment_frame, text="Record Payment", command=self._record_payment).grid(row=3, column=0, columnspan=3, pady=10)

        # Bottom: Ledger View
        self.ledger_tree = ttk.Treeview(frame, columns=('Date', 'Type', 'Amount', 'Details'), show='headings', selectmode='browse')
        self.ledger_tree.heading('Date', text='Date')
        self.ledger_tree.heading('Type', text='Transaction Type')
        self.ledger_tree.heading('Amount', text='Amount')
        self.ledger_tree.heading('Details', text='Details')
        self.ledger_tree.pack(fill='both', expand=True, pady=10)
        
        self.payment_vendor_combo.bind('<<ComboboxSelected>>', self._load_vendor_ledger)
        
        # Configure Ledger tags on the Treeview itself
        self.ledger_tree.tag_configure('payment_tx', foreground='green')
        self.ledger_tree.tag_configure('bill_tx', foreground='red')

    def _record_payment(self):
        vendor = self.payment_vendor_var.get()
        amount = self.payment_amount_var.get()
        date = self.payment_date_var.get()
        
        if not vendor or amount <= 0:
            messagebox.showwarning("Warning", "Please select a vendor and enter a valid amount.")
            return

        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO VendorLedger (Date, SupplierName, TransactionType, Amount, Details)
                VALUES (?, ?, ?, ?, ?)
            """, (date, vendor, 'Payment', -abs(amount), f"Payment recorded on {date}"))
            conn.commit()
            
            messagebox.showinfo("Success", f"Payment of {amount:.2f} recorded for {vendor}.")
            self.payment_amount_var.set(0.0)
            self._load_vendor_ledger(None) 
            self.load_vendor_list() # Refresh due in vendor list

        except Exception as e:
            messagebox.showerror("Error", f"Failed to record payment: {e}")
        finally:
            conn.close()
            
    def _load_vendor_ledger(self, event):
        """Loads all transactions (Bills and Payments) for the selected vendor."""
        vendor = self.payment_vendor_var.get()
        if not vendor: return

        self.ledger_tree.delete(*self.ledger_tree.get_children())
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sum of Bills (debit)
        bill_query = """
            SELECT Date, 'Bill' AS Type, SUM(Qty * VendorRate) AS Amount, 'Bill Total' AS Details
            FROM BillEntries WHERE SupplierName = ?
            GROUP BY Date
        """
        cursor.execute(bill_query, (vendor,))
        bills = cursor.fetchall()
        
        payment_query = "SELECT Date, TransactionType, Amount, Details FROM VendorLedger WHERE SupplierName = ?"
        cursor.execute(payment_query, (vendor,))
        payments = cursor.fetchall()
        conn.close()
        
        all_transactions = bills + [(p[0], p[1], p[2], p[3]) for p in payments]
        all_transactions.sort(key=lambda x: x[0], reverse=True)
        
        for tx in all_transactions:
            amount = tx[2]
            tag = 'payment_tx' if amount < 0 else 'bill_tx' 
            display_amount = f"{abs(amount):,.2f}"
            
            self.ledger_tree.insert('', tk.END, values=(tx[0], tx[1], display_amount, tx[3]), tags=(tag,))
        
        self._calculate_vendor_due(vendor)

    def _calculate_vendor_due(self, vendor):
        """Calculates the current net due balance for a vendor."""
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Sum of Bills (debit)
        cursor.execute("SELECT IFNULL(SUM(Qty * VendorRate), 0.0) FROM BillEntries WHERE SupplierName = ?", (vendor,))
        total_bills = cursor.fetchone()[0] or 0.0
        
        # Sum of Payments (credit, already stored as negative in ledger)
        cursor.execute("SELECT IFNULL(SUM(Amount), 0.0) FROM VendorLedger WHERE SupplierName = ?", (vendor,))
        total_payments = cursor.fetchone()[0] or 0.0
        
        conn.close()
        
        due_balance = round(total_bills + total_payments, 2)
        
        text = ""
        if due_balance > 0:
            text = f"NET DUE: ₹{due_balance:,.2f}"
        elif due_balance < 0:
            text = f"OVERPAID: ₹{-due_balance:,.2f}"
        else:
            text = "BALANCE: ₹0.00"
            
        self.ledger_due_var.set(text)
        # Update the due label in the list frame too
        self.due_label_var.set(text.replace("NET DUE:", "DUE:").replace("OVERPAID:", "OVERPAID:"))