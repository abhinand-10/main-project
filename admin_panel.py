import sys
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QMessageBox, QFileDialog, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget, QFrame, QSizePolicy)
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, pyqtSignal
from database import ElectionDatabase

class AdminPanel(QWidget):
    switch_back = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.db = ElectionDatabase()
        self.logo_path = ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Admin Management Panel")
        
        # Main layout for the entire window
        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignCenter)

        # Main Container - Changed to Expanding to fit screen size
        self.container = QFrame()
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.container.setMinimumWidth(800) # Minimum width to keep it readable
        self.container.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #dcdde1;
                border-radius: 15px;
            }
        """)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 20, 20, 20)
        
        # --- Top Navigation Bar ---
        top_bar = QHBoxLayout()
        back_btn = QPushButton("← Back")
        back_btn.setFixedWidth(80)
        back_btn.setStyleSheet("padding: 5px; background: #ecf0f1; border-radius: 5px; color: #2c3e50;")
        back_btn.clicked.connect(self.switch_back.emit)
        top_bar.addWidget(back_btn)
        
        header = QLabel("ADMIN CONTROL PANEL")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #2c3e50; border: none;")
        top_bar.addWidget(header)
        top_bar.addStretch() 
        container_layout.addLayout(top_bar)

        # --- Tab Widget ---
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #bdc3c7; }
            QTabBar::tab { padding: 10px 20px; font-weight: bold; }
        """)
        
        # Tab 1: Voter Management
        self.voter_tab = QWidget()
        self.setup_voter_tab()
        self.tabs.addTab(self.voter_tab, "Voter Management")

        # Tab 2: Candidate Management & Live Results
        self.cand_tab = QWidget()
        self.setup_candidate_tab()
        self.tabs.addTab(self.cand_tab, "Candidate & Results")

        container_layout.addWidget(self.tabs)
        
        # Add container to outer layout
        outer_layout.addWidget(self.container)
        self.setLayout(outer_layout)

    def setup_voter_tab(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Master Voter List Section
        layout.addWidget(QLabel("<b>1. Master Voter List</b> (Click 'Add' to enroll in current election)"))
        self.voter_table = QTableWidget()
        self.voter_table.setColumnCount(4)
        self.voter_table.setHorizontalHeaderLabels(["Reg No", "Name", "Class", "Action"])
        self.voter_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.voter_table)

        # Enrolled Voters Section
        layout.addWidget(QLabel("<br><b>2. Enrolled Voters for This Election</b>"))
        self.enrolled_table = QTableWidget()
        self.enrolled_table.setColumnCount(3)
        self.enrolled_table.setHorizontalHeaderLabels(["Reg No", "Name", "Action"])
        self.enrolled_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.enrolled_table)

        btn_refresh = QPushButton("🔄 Refresh Lists")
        btn_refresh.setStyleSheet("padding: 10px; background-color: #34495e; color: white; font-weight: bold; border-radius: 5px;")
        btn_refresh.clicked.connect(self.refresh_all_voter_data)
        layout.addWidget(btn_refresh)

        self.voter_tab.setLayout(layout)
        self.refresh_all_voter_data()

    def setup_candidate_tab(self):
        main_cand_layout = QHBoxLayout()
        main_cand_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left Side: Form to add candidate
        form_layout = QVBoxLayout()
        form_frame = QFrame()
        form_frame.setFixedWidth(280) # Fixed width for form to keep it tidy
        form_frame.setStyleSheet("border: 1px solid #bdc3c7; border-radius: 10px; background: #f9f9f9;")
        
        form_inner = QVBoxLayout(form_frame)
        form_inner.addWidget(QLabel("<b>Add New Candidate</b>"))
        
        self.cand_name = QLineEdit()
        self.cand_name.setPlaceholderText("Candidate Name")
        self.cand_name.setStyleSheet("padding: 8px; border-radius: 5px; border: 1px solid #ccc;")
        form_inner.addWidget(self.cand_name)

        self.btn_browse = QPushButton("Upload Logo")
        self.btn_browse.clicked.connect(self.browse_logo)
        form_inner.addWidget(self.btn_browse)

        self.logo_preview = QLabel("No Logo")
        self.logo_preview.setAlignment(Qt.AlignCenter)
        self.logo_preview.setFixedSize(100, 100)
        self.logo_preview.setStyleSheet("border: 1px solid #ccc; background: white;")
        form_inner.addWidget(self.logo_preview)

        btn_save = QPushButton("Save Candidate")
        btn_save.setStyleSheet("background-color: #27ae60; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_save.clicked.connect(self.save_candidate)
        form_inner.addWidget(btn_save)
        
        form_inner.addStretch()
        form_layout.addWidget(form_frame)
        
        # Right Side: Candidate List and Live Results
        results_layout = QVBoxLayout()
        results_layout.addWidget(QLabel("<b>Candidate List & Live Results</b>"))
        
        self.cand_table = QTableWidget()
        self.cand_table.setColumnCount(4)
        self.cand_table.setHorizontalHeaderLabels(["ID", "Candidate Name", "Votes", "Action"])
        self.cand_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        results_layout.addWidget(self.cand_table)
        
        btn_refresh_res = QPushButton("📊 Update Live Results")
        btn_refresh_res.setStyleSheet("background-color: #2980b9; color: white; padding: 10px; font-weight: bold; border-radius: 5px;")
        btn_refresh_res.clicked.connect(self.load_candidates)
        results_layout.addWidget(btn_refresh_res)

        # Adding layouts with stretch factors: 1 part form, 3 parts table
        main_cand_layout.addLayout(form_layout, 1)
        main_cand_layout.addLayout(results_layout, 3) 
        self.cand_tab.setLayout(main_cand_layout)
        self.load_candidates()

    # --- VOTER LOGIC ---
    def refresh_all_voter_data(self):
        self.load_voters_master()
        self.load_enrolled_voters()

    def load_voters_master(self):
        conn = self.db.connect()
        cursor = conn.cursor()
        query = """
            SELECT v.reg_no, v.name, v.class, 
            (SELECT COUNT(*) FROM election_voter_list e WHERE e.reg_no = v.reg_no) as is_enrolled
            FROM voters v
        """
        cursor.execute(query)
        voters = cursor.fetchall()
        conn.close()

        self.voter_table.setRowCount(len(voters))
        for i, (reg, name, v_class, enrolled) in enumerate(voters):
            self.voter_table.setItem(i, 0, QTableWidgetItem(reg))
            self.voter_table.setItem(i, 1, QTableWidgetItem(name))
            self.voter_table.setItem(i, 2, QTableWidgetItem(v_class))
            
            if enrolled > 0:
                lbl = QLabel("Enrolled ✅")
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("color: green; font-weight: bold; border: none;")
                self.voter_table.setCellWidget(i, 3, lbl)
            else:
                btn = QPushButton("Add")
                btn.clicked.connect(lambda ch, r=reg: self.add_to_election(r))
                self.voter_table.setCellWidget(i, 3, btn)

    def load_enrolled_voters(self):
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT e.reg_no, v.name FROM election_voter_list e JOIN voters v ON e.reg_no = v.reg_no")
        enrolled = cursor.fetchall()
        conn.close()

        self.enrolled_table.setRowCount(len(enrolled))
        for i, (reg, name) in enumerate(enrolled):
            self.enrolled_table.setItem(i, 0, QTableWidgetItem(reg))
            self.enrolled_table.setItem(i, 1, QTableWidgetItem(name))
            
            del_btn = QPushButton("Remove")
            del_btn.setStyleSheet("background-color: #c0392b; color: white; border-radius: 3px;")
            del_btn.clicked.connect(lambda ch, r=reg: self.remove_from_election(r))
            self.enrolled_table.setCellWidget(i, 2, del_btn)

    def add_to_election(self, reg_no):
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO election_voter_list (reg_no) VALUES (?)", (reg_no,))
        conn.commit()
        conn.close()
        self.refresh_all_voter_data()

    def remove_from_election(self, reg_no):
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM election_voter_list WHERE reg_no = ?", (reg_no,))
        conn.commit()
        conn.close()
        self.refresh_all_voter_data()

    # --- CANDIDATE LOGIC ---
    def browse_logo(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Logo", "", "Images (*.png *.jpg *.jpeg)")
        if file_path:
            self.logo_path = file_path
            self.logo_preview.setPixmap(QPixmap(self.logo_path).scaled(100, 100, Qt.KeepAspectRatio))

    def save_candidate(self):
        name = self.cand_name.text().strip()
        if name and self.logo_path:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO candidates (name, logo_path) VALUES (?, ?)", (name, self.logo_path))
            conn.commit()
            conn.close()
            self.cand_name.clear()
            self.logo_preview.setText("No Logo")
            self.load_candidates()
            QMessageBox.information(self, "Success", "Candidate registered successfully!")

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
            
            btn_del = QPushButton("Delete")
            btn_del.setStyleSheet("background-color: #e67e22; color: white; border-radius: 3px;")
            btn_del.clicked.connect(lambda ch, cid=c_id: self.delete_candidate(cid))
            self.cand_table.setCellWidget(i, 3, btn_del)

    def delete_candidate(self, cand_id):
        reply = QMessageBox.question(self, 'Confirm', "Are you sure you want to delete this candidate?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM candidates WHERE id = ?", (cand_id,))
            conn.commit()
            conn.close()
            self.load_candidates()