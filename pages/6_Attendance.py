import streamlit as st
import pandas as pd
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chicken_db
import utils

utils.apply_styling()

st.header("Attendance & Staff Management")

# Create tables
conn = utils.get_db_connection()
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS Employees (
        EmployeeID INTEGER PRIMARY KEY,
        Name TEXT NOT NULL,
        Role TEXT,
        Department TEXT,
        MonthlySalary REAL DEFAULT 0,
        DateOfJoining TEXT,
        Status TEXT DEFAULT 'Active',
        LastWorkingDate TEXT
    )
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS Attendance (
        ID INTEGER PRIMARY KEY,
        Date TEXT NOT NULL,
        EmployeeID INTEGER NOT NULL,
        Status TEXT NOT NULL,
        OTHours REAL DEFAULT 0,
        Remarks TEXT,
        FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID),
        UNIQUE(Date, EmployeeID)
    )
""")

conn.commit()
conn.close()

tab1, tab2, tab3 = st.tabs(["Daily Attendance", "Employee Master", "Reports"])

with tab1:
    st.subheader("Mark Attendance")
    
    attendance_date = st.date_input("Select Date", datetime.now())
    date_str = attendance_date.strftime("%Y-%m-%d")
    
    conn = utils.get_db_connection()
    
    # Get all active employees
    df_employees = pd.read_sql_query(
        "SELECT EmployeeID, Name, Role FROM Employees WHERE Status = 'Active'",
        conn
    )
    
    if df_employees.empty:
        st.warning("No active employees found. Please add employees in the 'Employee Master' tab.")
    else:
        # Load existing attendance for the date
        df_attendance = pd.read_sql_query("""
            SELECT a.EmployeeID, e.Name, e.Role, a.Status, a.OTHours, a.Remarks
            FROM Attendance a
            JOIN Employees e ON a.EmployeeID = e.EmployeeID
            WHERE a.Date = ?
        """, conn, params=(date_str,))
        
        # If no attendance, create template from employees
        if df_attendance.empty:
            df_attendance = df_employees.copy()
            df_attendance["Status"] = "Present"
            df_attendance["OTHours"] = 0.0
            df_attendance["Remarks"] = ""
        
        st.markdown("### Attendance Grid")
        edited_attendance = st.data_editor(
            df_attendance,
            column_config={
                "EmployeeID": st.column_config.NumberColumn(disabled=True),
                "Name": st.column_config.TextColumn(disabled=True),
                "Role": st.column_config.TextColumn(disabled=True),
                "Status": st.column_config.SelectboxColumn(
                    options=["Present", "Absent", "Half-day", "Leave"],
                    required=True
                ),
                "OTHours": st.column_config.NumberColumn(min_value=0.0, max_value=12.0, step=0.5, label="OT Hours"),
                "Remarks": st.column_config.TextColumn()
            },
            hide_index=True,
            width="stretch",
            key="attendance_editor"
        )
        
        # Summary
        present_count = len(edited_attendance[edited_attendance["Status"] == "Present"])
        absent_count = len(edited_attendance[edited_attendance["Status"] == "Absent"])
        
        col_a1, col_a2, col_a3 = st.columns(3)
        col_a1.metric("Present", present_count)
        col_a2.metric("Absent", absent_count)
        col_a3.metric("Total OT Hours", f"{edited_attendance['OTHours'].sum():.1f}")
        
        if st.button("Save Attendance", type="primary"):
            try:
                conn = utils.get_db_connection()
                cursor = conn.cursor()
                
                # Delete existing attendance for this date
                cursor.execute("DELETE FROM Attendance WHERE Date = ?", (date_str,))
                
                # Insert new attendance
                entries = []
                for _, row in edited_attendance.iterrows():
                    entries.append((
                        date_str,
                        row["EmployeeID"],
                        row["Status"],
                        row["OTHours"],
                        row["Remarks"]
                    ))
                
                cursor.executemany("""
                    INSERT INTO Attendance (Date, EmployeeID, Status, OTHours, Remarks)
                    VALUES (?, ?, ?, ?, ?)
                """, entries)
                
                conn.commit()
                conn.close()
                st.success(f"Attendance for {date_str} saved successfully!")
            except Exception as e:
                st.error(f"Error saving attendance: {e}")
    
    conn.close()

with tab2:
    st.subheader("Employee Master")
    
    conn = utils.get_db_connection()
    df_all_employees = pd.read_sql_query("SELECT * FROM Employees", conn)
    conn.close()
    
    if not df_all_employees.empty:
        st.markdown("### Existing Employees")
        edited_employees = st.data_editor(
            df_all_employees,
            column_config={
                "EmployeeID": st.column_config.NumberColumn(disabled=True),
                "Status": st.column_config.SelectboxColumn(options=["Active", "Inactive"]),
                "MonthlySalary": st.column_config.NumberColumn(min_value=0.0, step=1000.0, format="₹%.2f")
            },
            num_rows="dynamic",
            hide_index=True,
            width="stretch",
            key="employee_editor"
        )
        
        if st.button("Save Employee Changes"):
            try:
                conn = utils.get_db_connection()
                cursor = conn.cursor()
                
                # Simple approach: delete all and re-insert
                cursor.execute("DELETE FROM Employees")
                
                entries = []
                for _, row in edited_employees.iterrows():
                    if row["Name"]:
                        entries.append((
                            row["Name"],
                            row["Role"],
                            row["Department"],
                            row["MonthlySalary"],
                            row["DateOfJoining"],
                            row["Status"],
                            row["LastWorkingDate"]
                        ))
                
                if entries:
                    cursor.executemany("""
                        INSERT INTO Employees (Name, Role, Department, MonthlySalary, DateOfJoining, Status, LastWorkingDate)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, entries)
                
                conn.commit()
                conn.close()
                st.success("Employee data updated!")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating employees: {e}")
    
    with st.expander("Add New Employee"):
        with st.form("add_employee"):
            new_name = st.text_input("Name")
            new_role = st.text_input("Role")
            new_dept = st.selectbox("Department", ["Kitchen", "Service", "Delivery", "Management", "Other"])
            new_salary = st.number_input("Monthly Salary", min_value=0.0, step=1000.0)
            new_doj = st.date_input("Date of Joining", datetime.now())
            
            if st.form_submit_button("Add Employee"):
                try:
                    conn = utils.get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO Employees (Name, Role, Department, MonthlySalary, DateOfJoining, Status)
                        VALUES (?, ?, ?, ?, ?, 'Active')
                    """, (new_name, new_role, new_dept, new_salary, new_doj.strftime("%Y-%m-%d")))
                    conn.commit()
                    conn.close()
                    st.success(f"Employee {new_name} added!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error adding employee: {e}")

with tab3:
    st.subheader("Attendance Reports")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        report_start = st.date_input("From", datetime.now().replace(day=1), key="report_start")
    with col_r2:
        report_end = st.date_input("To", datetime.now(), key="report_end")
    
    start_str = report_start.strftime("%Y-%m-%d")
    end_str = report_end.strftime("%Y-%m-%d")
    
    conn = utils.get_db_connection()
    
    df_report = pd.read_sql_query("""
        SELECT 
            e.Name,
            e.Role,
            COUNT(CASE WHEN a.Status = 'Present' THEN 1 END) as PresentDays,
            COUNT(CASE WHEN a.Status = 'Absent' THEN 1 END) as AbsentDays,
            COUNT(CASE WHEN a.Status = 'Half-day' THEN 1 END) as HalfDays,
            SUM(a.OTHours) as TotalOT
        FROM Employees e
        LEFT JOIN Attendance a ON e.EmployeeID = a.EmployeeID AND a.Date BETWEEN ? AND ?
        WHERE e.Status = 'Active'
        GROUP BY e.EmployeeID, e.Name, e.Role
    """, conn, params=(start_str, end_str))
    
    conn.close()
    
    if not df_report.empty:
        st.dataframe(df_report, hide_index=True, width="stretch")
    else:
        st.info("No attendance data for this period.")
