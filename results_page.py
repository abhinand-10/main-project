import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QTableWidget, QTableWidgetItem, 
                             QHeaderView, QFileDialog, QMessageBox)
from PyQt5.QtGui import QPixmap 
from PyQt5.QtCore import Qt, pyqtSignal
from database import ElectionDatabase
class ResultsPage(QWidget):
    switch_back = pyqtSignal()  # Signal to go back to the Main Menu

    def __init__(self):
        super().__init__()
        self.db = ElectionDatabase()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Election Results Viewer")
        self.setMinimumSize(900, 600)
        self.setStyleSheet("background-color: #f5f6fa;")

        layout = QVBoxLayout(self)

        # --- HEADER SECTION ---
        header_layout = QHBoxLayout()
        
        back_btn = QPushButton("← Main Menu")
        back_btn.setFixedWidth(120)
        back_btn.setStyleSheet("padding: 8px; background: #34495e; color: white; border-radius: 5px;")
        back_btn.clicked.connect(self.switch_back.emit)
        header_layout.addWidget(back_btn)

        title = QLabel("LIVE ELECTION RESULTS")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        header_layout.addWidget(title)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFixedWidth(100)
        refresh_btn.setStyleSheet("padding: 8px; background: #27ae60; color: white; border-radius: 5px;")
        refresh_btn.clicked.connect(self.load_results)
        header_layout.addWidget(refresh_btn)
        
        layout.addLayout(header_layout)

        # --- RESULTS TABLE ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(3)
        self.results_table.setHorizontalHeaderLabels(["Candidate Name", "Logo", "Total Votes"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setStyleSheet("""
            QTableWidget { background-color: white; border-radius: 10px; gridline-color: #dcdde1; }
            QHeaderView::section { background-color: #2c3e50; color: white; padding: 5px; font-weight: bold; }
        """)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.results_table)

        # --- FOOTER / EXPORT ---
        export_btn = QPushButton("🖨️ Export Official Result PDF")
        export_btn.setStyleSheet("""
            QPushButton { background: #2980b9; color: white; padding: 15px; font-size: 16px; font-weight: bold; border-radius: 8px; }
            QPushButton:hover { background: #2471a3; }
        """)
        export_btn.clicked.connect(self.export_to_pdf)
        layout.addWidget(export_btn)

        self.load_results()

    def load_results(self):
        """Fetches data: Highest votes first, but forces 'NOTA' to the bottom"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # The CASE statement assigns 1 to 'NOTA' and 0 to everyone else.
            # SQL sorts 0 (candidates) before 1 (NOTA), 
            # then sorts the candidates by vote_count descending.
            query = """
                SELECT name, logo_path, vote_count 
                FROM candidates 
                ORDER BY 
                    CASE WHEN UPPER(name) = 'NOTA' THEN 1 ELSE 0 END ASC, 
                    vote_count DESC
            """
            
            cursor.execute(query)
            results = cursor.fetchall()
            conn.close()

            self.results_table.setRowCount(len(results))
            # Increase row height so the logos are clearly visible
            self.results_table.verticalHeader().setDefaultSectionSize(80) 

            for i, (name, logo_path, votes) in enumerate(results):
                # 1. Fill Candidate Name
                name_item = QTableWidgetItem(name)
                # Optional: Bold the winner (first row, if it's not NOTA)
                if i == 0 and name.upper() != 'NOTA':
                    font = name_item.font()
                    font.setBold(True)
                    name_item.setFont(font)
                
                self.results_table.setItem(i, 0, name_item)
                
                # 2. Handle the Logo Column (Image rendering)
                logo_label = QLabel()
                logo_label.setAlignment(Qt.AlignCenter)
                
                if logo_path and os.path.exists(logo_path):
                    pixmap = QPixmap(logo_path)
                    # Scale the image to fit the 80px row smoothly
                    scaled = pixmap.scaled(70, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    logo_label.setPixmap(scaled)
                else:
                    logo_label.setText("No Image")

                # Use setCellWidget to display the image label in the table
                self.results_table.setCellWidget(i, 1, logo_label)
                
                # 3. Fill Total Votes
                vote_item = QTableWidgetItem(str(votes))
                vote_item.setTextAlignment(Qt.AlignCenter)
                self.results_table.setItem(i, 2, vote_item)
                
        except Exception as e:
            QMessageBox.critical(self, "Data Error", f"Could not load results: {e}")
    def export_to_pdf(self):
        """Generates the PDF for printing"""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Results", "Election_Results.pdf", "PDF Files (*.pdf)")
        if not file_path: return

        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet

            doc = SimpleDocTemplate(file_path, pagesize=letter)
            elements = []
            styles = getSampleStyleSheet()

            elements.append(Paragraph("<b>OFFICIAL ELECTION RESULTS</b>", styles['Title']))
            elements.append(Spacer(1, 20))

            data = [["Candidate Name", "Total Votes"]] # Exclude logo path for clean print
            for row in range(self.results_table.rowCount()):
                name = self.results_table.item(row, 0).text()
                votes = self.results_table.item(row, 2).text()
                data.append([name, votes])

            pdf_table = Table(data, colWidths=[300, 100])
            pdf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 0), (-1, -1), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ]))

            elements.append(pdf_table)
            doc.build(elements)
            QMessageBox.information(self, "Success", "Results exported to PDF!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {e}")