import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt

# Importing your specific UI modules
from ui.registration import RegistrationWindow
from ui.admin_panel import AdminPanel 
from ui.voting_page import VotingWindow 

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
        self.btn_reg.setStyleSheet(button_style)
        self.btn_admin.setStyleSheet(button_style)
        self.btn_vote.setStyleSheet(button_style)

        # Connect button clicks
        self.btn_reg.clicked.connect(lambda: controller.show_screen(1))
        self.btn_admin.clicked.connect(lambda: controller.show_screen(2))
        self.btn_vote.clicked.connect(lambda: controller.show_screen(3)) 

        layout.addWidget(self.btn_reg)
        layout.addWidget(self.btn_admin)
        layout.addWidget(self.btn_vote)
        self.setLayout(layout)

class MainController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Voting System Management")

        # --- ഫുൾ സ്ക്രീൻ മാറ്റങ്ങൾ ഇവിടെ ---
        # Fixed size ഒഴിവാക്കി, വിൻഡോ മാക്സിമൈസ് ചെയ്യുന്നു
        self.setMinimumSize(1000, 700) 
        self.showMaximized() 

        # The StackedWidget manages multiple pages
        self.stacked_widget = QStackedWidget()
        self.setCentralWidget(self.stacked_widget)

        # 1. Initialize the screens
        self.home_screen = HomeWindow(self)
        self.registration_screen = RegistrationWindow()
        self.admin_screen = AdminPanel()
        self.voting_screen = VotingWindow() 

        # 2. Add them to the stack
        self.stacked_widget.addWidget(self.home_screen)         # Index 0
        self.stacked_widget.addWidget(self.registration_screen) # Index 1
        self.stacked_widget.addWidget(self.admin_screen)        # Index 2
        self.stacked_widget.addWidget(self.voting_screen)       # Index 3

        # 3. Connect 'Back' signals
        self.registration_screen.switch_back.connect(lambda: self.show_screen(0))
        self.admin_screen.switch_back.connect(lambda: self.show_screen(0))
        self.voting_screen.switch_back.connect(lambda: self.show_screen(0)) 

    def show_screen(self, index):
        """Switches the visible screen based on index"""
        self.stacked_widget.setCurrentIndex(index)

    def closeEvent(self, event):
        """Clean up hardware connections"""
        try:
            self.registration_screen.scanner.close()
            self.voting_screen.scanner.close()
            print("Resources released safely.")
        except Exception as e:
            print(f"Cleanup error: {e}")
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    controller = MainController()
    # ഇവിടെ show() നൽകുന്നത് വിൻഡോ ഡിസ്‌പ്ലേ ചെയ്യാൻ സഹായിക്കും
    controller.show() 
    sys.exit(app.exec_())