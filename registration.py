import sys
import os
import re
import numpy as np

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QPushButton, QMessageBox, QFrame,
                             QSizePolicy, QComboBox)
from PyQt5.QtCore import Qt, pyqtSignal
from database import ElectionDatabase

class RegistrationWindow(QWidget):
    switch_back = pyqtSignal()

    def __init__(self, scanner): 
        super().__init__()
        self.db = ElectionDatabase()
        self.scanner = scanner 
        self.temp_fingerprint = None 
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Secure Voter Registration")
        
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Container Frame
        self.container = QFrame()
        self.container.setMinimumWidth(450)
        self.container.setMaximumWidth(600)
        self.container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 15px;
            }
            QLabel { border: none; }
        """)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # --- Top Navigation ---
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(80)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1; border: 1px solid #bdc3c7;
                border-radius: 5px; padding: 5px; color: #2c3e50;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #bdc3c7; }
        """)
        self.back_btn.clicked.connect(self.switch_back.emit)
        nav_layout.addWidget(self.back_btn)
        nav_layout.addStretch()
        layout.addLayout(nav_layout)

        # Header
        header = QLabel("VOTER REGISTRATION")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(header)

        # Input Styles
        input_style = "padding: 12px; font-size: 14px; border: 1px solid #bdc3c7; border-radius: 8px; background: #fdfdfd; color: #2c3e50;"
        combo_style = """
            QComboBox { padding: 10px; font-size: 14px; border: 1px solid #bdc3c7; border-radius: 8px; background: #fdfdfd; color: #2c3e50; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { border: 1px solid #bdc3c7; selection-background-color: #3498db; }
        """

        # 1. Register Number
        self.reg_no = QLineEdit()
        self.reg_no.setPlaceholderText("Register Number (e.g., chn24mca2001)")
        self.reg_no.setStyleSheet(input_style)
        layout.addWidget(self.reg_no)

        # 2. Full Name
        self.name = QLineEdit()
        self.name.setPlaceholderText("Full Name")
        self.name.setStyleSheet(input_style)
        layout.addWidget(self.name)

        # 3. Batch Dropdown
        self.batch_type = QComboBox()
        self.batch_type.addItems(["-- Select Batch Type --", "Even", "Odd"])
        self.batch_type.setStyleSheet(combo_style)
        self.batch_type.currentIndexChanged.connect(self.update_class_options)
        layout.addWidget(QLabel("Select Batch Type:"))
        layout.addWidget(self.batch_type)

        # 4. Class Dropdown
        self.v_class = QComboBox()
        self.v_class.addItem("-- Select Class --")
        self.v_class.setStyleSheet(combo_style)
        layout.addWidget(QLabel("Select Class/Division:"))
        layout.addWidget(self.v_class)

        # 5. Department Dropdown
        self.dep = QComboBox()
        self.dep.addItems([
            "-- Select Department --", 
            "Computer Science & Engineering", 
            "Artificial Intelligence & Machine Learning", 
            "Master of Computer Applications (M.C.A)", 
            "Electrical & Electronics Engineering", 
            "Electronics and Communication Engineering"
        ])
        self.dep.setStyleSheet(combo_style)
        layout.addWidget(QLabel("Select Department:"))
        layout.addWidget(self.dep)

        # Fingerprint Section
        self.scan_btn = QPushButton(" SCAN FINGERPRINT ")
        self.scan_btn.setFixedHeight(50)
        self.scan_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; font-weight: bold; border-radius: 8px; border: none; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.scan_btn.clicked.connect(self.handle_scan)
        layout.addWidget(self.scan_btn)

        self.status_label = QLabel("Status: Scan in Mantra App First")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        layout.addWidget(self.status_label)

        layout.addSpacing(10)

        # Submit Button
        self.submit_btn = QPushButton("REGISTER VOTER")
        self.submit_btn.setFixedHeight(55)
        self.submit_btn.setStyleSheet("""
            QPushButton { background-color: #27ae60; color: white; font-size: 16px; border-radius: 8px; font-weight: bold; border: none; }
            QPushButton:hover { background-color: #219150; }
        """)
        self.submit_btn.clicked.connect(self.handle_registration)
        layout.addWidget(self.submit_btn)

        main_layout.addWidget(self.container)
        self.setLayout(main_layout)

    def update_class_options(self, index):
        self.v_class.clear()
        batch = self.batch_type.currentText()
        
        if batch == "Even":
            self.v_class.addItems(["S2 A", "S2 B", "S2 C", "S2 D", "S2 E", "S4 A", "S4 B", "S4 C", "S4 D", "S4 E", "S6 A", "S6 B", "S6 C", "S6 D", "S6 E", "S8 A", "S8 B", "S8 C", "S8 D", "S8 E", "MCA S2", "MCA S4"])
        elif batch == "Odd":
            self.v_class.addItems(["S1 A", "S1 B", "S1 C", "S1 D", "S1 E", "S3 A", "S3 B", "S3 C", "S3 D", "S3 E", "S5 A", "S5 B", "S5 C", "S5 D", "S5 E", "S7 A", "S7 B", "S7 C", "S7 D", "S7 E", "MCA S1", "MCA S3"])
        else:
            self.v_class.addItem("-- Select Class --")

    def handle_scan(self):
        if not self.reg_no.text().strip():
            QMessageBox.warning(self, "Input Required", "Enter Register Number before scanning.")
            return

        self.status_label.setText("Processing fingerprint...")
        self.status_label.setStyleSheet("color: #f39c12; font-style: italic;")
        self.repaint() 

        # capture_fingerprint returns the descriptors (template)
        self.temp_fingerprint = self.scanner.capture_fingerprint()
        
        if self.temp_fingerprint is not None:
            self.status_label.setText("Fingerprint Captured Successfully! ✅")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.status_label.setText("Error: Scan Failed ❌")
            self.status_label.setStyleSheet("color: #c0392b; font-weight: bold;")
            QMessageBox.critical(self, "Scanner Error", "Fingerprint capture failed!")

    def handle_registration(self):
        reg = self.reg_no.text().strip().lower()
        name = self.name.text().strip()
        batch = self.batch_type.currentText()
        v_class = self.v_class.currentText()
        dep = self.dep.currentText() 

        # 1. Validation for Empty Fields
        if not all([reg, name]) or "Select" in batch or "Select" in v_class or "Select" in dep:
            QMessageBox.warning(self, "Validation Error", "All fields must be filled correctly.")
            return

        # 2. Register Number Range Validation
        if not re.match(r"^chn2[1-6]", reg):
            QMessageBox.warning(self, "Invalid Range", "Register Number must start between 'chn21' and 'chn26'.")
            return

        # 3. Real Name Validation
        if not re.match(r"^[A-Za-z\s]+$", name):
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid name (alphabets only).")
            return

        # 4. Fingerprint Presence Check
        if self.temp_fingerprint is None:
            QMessageBox.warning(self, "Biometric Error", "Please capture a fingerprint first.")
            return

        # --- 🔥 NEW: Biometric Duplicate Prevention ---
        # Check if this finger already exists in the database under ANY register number
        is_duplicate, voter_info = self.db.check_fingerprint_exists(self.temp_fingerprint, self.scanner)
        
        if is_duplicate:
            QMessageBox.critical(self, "Security Denied", 
                                f"Duplicate Fingerprint Detected!\n\n"
                                f"This finger is already registered to:\n{voter_info}")
            return

        # 5. Database Save (Store template as BLOB)
        # Convert numpy descriptors to bytes for SQLite
        import numpy as np
        template_bytes = self.temp_fingerprint.astype(np.float32).tobytes()
        
        success = self.db.add_voter(reg, name, v_class, dep, template_bytes)
        
        if success:
            QMessageBox.information(self, "Success", f"Voter {name} registered successfully!")
            self.clear_fields()
        else:
            QMessageBox.critical(self, "Registration Failed", "Register Number already exists.")

    def clear_fields(self):
        self.reg_no.clear()
        self.name.clear()
        self.batch_type.setCurrentIndex(0) 
        self.v_class.clear()
        self.v_class.addItem("-- Select Class --")
        self.dep.setCurrentIndex(0) 
        self.temp_fingerprint = None
        self.status_label.setText("Status: Ready for next voter")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
