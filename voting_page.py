import cv2
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QMessageBox, QScrollArea, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from database import ElectionDatabase
from scanner_handler import BiometricHandler

class VotingWindow(QWidget):
    # Signal to return to the home screen
    switch_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.db = ElectionDatabase()
        self.scanner = BiometricHandler()
        self.current_voter_reg = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Biometric Voting Terminal")
        
        # 1. Main Layout (Centers the container on screen)
        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setAlignment(Qt.AlignCenter)

        # 2. Responsive Container (Fits to screen with constraints)
        self.container = QFrame()
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.container.setMinimumWidth(500)
        self.container.setMaximumWidth(800) # Prevents excessive stretching on ultra-wide screens
        self.container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 15px;
            }
        """)
        
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(30, 30, 30, 30)

        # --- Top Navigation ---
        nav = QHBoxLayout()
        self.back_btn = QPushButton("← Back to Home")
        self.back_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 15px; 
                background-color: #ecf0f1; 
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                color: #2c3e50;
            }
            QPushButton:hover { background-color: #dcdde1; }
        """)
        self.back_btn.clicked.connect(self.reset_and_go_back)
        nav.addWidget(self.back_btn)
        nav.addStretch()
        self.main_layout.addLayout(nav)

        # --- Authentication Section ---
        self.auth_frame = QFrame()
        self.auth_frame.setStyleSheet("border: none;") 
        self.auth_layout = QVBoxLayout()
        
        self.title_label = QLabel("VOTER VERIFICATION")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-top: 20px; border: none;")
        self.auth_layout.addWidget(self.title_label)

        self.instruction_label = QLabel("Please scan your fingerprint to proceed")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setStyleSheet("color: #7f8c8d; font-size: 14px; margin-bottom: 20px; border: none;")
        self.auth_layout.addWidget(self.instruction_label)

        self.verify_btn = QPushButton("🔍 SCAN & VERIFY IDENTITY")
        self.verify_btn.setFixedHeight(80)
        self.verify_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; 
                color: white; 
                font-weight: bold; 
                font-size: 16px; 
                border-radius: 10px; 
                border: none;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.verify_btn.clicked.connect(self.authenticate_voter)
        self.auth_layout.addWidget(self.verify_btn)

        self.auth_frame.setLayout(self.auth_layout)
        self.main_layout.addWidget(self.auth_frame)

        # --- Candidate Section (Hidden by default) ---
        self.candidate_area = QScrollArea()
        self.candidate_area.setWidgetResizable(True)
        self.candidate_area.setFixedHeight(450) # Scrollable area height
        self.candidate_area.setStyleSheet("border: none; background-color: transparent;")
        self.candidate_widget = QWidget()
        self.candidate_layout = QVBoxLayout(self.candidate_widget)
        self.candidate_area.setWidget(self.candidate_widget)
        self.candidate_area.hide() 
        self.main_layout.addWidget(self.candidate_area)

        # Final Layout Additions
        self.outer_layout.addWidget(self.container)
        self.setLayout(self.outer_layout)

    def authenticate_voter(self):
        """Verifies voter identity using biometric matching."""
        live_scan_data = self.scanner.capture_fingerprint()
        if not live_scan_data:
            return 

        conn = self.db.connect()
        cursor = conn.cursor()
        
        # Check against voters enrolled in the current election list
        query = """
            SELECT v.reg_no, v.name, v.class, v.department, v.fingerprint_template, v.has_voted 
            FROM voters v
            JOIN election_voter_list e ON v.reg_no = e.reg_no
        """
        cursor.execute(query)
        all_voters = cursor.fetchall()
        conn.close()

        found_voter = None
        for reg, name, v_class, dep, stored_template, has_voted in all_voters:
            if self.scanner.verify_match(stored_template, live_scan_data):
                found_voter = (reg, name, v_class, dep, has_voted)
                break

        if found_voter:
            reg, name, v_class, dep, has_voted = found_voter
            if has_voted:
                QMessageBox.critical(self, "Access Denied", f"Access Denied: {name} has already cast a vote!")
            else:
                self.current_voter_reg = reg
                self.show_candidates(name, dep, reg)
        else:
            QMessageBox.warning(self, "Access Denied", "Identity mismatch or voter is not enrolled for this election.")

    def show_candidates(self, name, dep, reg):
        """Displays the candidate list after successful authentication."""
        self.auth_frame.hide()
        self.candidate_area.show()
        self.title_label.setText(f"Welcome, {name}")
        self.instruction_label.setText(f"ID: {reg} | Dept: {dep}")
        self.title_label.setStyleSheet("font-size: 20px; color: #27ae60; font-weight: bold; border: none;")

        # Clear existing candidates from the layout
        for i in reversed(range(self.candidate_layout.count())): 
            item = self.candidate_layout.itemAt(i).widget()
            if item: item.setParent(None)

        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, logo_path FROM candidates")
        candidates = cursor.fetchall()
        conn.close()

        for c_id, c_name, c_logo in candidates:
            frame = QFrame()
            frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #ddd; 
                    border-radius: 10px; 
                    background: #f9f9f9; 
                    margin-bottom: 5px;
                }
            """)
            row = QHBoxLayout(frame)
            row.setContentsMargins(15, 10, 15, 10)
            
            logo_lbl = QLabel()
            pix = QPixmap(c_logo).scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            logo_lbl.setPixmap(pix)
            logo_lbl.setStyleSheet("border: none;")
            row.addWidget(logo_lbl)

            name_lbl = QLabel(c_name)
            name_lbl.setStyleSheet("font-size: 16px; font-weight: bold; border: none; color: #2d3436; margin-left: 10px;")
            row.addWidget(name_lbl)

            row.addStretch()

            v_btn = QPushButton("VOTE")
            v_btn.setFixedSize(110, 40)
            v_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2ecc71; 
                    color: white; 
                    font-weight: bold; 
                    border-radius: 5px; 
                    border: none;
                }
                QPushButton:hover { background-color: #27ae60; }
            """)
            v_btn.clicked.connect(lambda ch, id=c_id: self.cast_vote(id))
            row.addWidget(v_btn)

            self.candidate_layout.addWidget(frame)

    def cast_vote(self, candidate_id):
        """Finalizes the vote after user confirmation."""
        reply = QMessageBox.question(self, 'Confirm Vote', "Are you sure you want to cast your vote for this candidate?", 
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.db.cast_vote(self.current_voter_reg, candidate_id):
                QMessageBox.information(self, "Success", "Your vote has been recorded successfully.")
                self.reset_and_go_back()
            else:
                QMessageBox.critical(self, "Error", "Failed to record vote. Please try again.")

    def reset_and_go_back(self):
        """Resets the UI state and returns to the home screen."""
        self.current_voter_reg = None
        self.candidate_area.hide()
        self.auth_frame.show()
        self.title_label.setText("VOTER VERIFICATION")
        self.instruction_label.setText("Please scan your fingerprint to proceed")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-top: 20px; border: none;")
        self.switch_back.emit()