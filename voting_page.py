import os
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QMessageBox, QScrollArea, QFrame, 
                             QSizePolicy, QInputDialog, QLineEdit)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer  # Added QTimer for the delay
from PyQt5.QtGui import QPixmap
from database import ElectionDatabase

class VotingWindow(QWidget):
    switch_back = pyqtSignal()

    def __init__(self, scanner):
        super().__init__()
        self.db = ElectionDatabase()
        self.scanner = scanner 
        self.current_voter_reg = None
        self.admin_pin = "1234"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Biometric Voting Terminal")
        self.setStyleSheet("background-color: #2c3e50;") 

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setAlignment(Qt.AlignCenter)

        # --- Main Container ---
        self.container = QFrame()
        self.container.setFixedWidth(850) 
        self.container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 2px solid #2980b9;
                border-radius: 15px;
            }
            QLabel { background: transparent; border: none; }
        """)
        
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(30, 30, 30, 30)

        # --- Top Navigation ---
        nav = QHBoxLayout()
        self.exit_label = QLabel("VOTING TERMINAL")
        self.exit_label.setStyleSheet("color: #7f8c8d; font-weight: bold; font-size: 11px;")
        nav.addWidget(self.exit_label)
        nav.addStretch()
        
        self.back_btn = QPushButton("Exit")
        self.back_btn.setFixedWidth(70)
        self.back_btn.setStyleSheet("background: #f1f2f6; border-radius: 4px; font-size: 10px; color: #666;")
        self.back_btn.clicked.connect(self.exit_to_home_with_pin) 
        nav.addWidget(self.back_btn)
        self.main_layout.addLayout(nav)

        self.title_label = QLabel("Voter Verification")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50; margin-bottom: 5px;")
        self.main_layout.addWidget(self.title_label)

        # --- View 1: Authentication ---
        self.auth_frame = QFrame()
        self.auth_frame.setStyleSheet("border: none; background: transparent;") 
        self.auth_layout = QVBoxLayout(self.auth_frame)
        
        self.instruction_label = QLabel("Place finger on scanner to verify identity")
        self.instruction_label.setAlignment(Qt.AlignCenter)
        self.instruction_label.setStyleSheet("color: #95a5a6; font-size: 14px; margin-bottom: 15px;")
        self.auth_layout.addWidget(self.instruction_label)

        self.verify_btn = QPushButton("VERIFY IDENTITY")
        self.verify_btn.setFixedHeight(80)
        self.verify_btn.setStyleSheet("""
            QPushButton { 
                background-color: #3498db; color: white; font-weight: bold; 
                font-size: 18px; border-radius: 10px; border: none;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        self.verify_btn.clicked.connect(self.authenticate_voter)
        self.auth_layout.addWidget(self.verify_btn)
        self.main_layout.addWidget(self.auth_frame)

        # --- View 2: Voting ---
        self.voting_view = QWidget()
        self.voting_view.setStyleSheet("background: transparent;")
        self.voting_layout = QVBoxLayout(self.voting_view)
        
        self.voter_header = QFrame()
        self.voter_header.setStyleSheet("""
            QFrame { background-color: #ecf0f1; border-bottom: 3px solid #3498db; border-radius: 8px; margin-bottom: 10px; }
        """)
        self.header_layout = QHBoxLayout(self.voter_header)
        self.header_layout.setContentsMargins(15, 15, 15, 15)
        
        self.voter_info_label = QLabel("Voter: Unknown")
        self.voter_info_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50; border: none;")
        self.header_layout.addWidget(self.voter_info_label, alignment=Qt.AlignCenter)
        self.voting_layout.addWidget(self.voter_header)

        self.candidate_area = QScrollArea()
        self.candidate_area.setWidgetResizable(True)
        self.candidate_area.setFixedHeight(350)
        self.candidate_area.setStyleSheet("border: 1px solid #ddd; border-radius: 10px; background: white;")
        
        self.candidate_list_widget = QWidget()
        self.candidate_list_layout = QVBoxLayout(self.candidate_list_widget)
        self.candidate_list_layout.setAlignment(Qt.AlignTop)
        self.candidate_area.setWidget(self.candidate_list_widget)
        self.voting_layout.addWidget(self.candidate_area)
        
        self.voting_view.hide()
        self.main_layout.addWidget(self.voting_view)

        self.outer_layout.addWidget(self.container)
        self.setLayout(self.outer_layout)

    def verify_admin_pin(self, title):
        pin, ok = QInputDialog.getText(self, "Security", title, QLineEdit.Password)
        if ok and pin == self.admin_pin:
            return True
        elif ok:
            QMessageBox.warning(self, "Denied", "Incorrect PIN!")
        return False

    def exit_to_home_with_pin(self):
        if self.verify_admin_pin("Enter Admin PIN:"):
            self.refresh_for_next_voter()
            self.switch_back.emit()

    def authenticate_voter(self):
        is_live, message = self.db.is_election_time_valid()
        if not is_live:
            QMessageBox.warning(self, "System Closed", message)
            return

        self.verify_btn.setText("Capturing Template...")
        self.verify_btn.setEnabled(False)
        self.repaint() 

        live_template = self.scanner.capture_fingerprint()
        self.verify_btn.setText("VERIFY IDENTITY")
        self.verify_btn.setEnabled(True)

        if live_template is None:
            QMessageBox.warning(self, "Error", "No fingerprint detected or poor scan quality.")
            return 

        all_voters = self.db.get_all_voters_with_biometrics()
        found_voter = None

        for voter in all_voters:
            reg, name, v_class, dep, stored_blob, has_voted = voter
            if stored_blob is None:
                continue
            if isinstance(stored_blob, memoryview):
                stored_blob = stored_blob.tobytes()

            try:
                if self.scanner.verify_match(stored_blob, live_template):
                    found_voter = voter
                    break
            except Exception as e:
                print(f"Matching Error for {reg}: {e}")

        if found_voter:
            reg, name, v_class, dep, blob, has_voted = found_voter
            if has_voted:
                QMessageBox.critical(self, "Access Denied", f"Fraud Alert: {name} has already cast a vote!")
                self.refresh_for_next_voter()
            else:
                self.current_voter_reg = reg
                self.voter_info_label.setText(f"Voter: {name.upper()} | ID: {reg}")
                self.show_candidates()
        else:
            QMessageBox.warning(self, "Authentication Failed", 
                                "Fingerprint not recognized or you are not registered.")

    def show_candidates(self):
        for i in reversed(range(self.candidate_list_layout.count())): 
            item = self.candidate_list_layout.itemAt(i)
            if item.widget():
                item.widget().setParent(None)

        candidates = self.db.get_candidates()
        if not candidates:
            QMessageBox.information(self, "Notice", "No candidates registered.")
            self.refresh_for_next_voter()
            return

        self.auth_frame.hide()
        self.voting_view.show()
        self.title_label.setText("Ballot Paper")

        for c_id, c_name, c_logo in candidates:
            frame = QFrame()
            frame.setStyleSheet("QFrame { border: 1px solid #eee; background: #fff; border-radius: 10px; margin-bottom: 5px; }")
            row = QHBoxLayout(frame)
            
            logo = QLabel()
            if c_logo and os.path.exists(c_logo):
                logo.setPixmap(QPixmap(c_logo).scaled(50, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                logo.setText("📷")
            row.addWidget(logo)

            name = QLabel(c_name)
            name.setStyleSheet("font-size: 16px; font-weight: bold; color: #2c3e50;")
            row.addWidget(name)
            row.addStretch()

            v_btn = QPushButton("Vote")
            v_btn.setFixedSize(100, 40)
            v_btn.setStyleSheet("background: #27ae60; color: white; border-radius: 5px; font-weight: bold;")
            # Pass the button itself to the cast_vote function
            v_btn.clicked.connect(lambda ch, cid=c_id, btn=v_btn: self.cast_vote(cid, btn))
            row.addWidget(v_btn)
            self.candidate_list_layout.addWidget(frame)

        # ADD NOTA BUTTON
        nota_frame = QFrame()
        nota_frame.setStyleSheet("QFrame { border: 2px solid #e74c3c; background: #fff5f5; border-radius: 10px; margin-top: 10px; }")
        nota_row = QHBoxLayout(nota_frame)
        
        nota_icon = QLabel("🚫")
        nota_icon.setStyleSheet("font-size: 20px; background: transparent;")
        nota_row.addWidget(nota_icon)

        nota_name = QLabel("None of the Above (NOTA)")
        nota_name.setStyleSheet("font-size: 16px; font-weight: bold; color: #c0392b; background: transparent;")
        nota_row.addWidget(nota_name)
        nota_row.addStretch()

        nota_btn = QPushButton("NOTA")
        nota_btn.setFixedSize(100, 40)
        nota_btn.setStyleSheet("background: #c0392b; color: white; border-radius: 5px; font-weight: bold;")
        # Pass the button itself to the cast_vote function
        nota_btn.clicked.connect(lambda ch, btn=nota_btn: self.cast_vote(0, btn)) 
        
        nota_row.addWidget(nota_btn)
        self.candidate_list_layout.addWidget(nota_frame)

    def cast_vote(self, candidate_id, button_widget):
        """Processes vote instantly with visual feedback and automatic refresh"""
        is_live, message = self.db.is_election_time_valid()
        if not is_live:
            QMessageBox.critical(self, "Election Ended", "The election period has just ended.")
            self.refresh_for_next_voter()
            return

        # Disable candidate area immediately to prevent multiple clicks
        self.candidate_area.setEnabled(False)
        
        if self.db.cast_vote(self.current_voter_reg, candidate_id):
            # Change button to Red and show "VOTED"
            button_widget.setText("VOTED ✓")
            button_widget.setStyleSheet("background: #e74c3c; color: white; border-radius: 5px; font-weight: bold;")
            
            # Start 3-second timer then refresh
            QTimer.singleShot(3000, self.refresh_for_next_voter)
        else:
            QMessageBox.critical(self, "Error", "Failed to record vote. Please contact admin.")
            self.candidate_area.setEnabled(True)

    def refresh_for_next_voter(self):
        self.current_voter_reg = None
        self.candidate_area.setEnabled(True) # Re-enable for the next voter
        self.voting_view.hide()
        self.auth_frame.show()
        self.title_label.setText("Voter Verification")
        self.voter_info_label.setText("Voter: Unknown")
