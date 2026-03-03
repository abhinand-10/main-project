import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from database import ElectionDatabase
from scanner_handler import BiometricHandler

class RegistrationWindow(QWidget):
    switch_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.db = ElectionDatabase()
        self.scanner = BiometricHandler()
        self.temp_fingerprint = None 
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Voter Registration System")
        
        # Main layout to handle overall window centering
        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignCenter)

        # Container Frame - Set to Expanding to fit screen variations
        self.container = QFrame()
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.container.setMinimumWidth(400)
        self.container.setMaximumWidth(600) # Prevents the form from becoming too wide on large screens
        self.container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 15px;
            }
        """)
        
        # Internal layout for the container
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        # --- Top Navigation Bar ---
        nav_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(80)
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #ecf0f1; border: 1px solid #bdc3c7;
                border-radius: 5px; padding: 5px; color: #2c3e50;
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
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50; border: none;")
        layout.addWidget(header)

        # Input Fields Styling
        input_style = "padding: 12px; font-size: 14px; border: 1px solid #bdc3c7; border-radius: 8px; background: #fdfdfd; color: #2c3e50;"
        
        self.reg_no = QLineEdit()
        self.reg_no.setPlaceholderText("Register Number (e.g., 101)")
        self.reg_no.setStyleSheet(input_style)
        
        self.name = QLineEdit()
        self.name.setPlaceholderText("Full Name")
        self.name.setStyleSheet(input_style)
        
        self.v_class = QLineEdit()
        self.v_class.setPlaceholderText("Class/Division")
        self.v_class.setStyleSheet(input_style)

        self.dep = QLineEdit()
        self.dep.setPlaceholderText("Department")
        self.dep.setStyleSheet(input_style)

        layout.addWidget(self.reg_no)
        layout.addWidget(self.name)
        layout.addWidget(self.v_class)
        layout.addWidget(self.dep)

        # Fingerprint Section
        self.scan_btn = QPushButton("📷 SELECT FINGERPRINT FILE")
        self.scan_btn.setFixedHeight(50)
        self.scan_btn.setStyleSheet("""
            QPushButton { background-color: #3498db; color: white; font-weight: bold; border-radius: 8px; border: none; }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.scan_btn.clicked.connect(self.handle_scan)
        layout.addWidget(self.scan_btn)

        self.status_label = QLabel("Status: Select file from Mantra folder")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic; border: none;")
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

        # Finalizing layout
        main_layout.addWidget(self.container)
        self.setLayout(main_layout)

    def handle_scan(self):
        # Trigger fingerprint capture from scanner handler
        self.temp_fingerprint = self.scanner.capture_fingerprint()
        if self.temp_fingerprint:
            self.status_label.setText("Fingerprint File Loaded! ✅")
            self.status_label.setStyleSheet("color: #27ae60; font-weight: bold; border: none;")
        else:
            self.status_label.setText("No file selected.")
            self.status_label.setStyleSheet("color: #c0392b; border: none;")

    def handle_registration(self):
        # Collect data from fields
        reg = self.reg_no.text().strip()
        name = self.name.text().strip()
        v_class = self.v_class.text().strip()
        dep = self.dep.text().strip()

        # Validation check
        if not reg or not name or not self.temp_fingerprint:
            QMessageBox.warning(self, "Error", "Please fill all fields and select a fingerprint image!")
            return

        # Attempt to save to database
        success = self.db.add_voter(reg, name, v_class, dep, self.temp_fingerprint)
        if success:
            QMessageBox.information(self, "Success", f"Voter {name} registered successfully!")
            self.clear_fields()
        else:
            QMessageBox.critical(self, "Error", "Registration failed. Reg Number might already exist.")

    def clear_fields(self):
        # Reset form after successful registration
        self.reg_no.clear()
        self.name.clear()
        self.v_class.clear()
        self.dep.clear()
        self.temp_fingerprint = None
        self.status_label.setText("Status: Ready")
        self.status_label.setStyleSheet("color: #7f8c8d; font-style: italic; border: none;")