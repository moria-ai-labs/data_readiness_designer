"""
Main entry point for the KPI Network Builder application.

This script initializes and runs the PyQt6 application, displaying the main window.
It should be executed from the root directory of the project if running directly,
or it can be part of a module structure.
"""
import sys
from PyQt6.QtWidgets import QApplication

# Relative import for the MainWindow class from the gui module.
# This assumes that 'main.py' is either in the same directory as 'gui.py' (if run directly)
# or that 'src' is treated as a package and this is run as a module from outside 'src',
# e.g., python -m kpi_network_builder.src.main
from .gui import MainWindow

def main():
    """
    Initializes the PyQt6 application and the main window.

    Creates an instance of `QApplication` to manage GUI resources and an
    instance of `MainWindow` from the `.gui` module. The main window is then
    displayed, and the application's event loop is started. The script exits
    when the event loop terminates (e.g., when the main window is closed).
    """
    # Create the PyQt6 application object.
    # sys.argv allows passing command-line arguments to the application, if any.
    app = QApplication(sys.argv)

    # Create an instance of the main application window.
    window = MainWindow()

    # Show the main window.
    window.show()

    # Start the Qt event loop. The application will block here until exit.
    # sys.exit() ensures that the application's exit code is properly returned.
    sys.exit(app.exec())

if __name__ == '__main__':
    # This block ensures that main() is called only when the script is executed directly,
    # not when it's imported as a module into another script.
    main()
