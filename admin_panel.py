import sys
import os
import shutil
import datetime # Added for timestamps
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, 
                             QTabWidget, QFrame, QSizePolicy, QDialog, QFormLayout, 
                             QComboBox, QTimeEdit, QScrollArea)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal, QTime

# --- PDF EXPORT IMPORTS ---
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet

from database import ElectionDatabase
# --- LOGIN & SIGNUP DIALOG ---
class AdminLoginDialog(QDialog):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.is_signup_mode = False  
        self.init_ui()

    def check_admin_exists(self):
        """Helper function to check if any admin is already in the DB"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM admins")
            count = cursor.fetchone()[0]
            conn.close()
            return count > 0
        except Exception:
            return False

    def init_ui(self):
        self.setWindowTitle("Admin Access")
        self.setFixedSize(350, 280) # Increased height slightly for the warning label
        self.setStyleSheet("background-color: white;")
        
        self.layout = QVBoxLayout(self)
        
        self.header = QLabel("ADMIN LOGIN")
        self.header.setAlignment(Qt.AlignCenter)
        self.header.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50; margin-bottom: 10px;")
        self.layout.addWidget(self.header)

        form = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter Username")
        self.username_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 5px;")
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("Enter Password")
        self.password_input.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 5px;")
        
        form.addRow("Username:", self.username_input)
        form.addRow("Password:", self.password_input)
        self.layout.addLayout(form)

        self.action_btn = QPushButton("Login")
        self.action_btn.setStyleSheet("""
            QPushButton { background-color: #2980b9; color: white; padding: 10px; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background-color: #2471a3; }
        """)
        self.action_btn.clicked.connect(self.handle_auth)
        self.layout.addWidget(self.action_btn)

        # --- SECURITY CHANGE: HIDE SIGNUP BUTTON IF ADMIN EXISTS ---
        self.toggle_btn = QPushButton("Don't have an account? Sign Up")
        self.toggle_btn.setStyleSheet("color: #7f8c8d; border: none; font-size: 11px; text-decoration: underline;")
        self.toggle_btn.clicked.connect(self.toggle_mode)
        self.layout.addWidget(self.toggle_btn)

        # Check at startup: if an admin exists, hide the signup option
        if self.check_admin_exists():
            self.toggle_btn.setVisible(False)
            self.footer_msg = QLabel("Registration is locked (Admin already exists)")
            self.footer_msg.setAlignment(Qt.AlignCenter)
            self.footer_msg.setStyleSheet("color: #95a5a6; font-size: 10px; font-style: italic;")
            self.layout.addWidget(self.footer_msg)

    def toggle_mode(self):
        # Final security check before switching to signup mode
        if not self.is_signup_mode and self.check_admin_exists():
            QMessageBox.warning(self, "Security", "Unauthorized Access: Signup is disabled.")
            return

        self.is_signup_mode = not self.is_signup_mode
        if self.is_signup_mode:
            self.header.setText("CREATE ADMIN ACCOUNT")
            self.action_btn.setText("Register New Admin")
            self.action_btn.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
            self.toggle_btn.setText("Already have an account? Login")
        else:
            self.header.setText("ADMIN LOGIN")
            self.action_btn.setText("Login")
            self.action_btn.setStyleSheet("background-color: #2980b9; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
            self.toggle_btn.setText("Don't have an account? Sign Up")

    def handle_auth(self):
        user = self.username_input.text().strip()
        pw = self.password_input.text().strip()
        
        if not user or not pw:
            QMessageBox.warning(self, "Input Error", "Please enter both username and password.")
            return

        conn = self.db.connect()
        cursor = conn.cursor()

        if self.is_signup_mode:
            # Double Check: Prevent registration if someone bypassed the UI
            if self.check_admin_exists():
                QMessageBox.critical(self, "Error", "Signup blocked by security policy.")
                conn.close()
                return

            try:
                cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (user, pw))
                conn.commit()
                QMessageBox.information(self, "Success", "Account created! Please login.")
                # After successful signup, hide the button so no one else can sign up
                self.toggle_btn.setVisible(False)
                self.toggle_mode()
            except Exception:
                QMessageBox.warning(self, "Error", "Username might already exist.")
        else:
            cursor.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (user, pw))
            if cursor.fetchone():
                self.accept()
            else:
                QMessageBox.warning(self, "Access Denied", "Invalid Username or Password!")
        conn.close()

# --- ADMIN PANEL MAIN VIEW ---
class AdminPanel(QWidget):
    switch_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.db = ElectionDatabase()
        self.logo_path = ""
        self.init_ui()

    # --- NEW PDF EXPORT ENGINE ---
    def export_to_pdf(self, table_widget, title):
        """Generic function to convert any QTableWidget to a PDF file"""
        path, _ = QFileDialog.getSaveFileName(self, "Export PDF", f"{title}.pdf", "PDF Files (*.pdf)")
        if not path:
            return

        try:
            doc = SimpleDocTemplate(path, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            # Add Title and Timestamp
            elements.append(Paragraph(f"<b>{title.upper()}</b>", styles['Title']))
            elements.append(Paragraph(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
            elements.append(Spacer(1, 20))

            # Extract Data from Table
            data = []
            headers = [table_widget.horizontalHeaderItem(i).text() for i in range(table_widget.columnCount())]
            # Exclude 'Action' columns from PDF
            clean_headers = [h for h in headers if h.lower() != "action"]
            data.append(clean_headers)

            for row in range(table_widget.rowCount()):
                row_data = []
                for col in range(table_widget.columnCount()):
                    header_text = table_widget.horizontalHeaderItem(col).text().lower()
                    if header_text == "action":
                        continue
                    
                    item = table_widget.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)

            # Create PDF Table
            pdf_table = Table(data)
            style = TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ])
            pdf_table.setStyle(style)
            elements.append(pdf_table)

            doc.build(elements)
            QMessageBox.information(self, "Success", f"PDF exported successfully to {path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate PDF: {e}")

    def init_ui(self):
        self.setWindowTitle("Admin Management Panel")
        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignCenter)

        self.container = QFrame()
        self.container.setMinimumWidth(1100)
        self.container.setStyleSheet("QFrame { background-color: white; border: 1px solid #dcdde1; border-radius: 12px; }")
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        
        # Header Bar
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← Logout")
        back_btn.setFixedWidth(80)
        back_btn.setStyleSheet("padding: 5px; background: #ecf0f1; border-radius: 5px; color: #2c3e50; font-size: 11px;")
        back_btn.clicked.connect(self.switch_back.emit)
        top_bar.addWidget(back_btn)
        
        header = QLabel("ADMIN CONTROL PANEL")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #2c3e50; border: none;")
        top_bar.addWidget(header)
        top_bar.addStretch() 
        container_layout.addLayout(top_bar)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; }
            QTabBar::tab { padding: 12px 25px; font-weight: bold; min-width: 150px; font-size: 12px; }
            QTabBar::tab:selected { background: #34495e; color: white; }
        """)
        
        # Setup Tabs
        self.voter_tab = QWidget()
        self.setup_voter_tab()
        self.tabs.addTab(self.voter_tab, "Voter Management")

        self.enrolled_tab_widget = QWidget()
        self.setup_enrolled_tab()
        self.tabs.addTab(self.enrolled_tab_widget, "Enrolled Voters")

        # NEW TAB: Voted List
        self.voted_tab_widget = QWidget()
        self.setup_voted_tab()
        self.tabs.addTab(self.voted_tab_widget, "Voted People List")

        self.cand_tab = QWidget()
        self.setup_candidate_tab()
        self.tabs.addTab(self.cand_tab, "Candidate & Results")

        container_layout.addWidget(self.tabs)
        outer_layout.addWidget(self.container)
        self.setLayout(outer_layout)
        # 5. NEW TAB: System Controls
        self.system_tab = QWidget()
        self.setup_system_tab() # We will define this method below
        self.tabs.addTab(self.system_tab, "⚙️ System Controls")

    def refresh_class_dropdowns(self):
        """Manually populates dropdowns with all specific academic class options"""
        try:
            # 1. Define your manual list of all possible classes
            classes = [
                "All",
                # Even Semester Classes
                "S2 A", "S2 B", "S2 C", "S2 D", "S2 E", 
                "S4 A", "S4 B", "S4 C", "S4 D", "S4 E", 
                "S6 A", "S6 B", "S6 C", "S6 D", "S6 E", 
                "S8 A", "S8 B", "S8 C", "S8 D", "S8 E", 
                "MCA S2", "MCA S4",
                # Odd Semester Classes
                "S1 A", "S1 B", "S1 C", "S1 D", "S1 E", 
                "S3 A", "S3 B", "S3 C", "S3 D", "S3 E", 
                "S5 A", "S5 B", "S5 C", "S5 D", "S5 E", 
                "S7 A", "S7 B", "S7 C", "S7 D", "S7 E", 
                "MCA S1", "MCA S3"
            ]

            # 2. Sort the list (optional) but keep "All" at the top
            # sorted_classes = ["All"] + sorted([c for c in classes if c != "All"])

            # 3. Apply to all dropdowns in the Admin Panel
            dropdowns = [
                self.voter_class_filter, 
                self.enroll_class_filter, 
                self.voted_class_filter
            ]

            for cb in dropdowns:
                cb.blockSignals(True)   # Prevents triggering search until list is ready
                cb.clear()
                cb.addItems(classes)    # Use 'classes' or 'sorted_classes'
                cb.blockSignals(False)
                
        except Exception as e:
            print(f"Error refreshing classes: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        login = AdminLoginDialog(self.db)
        if login.exec_() != QDialog.Accepted:
            self.switch_back.emit() 
        else:
            self.refresh_all_data()

    def refresh_all_data(self):
        self.refresh_class_dropdowns()
        self.load_voters_master()
        self.load_enrolled_voters()
        self.load_voted_list()
        self.load_candidates()

    def setup_voter_tab(self):
        layout = QVBoxLayout()
        filter_layout = QHBoxLayout()
        
        # 1. SEARCH BAR
        filter_layout.addWidget(QLabel("Search:"))
        self.voter_search_input = QLineEdit()
        self.voter_search_input.setPlaceholderText("Search Name or Reg No...")
        self.voter_search_input.setFixedWidth(200)
        self.voter_search_input.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.voter_search_input.textChanged.connect(self.load_voters_master)
        filter_layout.addWidget(self.voter_search_input)
        
        filter_layout.addSpacing(15) 

        # 2. DEPARTMENT FILTER
        filter_layout.addWidget(QLabel("Department:"))
        self.voter_dept_filter = QComboBox()
        self.voter_dept_filter.addItems([
            "All", 
            "Computer Science & Engineering", 
            "Artificial Intelligence & Machine Learning", 
            "Master of Computer Applications (M.C.A)", 
            "Electrical & Electronics Engineering", 
            "Electronics and Communication Engineering"
        ])
        self.voter_dept_filter.currentTextChanged.connect(self.load_voters_master)
        filter_layout.addWidget(self.voter_dept_filter)

        # 3. CLASS FILTER
        filter_layout.addWidget(QLabel("Class:"))
        self.voter_class_filter = QComboBox()
        self.voter_class_filter.currentTextChanged.connect(self.load_voters_master)
        filter_layout.addWidget(self.voter_class_filter)
        
        filter_layout.addSpacing(15)

        # 4. PDF EXPORT BUTTON
        pdf_btn = QPushButton("🖨️ Export PDF")
        pdf_btn.setStyleSheet("""
            QPushButton { 
                background: #34495e; 
                color: white; 
                padding: 5px 15px; 
                font-weight: bold; 
                border-radius: 4px;
            }
            QPushButton:hover { background: #2c3e50; }
        """)
        pdf_btn.clicked.connect(lambda: self.export_to_pdf(self.voter_table, "Master Voter List"))
        filter_layout.addWidget(pdf_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # 5. THE TABLE
        self.voter_table = QTableWidget()
        self.voter_table.setColumnCount(6)
        self.voter_table.setHorizontalHeaderLabels(["Reg No", "Name", "Department", "Class", "Biometric", "Action"])
        self.voter_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.voter_table.setAlternatingRowColors(True)
        self.voter_table.verticalHeader().setVisible(False) 
        
        layout.addWidget(self.voter_table)
        self.voter_tab.setLayout(layout)
        
    def setup_enrolled_tab(self):
        layout = QVBoxLayout()
        filter_layout = QHBoxLayout()
        
        # --- SEARCH BAR ---
        filter_layout.addWidget(QLabel("Search:"))
        self.enroll_search_input = QLineEdit()
        self.enroll_search_input.setPlaceholderText("Search Name or Reg No...")
        self.enroll_search_input.setFixedWidth(200)
        self.enroll_search_input.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.enroll_search_input.textChanged.connect(self.load_enrolled_voters)
        filter_layout.addWidget(self.enroll_search_input)
        filter_layout.addSpacing(15) 
        
        # --- FILTERS ---
        filter_layout.addWidget(QLabel("Department:"))
        self.enroll_dept_filter = QComboBox()
        self.enroll_dept_filter.addItems(["All", "Computer Science & Engineering", "Artificial Intelligence & Machine Learning", "Master of Computer Applications (M.C.A)", "Electrical & Electronics Engineering", "Electronics and Communication Engineering"])
        self.enroll_dept_filter.currentTextChanged.connect(self.load_enrolled_voters)
        filter_layout.addWidget(self.enroll_dept_filter)

        filter_layout.addWidget(QLabel("Class:"))
        self.enroll_class_filter = QComboBox()
        self.enroll_class_filter.currentTextChanged.connect(self.load_enrolled_voters)
        filter_layout.addWidget(self.enroll_class_filter)

        # --- ADDED: EXPORT PDF BUTTON ---
        self.btn_export_enrolled = QPushButton("🖨️ Export PDF")
        self.btn_export_enrolled.setStyleSheet("""
            QPushButton { background: #34495e; color: white; padding: 5px 15px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background: #2c3e50; }
        """)
        self.btn_export_enrolled.clicked.connect(lambda: self.export_to_pdf(self.enrolled_table, "Enrolled Voters List"))
        filter_layout.addWidget(self.btn_export_enrolled)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.enrolled_table = QTableWidget()
        self.enrolled_table.setColumnCount(4)
        self.enrolled_table.setHorizontalHeaderLabels(["Reg No", "Name", "Dept/Class", "Action"])
        self.enrolled_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.enrolled_table)
        self.enrolled_tab_widget.setLayout(layout)

    def setup_voted_tab(self):
        """Logic for the updated Voted People List Tab with Search, Dept Filter, and PDF Export"""
        layout = QVBoxLayout()
        filter_layout = QHBoxLayout()
        
        # --- SEARCH BAR ---
        filter_layout.addWidget(QLabel("Search:"))
        self.voted_search_input = QLineEdit()
        self.voted_search_input.setPlaceholderText("Search Name or Reg No...")
        self.voted_search_input.setFixedWidth(200)
        self.voted_search_input.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        self.voted_search_input.textChanged.connect(self.load_voted_list)
        filter_layout.addWidget(self.voted_search_input)
        
        filter_layout.addSpacing(15) 

        # --- DEPARTMENT FILTER ---
        filter_layout.addWidget(QLabel("Department:"))
        self.voted_dept_filter = QComboBox()
        self.voted_dept_filter.addItems([
            "All", "Computer Science & Engineering", "Artificial Intelligence & Machine Learning", 
            "Master of Computer Applications (M.C.A)", "Electrical & Electronics Engineering", 
            "Electronics and Communication Engineering"
        ])
        self.voted_dept_filter.currentTextChanged.connect(self.load_voted_list)
        filter_layout.addWidget(self.voted_dept_filter)

        # --- CLASS FILTER ---
        filter_layout.addWidget(QLabel("Class:"))
        self.voted_class_filter = QComboBox()
        self.voted_class_filter.currentTextChanged.connect(self.load_voted_list)
        filter_layout.addWidget(self.voted_class_filter)
        
        # --- ADDED: EXPORT PDF BUTTON ---
        self.btn_export_voted = QPushButton("🖨️ Export PDF")
        self.btn_export_voted.setStyleSheet("""
            QPushButton { background: #27ae60; color: white; padding: 5px 15px; font-weight: bold; border-radius: 4px; }
            QPushButton:hover { background: #219150; }
        """)
        self.btn_export_voted.clicked.connect(lambda: self.export_to_pdf(self.voted_table, "Final Voted List"))
        filter_layout.addWidget(self.btn_export_voted)

        # --- REFRESH BUTTON ---
        refresh_btn = QPushButton("Refresh List")
        refresh_btn.clicked.connect(self.load_voted_list)
        filter_layout.addWidget(refresh_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        self.voted_table = QTableWidget()
        self.voted_table.setColumnCount(4)
        self.voted_table.setHorizontalHeaderLabels(["Reg No", "Name", "Department", "Class"])
        self.voted_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.voted_table)
        
        self.voted_tab_widget.setLayout(layout)

    def setup_candidate_tab(self):
        main_cand_layout = QHBoxLayout()
        form_frame = QFrame()
        form_frame.setFixedWidth(260)
        form_frame.setStyleSheet("border: 1px solid #bdc3c7; background: #f9f9f9;")
        form_inner = QVBoxLayout(form_frame)
        
        self.cand_name = QLineEdit()
        self.cand_name.setPlaceholderText("Candidate Name")
        form_inner.addWidget(self.cand_name)

        btn_browse = QPushButton("Upload Logo")
        btn_browse.clicked.connect(self.browse_logo)
        form_inner.addWidget(btn_browse)

        self.logo_preview = QLabel("No Logo")
        self.logo_preview.setFixedSize(100, 100)
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setStyleSheet("border: 1px solid #ccc; background: white;")
        form_inner.addWidget(self.logo_preview)

        btn_save = QPushButton("Save Candidate")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold;")
        btn_save.clicked.connect(self.save_candidate)
        form_inner.addWidget(btn_save)
        form_inner.addStretch()

        results_layout = QVBoxLayout()
        self.cand_table = QTableWidget()
        self.cand_table.setColumnCount(4)
        self.cand_table.setHorizontalHeaderLabels(["ID", "Name", "Votes", "Action"])
        self.cand_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.cand_table)
        
        # --- ADDED: EXPORT BALLOT BUTTON (No Vote Counts) ---
        self.btn_export_ballot = QPushButton("📜 Export Candidate Ballot PDF")
        self.btn_export_ballot.setStyleSheet("""
            QPushButton { 
                background-color: #34495e; color: white; padding: 12px; 
                font-weight: bold; border-radius: 6px; 
            }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        self.btn_export_ballot.clicked.connect(self.export_ballot_only)
        results_layout.addWidget(self.btn_export_ballot)
        
        main_cand_layout.addWidget(form_frame)
        main_cand_layout.addLayout(results_layout) 
        self.cand_tab.setLayout(main_cand_layout)

    def load_voters_master(self):
        dept_filter = self.voter_dept_filter.currentText()
        class_filter = self.voter_class_filter.currentText()
        # --- ADDED: Get the search text ---
        search_text = self.voter_search_input.text().strip()

        query = "SELECT reg_no, name, department, class, fingerprint_template FROM voters WHERE 1=1"
        params = []
        
        if dept_filter != "All":
            query += " AND department = ?"
            params.append(dept_filter)
        if class_filter != "All":
            query += " AND class = ?"
            params.append(class_filter)
            
        # --- ADDED: SQL LIKE filter for Name or Reg No ---
        if search_text:
            query += " AND (reg_no LIKE ? OR name LIKE ?)"
            search_param = f"%{search_text}%"
            params.append(search_param)
            params.append(search_param)

        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        voters = cursor.fetchall()

        self.voter_table.setRowCount(len(voters))
        for i, (reg, name, dept, v_class, template) in enumerate(voters):
            self.voter_table.setItem(i, 0, QTableWidgetItem(reg))
            self.voter_table.setItem(i, 1, QTableWidgetItem(name))
            self.voter_table.setItem(i, 2, QTableWidgetItem(dept))
            self.voter_table.setItem(i, 3, QTableWidgetItem(v_class))
            
            status_text = "Ready 🧬" if template else "Missing ❌"
            status_item = QTableWidgetItem(status_text)
            status_item.setTextAlignment(Qt.AlignCenter)
            self.voter_table.setItem(i, 4, status_item)

            cursor.execute("SELECT COUNT(*) FROM election_voter_list WHERE reg_no = ?", (reg,))
            enrolled = cursor.fetchone()[0]

            action_widget = QWidget()
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(2, 2, 2, 2)

            if enrolled == 0:
                add_btn = QPushButton("Enroll")
                add_btn.setStyleSheet("background: #3498db; color: white; border-radius: 3px; padding: 2px 5px;")
                add_btn.clicked.connect(lambda ch, r=reg: self.add_to_election(r))
                action_layout.addWidget(add_btn)
            else:
                label = QLabel("Enrolled ✅")
                label.setStyleSheet("color: #27ae60; font-weight: bold;")
                action_layout.addWidget(label)

            # --- ADD THE EDIT BUTTON HERE ---
            edit_btn = QPushButton("Edit")
            edit_btn.setStyleSheet("background: #2ecc71; color: white; border-radius: 3px; padding: 2px 5px;")
            # This calls the popup dialog we created earlier
            edit_btn.clicked.connect(lambda ch, r=reg, n=name, d=dept, c=v_class: self.open_edit_voter_dialog(r, n, d, c))
            action_layout.addWidget(edit_btn)

            # --- YOUR EXISTING DELETE BUTTON ---
            del_btn = QPushButton("Delete")
            del_btn.setStyleSheet("background: #e74c3c; color: white; border-radius: 3px; padding: 2px 5px;")
            del_btn.clicked.connect(lambda ch, r=reg: self.delete_voter_from_db(r))
            action_layout.addWidget(del_btn)
            
            self.voter_table.setCellWidget(i, 5, action_widget)
            
        conn.close()

    def load_enrolled_voters(self):
        # 1. Get current filter values
        dept_filter = self.enroll_dept_filter.currentText()
        class_filter = self.enroll_class_filter.currentText()
        search_text = self.enroll_search_input.text().strip() 

        # 2. Base Query
        query = "SELECT e.reg_no, v.name, v.department, v.class FROM election_voter_list e JOIN voters v ON e.reg_no = v.reg_no WHERE 1=1"
        params = []
        
        # 3. Apply Search Filter (Name or Reg No)
        if search_text:
            query += " AND (e.reg_no LIKE ? OR v.name LIKE ?)"
            search_param = f"%{search_text}%"
            params.append(search_param)
            params.append(search_param)

        # 4. Apply Department Filter
        if dept_filter != "All":
            query += " AND v.department = ?"
            params.append(dept_filter)

        # 5. Apply Class Filter
        if class_filter != "All":
            query += " AND v.class = ?"
            params.append(class_filter)

        # 6. Execute Database call
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        enrolled = cursor.fetchall()
        conn.close()
        
        # 7. Update the Table UI
        self.enrolled_table.setRowCount(len(enrolled))
        for i, (reg, name, dept, v_class) in enumerate(enrolled):
            self.enrolled_table.setItem(i, 0, QTableWidgetItem(reg))
            self.enrolled_table.setItem(i, 1, QTableWidgetItem(name))
            self.enrolled_table.setItem(i, 2, QTableWidgetItem(f"{dept} ({v_class})"))
            
            btn = QPushButton("Remove")
            btn.setStyleSheet("background: #f39c12; color: white; padding: 4px;")
            # Important: Use the specific 'reg' for each row's button
            btn.clicked.connect(lambda ch, r=reg: self.remove_from_election(r))
            self.enrolled_table.setCellWidget(i, 3, btn)

    def load_voted_list(self):
        """Fills the Voted People table based on has_voted = 1 and all filters"""
        # 1. Get current values from all inputs
        dept_filter = self.voted_dept_filter.currentText()
        class_filter = self.voted_class_filter.currentText()
        search_text = self.voted_search_input.text().strip() 
        
        # 2. Base query (Selecting only those who have already voted)
        query = "SELECT reg_no, name, department, class FROM voters WHERE has_voted = 1"
        params = []
        
        # 3. Apply Search Filter (Partial match for Name or Reg No)
        if search_text:
            query += " AND (reg_no LIKE ? OR name LIKE ?)"
            search_param = f"%{search_text}%"
            params.append(search_param)
            params.append(search_param)

        # 4. ADDED: Apply Department Filter
        if dept_filter != "All":
            query += " AND department = ?"
            params.append(dept_filter)

        # 5. Apply Class Filter
        if class_filter != "All":
            query += " AND class = ?"
            params.append(class_filter)

        # 6. Database Execution
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        voted_data = cursor.fetchall()
        conn.close()

        # 7. Refresh the Table UI
        self.voted_table.setRowCount(len(voted_data))
        for i, row in enumerate(voted_data):
            for j, val in enumerate(row):
                item = QTableWidgetItem(str(val))
                # Important: Keeps the list read-only to prevent accidental edits
                item.setFlags(Qt.ItemIsEnabled) 
                self.voted_table.setItem(i, j, item)

    def add_to_election(self, reg_no):
        conn = self.db.connect()
        conn.cursor().execute("INSERT OR IGNORE INTO election_voter_list (reg_no) VALUES (?)", (reg_no,))
        conn.commit()
        conn.close()
        self.refresh_all_data()

    def reset_voted_filters(self):
        """Resets all search and dropdowns in the Voted Tab to default"""
        # 1. Clear the text box (this triggers load_voted_list automatically via textChanged)
        self.voted_search_input.clear()
        
        # 2. Reset dropdowns to "All" (Index 0)
        # We block signals so it doesn't refresh the database 3 times in a row
        self.voted_dept_filter.blockSignals(True)
        self.voted_class_filter.blockSignals(True)
        
        self.voted_dept_filter.setCurrentIndex(0)
        self.voted_class_filter.setCurrentIndex(0)
        
        self.voted_dept_filter.blockSignals(False)
        self.voted_class_filter.blockSignals(False)
        
        # 3. Final manual refresh
        self.load_voted_list()    

    def remove_from_election(self, reg_no):
        conn = self.db.connect()
        conn.cursor().execute("DELETE FROM election_voter_list WHERE reg_no = ?", (reg_no,))
        conn.commit()
        conn.close()
        self.refresh_all_data()

    def delete_voter_from_db(self, reg_no):
        if QMessageBox.question(self, 'Confirm', f"Delete {reg_no} from database?") == QMessageBox.Yes:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM election_voter_list WHERE reg_no = ?", (reg_no,))
            cursor.execute("DELETE FROM voters WHERE reg_no = ?", (reg_no,))
            conn.commit()
            conn.close()
            self.refresh_all_data()

    def browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg)")
        if path:
            self.logo_path = path
            self.logo_preview.setPixmap(QPixmap(path).scaled(100, 100, Qt.KeepAspectRatio))

    def save_candidate(self):
        name = self.cand_name.text().strip()
        if name and self.logo_path:
            conn = self.db.connect()
            conn.cursor().execute("INSERT INTO candidates (name, logo_path) VALUES (?, ?)", (name, self.logo_path))
            conn.commit()
            conn.close()
            self.cand_name.clear()
            self.load_candidates()

    def load_candidates(self):
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, vote_count FROM candidates")
        candidates = cursor.fetchall()
        conn.close()
        self.cand_table.setRowCount(len(candidates))
        for i, (c_id, name, votes) in enumerate(candidates):
            self.cand_table.setItem(i, 0, QTableWidgetItem(str(c_id)))
            self.cand_table.setItem(i, 1, QTableWidgetItem(name))
            self.cand_table.setItem(i, 2, QTableWidgetItem(str(votes)))
            btn = QPushButton("Delete")
            btn.setStyleSheet("background: #e74c3c; color: white;")
            btn.clicked.connect(lambda ch, cid=c_id: self.delete_candidate(cid))
            self.cand_table.setCellWidget(i, 3, btn)

    def delete_candidate(self, cand_id):
        conn = self.db.connect()
        conn.cursor().execute("DELETE FROM candidates WHERE id = ?", (cand_id,))
        conn.commit()
        conn.close()
        self.load_candidates()
    
    def setup_system_tab(self):
        """Updated System Controls with ScrollArea to prevent overlapping"""
        
        # 1. Create a Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        # 2. Create a container widget for the content
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 20, 30, 20)
        content_layout.setSpacing(20)

        # --- SECTION 1: ELECTION SCHEDULE ---
        time_card = QFrame()
        time_card.setStyleSheet("background: #ffffff; border: 1px solid #dcdde1; border-radius: 12px;")
        time_layout = QVBoxLayout(time_card)
        time_layout.setContentsMargins(25, 20, 25, 20)
        
        time_header = QLabel("⏰ ELECTION SCHEDULE")
        time_header.setStyleSheet("font-weight: bold; font-size: 16px; color: #34495e; border: none;")
        time_layout.addWidget(time_header)

        time_inputs = QHBoxLayout()
        
        # Start Time
        start_box = QVBoxLayout()
        start_box.addWidget(QLabel("Voting Start Time:"))
        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("hh:mm AP")
        # Use padding instead of high fixed minimum heights
        self.start_time_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 5px;")
        start_box.addWidget(self.start_time_edit)
        time_inputs.addLayout(start_box)

        # End Time
        end_box = QVBoxLayout()
        end_box.addWidget(QLabel("Voting End Time:"))
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("hh:mm AP")
        self.end_time_edit.setStyleSheet("padding: 8px; font-size: 14px; border: 1px solid #ccc; border-radius: 5px;")
        end_box.addWidget(self.end_time_edit)
        time_inputs.addLayout(end_box)

        time_layout.addLayout(time_inputs)

        save_time_btn = QPushButton("Update Voting Hours")
        save_time_btn.setStyleSheet("""
            QPushButton { background: #34495e; color: white; padding: 10px; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background: #2c3e50; }
        """)
        save_time_btn.clicked.connect(self.save_election_times)
        time_layout.addWidget(save_time_btn)
        content_layout.addWidget(time_card)

        # --- SECTION 2: MANUAL MASTER CONTROL ---
        status_card = QFrame()
        status_card.setStyleSheet("background: #fdfdfd; border: 1px solid #dcdde1; border-radius: 12px;")
        status_layout = QVBoxLayout(status_card)
        
        self.status_label = QLabel("Election Status: LOADING...")
        self.status_label.setStyleSheet("font-size: 18px; font-weight: bold; border: none; margin: 5px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        status_layout.addWidget(self.status_label)

        btn_box = QHBoxLayout()
        start_btn = QPushButton("FORCE ACTIVATE")
        start_btn.setFixedHeight(45) # Use fixed height instead of minimum height
        start_btn.setStyleSheet("background: #27ae60; color: white; font-weight: bold; border-radius: 5px;")
        start_btn.clicked.connect(lambda: self.update_election_status("active"))

        stop_btn = QPushButton("FORCE STOP")
        stop_btn.setFixedHeight(45)
        stop_btn.setStyleSheet("background: #e67e22; color: white; font-weight: bold; border-radius: 5px;")
        stop_btn.clicked.connect(lambda: self.update_election_status("stopped"))

        btn_box.addWidget(start_btn)
        btn_box.addWidget(stop_btn)
        status_layout.addLayout(btn_box)
        content_layout.addWidget(status_card)

        # --- SECTION 3: PROMOTION & UNDO ---
        promo_card = QFrame()
        promo_card.setStyleSheet("background: #ffffff; border: 1px solid #3498db; border-radius: 12px;")
        promo_layout = QVBoxLayout(promo_card)
        
        promo_header = QLabel("🎓 ACADEMIC CONTROLS")
        promo_header.setStyleSheet("font-weight: bold; font-size: 16px; color: #2980b9; border: none;")
        promo_layout.addWidget(promo_header)

        btn_group = QHBoxLayout() 
        promo_btn = QPushButton("PROMOTE STUDENTS")
        promo_btn.setFixedHeight(45)
        promo_btn.setStyleSheet("background: #3498db; color: white; font-weight: bold; border-radius: 5px;")
        promo_btn.clicked.connect(self.promote_students)
        
        back_btn = QPushButton("GO BACK (UNDO)")
        back_btn.setFixedHeight(45)
        back_btn.setStyleSheet("background: #95a5a6; color: white; font-weight: bold; border-radius: 5px;")
        back_btn.clicked.connect(self.undo_promotion)
        
        btn_group.addWidget(promo_btn)
        btn_group.addWidget(back_btn)
        promo_layout.addLayout(btn_group)
        content_layout.addWidget(promo_card)

        # --- SECTION 4: ADMIN MANAGEMENT ---
        admin_card = QFrame()
        admin_card.setStyleSheet("background: #ffffff; border: 1px solid #dcdde1; border-radius: 12px;")
        admin_layout = QVBoxLayout(admin_card)

        admin_header = QLabel("👥 ADMIN MANAGEMENT")
        admin_header.setStyleSheet("font-weight: bold; font-size: 16px; color: #2c3e50; border: none;")
        admin_layout.addWidget(admin_header)

        admin_form = QFormLayout()
        admin_form.setVerticalSpacing(10) 
        
        self.new_admin_user = QLineEdit()
        self.new_admin_user.setPlaceholderText("Enter new admin username")
        self.new_admin_user.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 5px;")
        
        self.new_admin_pass = QLineEdit()
        self.new_admin_pass.setPlaceholderText("Enter new admin password")
        self.new_admin_pass.setEchoMode(QLineEdit.Password)
        self.new_admin_pass.setStyleSheet("padding: 8px; border: 1px solid #ccc; border-radius: 5px;")

        admin_form.addRow("Username:", self.new_admin_user)
        admin_form.addRow("Password:", self.new_admin_pass)
        admin_layout.addLayout(admin_form)

        btn_add_admin = QPushButton("Create New Admin Account")
        btn_add_admin.setStyleSheet("""
            QPushButton { background-color: #34495e; color: white; padding: 10px; font-weight: bold; border-radius: 5px; }
            QPushButton:hover { background-color: #2c3e50; }
        """)
        btn_add_admin.clicked.connect(self.create_secondary_admin)
        admin_layout.addWidget(btn_add_admin)
        content_layout.addWidget(admin_card) 

        # Add stretch to keep items at the top
        content_layout.addStretch()

        # 3. Final Step: Put everything into the tab via the scroll area
        scroll.setWidget(content_widget)
        
        tab_layout = QVBoxLayout(self.system_tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)
        
        self.load_system_settings()

    def log_activity(self, message):
        """Logs admin actions to a text file for auditing"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open("admin_activity.log", "a") as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception as e:
            print(f"Logging failed: {e}")

    def load_system_settings(self):
        """Fetches both status and times from the settings table"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Fetch all settings into a dictionary
            cursor.execute("SELECT key, value FROM settings")
            settings = dict(cursor.fetchall())
            conn.close()

            # Update Status Label
            status = settings.get('election_status', 'stopped')
            self.update_status_ui(status)

            # Update Time Pickers (Convert "HH:mm" string to QTime)
            start_str = settings.get('election_start_time', '07:00')
            end_str = settings.get('election_end_time', '18:00')
            
            self.start_time_edit.setTime(QTime.fromString(start_str, "HH:mm"))
            self.end_time_edit.setTime(QTime.fromString(end_str, "HH:mm"))
            
        except Exception as e:
            print(f"Error loading system settings: {e}")

    def save_election_times(self):
        """Saves the QTime values back to the database as strings"""
        start = self.start_time_edit.time().toString("HH:mm")
        end = self.end_time_edit.time().toString("HH:mm")
        
        try:
            conn = self.db.connect()
            conn.execute("UPDATE settings SET value=? WHERE key='election_start_time'", (start,))
            conn.execute("UPDATE settings SET value=? WHERE key='election_end_time'", (end,))
            conn.commit()
            conn.close()
            QMessageBox.information(self, "Success", f"Election hours set from {start} to {end}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save times: {e}")

    def update_status_ui(self, status):
        """Updates the label colors based on status"""
        if status == "active":
            self.status_label.setText("Election Status: ACTIVE 🟢")
            self.status_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #27ae60; border: none;")
        else:
            self.status_label.setText("Election Status: STOPPED 🛑")
            self.status_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #e74c3c; border: none;")

    def update_election_status(self, status):
        """Manual override for the election status switch"""
        try:
            conn = self.db.connect()
            conn.execute("UPDATE settings SET value=? WHERE key='election_status'", (status,))
            conn.commit()
            conn.close()
            self.update_status_ui(status)
            QMessageBox.information(self, "Success", f"System manually {status.upper()}.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Database update failed: {e}")

    def create_secondary_admin(self):
        """Allows the logged-in admin to create another admin account"""
        user = self.new_admin_user.text().strip()
        pw = self.new_admin_pass.text().strip()

        if not user or not pw:
            QMessageBox.warning(self, "Input Error", "Please provide both username and password.")
            return

        confirm = QMessageBox.question(self, "Confirm", f"Create a new admin account for '{user}'?",
                                      QMessageBox.YES | QMessageBox.NO)
        
        if confirm == QMessageBox.YES:
            try:
                conn = self.db.connect()
                cursor = conn.cursor()
                # Inserts the new admin into the 'admins' table
                cursor.execute("INSERT INTO admins (username, password) VALUES (?, ?)", (user, pw))
                conn.commit()
                conn.close()
                
                QMessageBox.information(self, "Success", f"Admin account '{user}' created successfully.")
                self.new_admin_user.clear()
                self.new_admin_pass.clear()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not create account: {e}")
            
    def promote_students(self):
        """Advances students and creates a 'Go Back' point automatically."""
        try:
            # --- FIXED PATHS ---
            original_db = "data/voting_db.db"
            backup_db = "data/voting_db_backup.db"

            # 1. CREATE BACKUP (The 'Go Back' point)
            if os.path.exists(original_db):
                shutil.copyfile(original_db, backup_db)
            else:
                raise FileNotFoundError(f"Could not find {original_db}")

            # 2. RUN PROMOTION
            promo_map = {
                "S1": "S2", "S2": "S3", "S3": "S4", "S4": "S5", 
                "S5": "S6", "S6": "S7", "S7": "S8", "S8": "GRADUATED",
                "MCA S1": "MCA S2", "MCA S2": "MCA S3", "MCA S3": "MCA S4", "MCA S4": "GRADUATED"
            }

            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM election_voter_list")
            cursor.execute("UPDATE voters SET has_voted = 0")
            cursor.execute("SELECT reg_no, class FROM voters WHERE is_active = 1")
            
            for reg, current_class in cursor.fetchall():
                parts = current_class.split(' ')
                # Handles MCA and Engineering class formats correctly
                sem_key = f"MCA {parts[1]}" if "MCA" in current_class and len(parts) > 1 else parts[0]
                section = f" {parts[1]}" if "MCA" not in current_class and len(parts) > 1 else ""
                
                next_sem = promo_map.get(sem_key)
                if next_sem == "GRADUATED":
                    cursor.execute("UPDATE voters SET is_active = 0, class = 'ALUMNI' WHERE reg_no = ?", (reg,))
                elif next_sem:
                    cursor.execute("UPDATE voters SET class = ? WHERE reg_no = ?", (f"{next_sem}{section}", reg))

            conn.commit()
            conn.close()
            self.refresh_all_data()
            QMessageBox.information(self, "Done", "Promoted! Use 'Go Back' if this was a mistake.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Promotion failed: {str(e)}")

    def undo_promotion(self):
        """The 'Go Back' button logic using the correct database path."""
        original_db = "data/voting_db.db"
        backup_db = "data/voting_db_backup.db"

        if not os.path.exists(backup_db):
            QMessageBox.warning(self, "Error", "No backup found to go back to.")
            return
        
        try:
            shutil.copyfile(backup_db, original_db)
            self.refresh_all_data()
            QMessageBox.information(self, "Restored", "System has gone back to the previous state.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Restore failed: {e}")

    def export_ballot_only(self):
        """Generates a PDF for the ballot with Name and Logo only (excludes vote counts)"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Ballot", "Candidate_Ballot.pdf", "PDF Files (*.pdf)")
        if not file_path:
            return

        try:
            from reportlab.platypus import Image
            
            doc = SimpleDocTemplate(file_path, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            # Header for the PDF
            elements.append(Paragraph("<b>OFFICIAL CANDIDATE BALLOT</b>", styles['Title']))
            elements.append(Spacer(1, 20))

            # Fetch fresh data from DB to get Image Paths in ID order
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT name, logo_path FROM candidates ORDER BY id ASC")
            candidates = cursor.fetchall()
            conn.close()

            # Table Data: [Candidate Name | Logo]
            data = [["Candidate Name", "Logo"]]

            for name, logo_path in candidates:
                img = ""
                if logo_path and os.path.exists(logo_path):
                    try:
                        img = Image(logo_path, width=60, height=60)
                    except:
                        img = "[Error Loading Logo]"
                else:
                    img = "[No Logo]"

                data.append([name, img])

            pdf_table = Table(data, colWidths=[300, 150])
            pdf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('TOPPADDING', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
            ]))

            elements.append(pdf_table)
            doc.build(elements)
            QMessageBox.information(self, "Success", "Ballot PDF generated successfully!")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to generate ballot PDF: {e}")

    def open_edit_voter_dialog(self, reg_no, name, dept, v_class):
        """Opens a popup to edit the selected voter's details"""
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edit Voter: {reg_no}")
        dialog.setFixedWidth(400)
        layout = QVBoxLayout(dialog)

        form = QFormLayout()
        
        # Create input fields with existing data
        name_input = QLineEdit(name)
        
        dept_input = QComboBox()
        dept_input.addItems([
            "Computer Science & Engineering", 
            "Artificial Intelligence & Machine Learning", 
            "Master of Computer Applications (M.C.A)", 
            "Electrical & Electronics Engineering", 
            "Electronics and Communication Engineering"
        ])
        dept_input.setCurrentText(dept)

        class_input = QLineEdit(v_class)
        
        form.addRow("Name:", name_input)
        form.addRow("Department:", dept_input)
        form.addRow("Class:", class_input)
        layout.addLayout(form)

        save_btn = QPushButton("Save Changes")
        save_btn.setStyleSheet("background: #27ae60; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        
        def save_and_close():
            new_name = name_input.text().strip()
            new_dept = dept_input.currentText()
            new_class = class_input.text().strip()
            
            if new_name and new_class:
                self.update_voter_in_db(reg_no, new_name, new_dept, new_class)
                dialog.accept()
            else:
                QMessageBox.warning(dialog, "Input Error", "All fields must be filled.")

        save_btn.clicked.connect(save_and_close)
        layout.addWidget(save_btn)
        dialog.exec_()

    def update_voter_in_db(self, reg_no, name, dept, v_class):
        """Updates the database with the new voter information"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE voters 
                SET name = ?, department = ?, class = ? 
                WHERE reg_no = ?
            """, (name, dept, v_class, reg_no))
            conn.commit()
            conn.close()
            
            self.log_activity(f"Admin edited details for Voter {reg_no}")
            self.refresh_all_data() 
            QMessageBox.information(self, "Success", "Voter details updated.")
        except Exception as e:
            QMessageBox.critical(self, "Database Error", f"Update failed: {e}")
