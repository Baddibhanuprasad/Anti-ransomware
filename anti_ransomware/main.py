import sys
import os
import threading
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer
from ui.main_window import AntiRansomwareUI

def main():
    app = QApplication(sys.argv)
    
    # Set application style
    app.setStyle('Fusion')
    
    window = AntiRansomwareUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()