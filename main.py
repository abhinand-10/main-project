import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt

# Importing your specific UI modules
from ui.registration import RegistrationWindow
from ui.admin_panel import AdminPanel 
from ui.voting_page import VotingWindow 
from ui.results_page import ResultsPage  # 1. IMPORT THE NEW PAGE
from scanner_handler import BiometricHandler

class HomeWindow(QWidget):
    """The landing page with navigation buttons"""
    def __init__(self, controller):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(20)

        label = QLabel("BIOMETRIC VOTING SYSTEM")
        label.setStyleSheet("font-size: 32px; font-weight: bold; color: #2c3e50; margin-bottom: 40px;")
        layout.addWidget(label)

        # Buttons to navigate
        self.btn_reg = QPushButton("Voter Registration")
        self.btn_admin = QPushButton("Admin Panel")
        self.btn_vote = QPushButton("Voting Terminal") 
        self.btn_results = QPushButton("📊 View Election Results") # 2. ADD RESULTS BUTTON

        # Styling buttons
        button_style = """
            QPushButton {
                background-color: #34495e;
                color: white;
                font-size: 18px;
                padding: 20px;
                min-width: 300px;
                border-radius: 10px;
            }
            QPushButton:hover { background-color: #2c3e50; }
        """
        
        # Style for results button (different color to stand out)
        results_style = button_style.replace("#34495e", "#27ae60").replace("#2c3e50", "#219150")

        self.btn_reg.setStyleSheet(button_style)
        self.btn_admin.setStyleSheet(button_style)
        self.btn_vote.setStyleSheet(button_style)
        self.btn_results.setStyleSheet(results_style)

        # Connect button clicks
        self.btn_reg.clicked.connect(lambda: controller.show_screen(1))
        self.btn_admin.clicked.connect(lambda: controller.show_screen(2))
        self.btn_vote.clicked.connect(lambda: controller.show_screen(3)) 
        self.btn_results.clicked.connect(lambda: controller.show_screen(4)) # Index 4

        layout.addWidget(self.btn_reg)
        layout.addWidget(self.btn_admin)
        layout.addWidget(self.btn_vote)
        layout.addWidget(self.btn_results) # Add to layout
        self.setLayout(layout)

class MainController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voting System Management")

        # Responsive Window Settings
        self.setMinimumSize(1000, 700) 
        self.showMaximized() 

        # --- INITIALIZE THE SHARED SCANNER ---
        self.shared_scanner = BiometricHandler()

        # The StackedWidget manages multiple pages
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # --- INITIALIZE SCREENS ---
        self.home_screen = HomeWindow(self)
        self.registration_screen = RegistrationWindow(scanner=self.shared_scanner)
        self.admin_screen = AdminPanel()
        self.voting_screen = VotingWindow(scanner=self.shared_scanner) 
        self.results_screen = ResultsPage() # 3. INITIALIZE RESULTS PAGE

        # Add them to the stack
        self.stacked_widget.addWidget(self.home_screen)         # Index 0
        self.stacked_widget.addWidget(self.registration_screen) # Index 1
        self.stacked_widget.addWidget(self.admin_screen)        # Index 2
        self.stacked_widget.addWidget(self.voting_screen)       # Index 3
        self.stacked_widget.addWidget(self.results_screen)      # Index 4

        # 4. Connect 'Back' signals
        self.registration_screen.switch_back.connect(lambda: self.show_screen(0))
        self.admin_screen.switch_back.connect(lambda: self.show_screen(0))
        self.voting_screen.switch_back.connect(lambda: self.show_screen(0)) 
        self.results_screen.switch_back.connect(lambda: self.show_screen(0)) # Connect results back

    def show_screen(self, index):
        """Switches the visible screen based on index"""
        # If switching to results, refresh the data first
        if index == 4:
            self.results_screen.load_results()
            
        self.stacked_widget.setCurrentIndex(index)

    def closeEvent(self, event):
        """Clean up hardware connections safely"""
        try:
            if self.shared_scanner.mfs:
                self.shared_scanner.mfs.MFS100Uninit()
            print("Scanner resources released safely.")
        except Exception as e:
            print(f"Cleanup error: {e}")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    controller = MainController()
    controller.show() 
    sys.exit(app.exec_())
