import os
import sys
import io
import fitz  # PyMuPDF
from PyQt6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QVBoxLayout, QHBoxLayout, 
                            QWidget, QPushButton, QLabel, QScrollArea, QSplitter,
                            QListWidget, QListWidgetItem, QToolBar, QStatusBar, QComboBox, QSlider,
                            QMessageBox)
from PyQt6.QtGui import QPixmap, QImage, QAction, QIcon
from PyQt6.QtCore import Qt, QSize, QRect, QPoint

class PDFEditorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.doc = None
        self.current_page = 0
        self.total_pages = 0
        self.zoom_factor = 1.0
        self.recent_files = []
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("PDF Viewer")
        self.setGeometry(100, 100, 1200, 800)
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        
        # Create a splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Create recent files panel instead of file explorer
        self.file_list = self.create_recent_files_panel()
        
        # Create right panel with PDF view
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Create PDF view area
        self.pdf_view = QScrollArea()
        self.pdf_view.setWidgetResizable(True)
        self.pdf_container = QWidget()
        self.pdf_layout = QVBoxLayout(self.pdf_container)
        
        # Image label to display PDF page
        self.image_label = QLabel("Open a PDF file to start")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(600, 600)
        self.pdf_layout.addWidget(self.image_label)
        
        self.pdf_view.setWidget(self.pdf_container)
        
        right_layout.addWidget(self.pdf_view)
        
        # Add widgets to splitter
        splitter.addWidget(self.file_list)
        splitter.addWidget(right_panel)
        splitter.setSizes([200, 1000])  # Default sizes
        
        main_layout.addWidget(splitter)
        
        self.setCentralWidget(central_widget)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
        # Set up dark theme
        self.apply_dark_theme()
        
    def apply_dark_theme(self):
        # Dark theme style
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2D2D30;
                color: #E1E1E1;
            }
            QToolBar, QStatusBar {
                background-color: #1E1E1E;
                color: #E1E1E1;
                border: none;
            }
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #1E88E5;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
            QPushButton:disabled {
                background-color: #3D3D3D;
                color: #9D9D9D;
            }
            QComboBox, QSpinBox {
                background-color: #3D3D3D;
                color: #E1E1E1;
                border: 1px solid #555555;
                padding: 2px;
                border-radius: 3px;
            }
            QScrollArea, QTreeView, QListWidget {
                background-color: #252526;
                border: 1px solid #3F3F46;
            }
            QSlider::groove:horizontal {
                border: 1px solid #999999;
                height: 6px;
                background: #3D3D3D;
                margin: 2px 0;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #0078D7;
                border: 1px solid #0078D7;
                width: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #3F3F46;
            }
            QListWidget::item:selected {
                background-color: #0078D7;
            }
            QListWidget::item:hover {
                background-color: #3E3E40;
            }
        """)
        
    def create_recent_files_panel(self):
        # Create a list widget for recent files
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Label
        title_label = QLabel("Recent Files")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # List widget
        self.recent_list = QListWidget()
        self.recent_list.itemClicked.connect(self.on_recent_file_clicked)
        
        # Open button
        open_btn = QPushButton("Open PDF File")
        open_btn.clicked.connect(self.open_file)
        
        layout.addWidget(title_label)
        layout.addWidget(self.recent_list)
        layout.addWidget(open_btn)
        
        return panel
        
    def create_toolbar(self):
        # Main toolbar
        self.toolbar = QToolBar("Main Toolbar")
        self.toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.toolbar)
        
        # Open file action
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        self.toolbar.addAction(open_action)
        
        self.toolbar.addSeparator()
        
        # Previous page action
        prev_action = QAction("Previous", self)
        prev_action.triggered.connect(self.prev_page)
        self.toolbar.addAction(prev_action)
        
        # Page navigation combo
        self.page_combo = QComboBox()
        self.page_combo.setEditable(True)
        self.page_combo.setFixedWidth(100)
        self.page_combo.activated.connect(self.go_to_page)
        self.toolbar.addWidget(self.page_combo)
        
        # Next page action
        next_action = QAction("Next", self)
        next_action.triggered.connect(self.next_page)
        self.toolbar.addAction(next_action)
        
        self.toolbar.addSeparator()
        
        # Zoom controls
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.triggered.connect(self.zoom_out)
        self.toolbar.addAction(zoom_out_action)
        
        # Zoom slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 200)  # 10% to 200%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(100)
        self.zoom_slider.valueChanged.connect(self.zoom_slider_changed)
        self.toolbar.addWidget(self.zoom_slider)
        
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.triggered.connect(self.zoom_in)
        self.toolbar.addAction(zoom_in_action)
        
        self.toolbar.addSeparator()
        
        # Extract text action
        extract_action = QAction("Extract Text", self)
        extract_action.triggered.connect(self.extract_text)
        self.toolbar.addAction(extract_action)

    def on_recent_file_clicked(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and os.path.exists(file_path):
            self.load_pdf(file_path)
        
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open PDF File", "", "PDF Files (*.pdf)"
        )
        if file_path:
            self.load_pdf(file_path)
            
    def add_to_recent_files(self, file_path):
        # Check if file is already in recent files
        for i in range(self.recent_list.count()):
            item = self.recent_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == file_path:
                self.recent_list.takeItem(i)
                break
                
        # Add file to top of recent files
        filename = os.path.basename(file_path)
        item = QListWidgetItem(filename)
        item.setData(Qt.ItemDataRole.UserRole, file_path)
        self.recent_list.insertItem(0, item)
        
        # Limit to 10 recent files
        while self.recent_list.count() > 10:
            self.recent_list.takeItem(self.recent_list.count() - 1)
            
    def load_pdf(self, file_path):
        try:
            # Close existing document if open
            if self.doc:
                self.doc.close()
                
            # Open the PDF file
            self.doc = fitz.open(file_path)
            self.total_pages = len(self.doc)
            self.current_page = 0
            
            # Update page combo box
            self.page_combo.clear()
            for i in range(self.total_pages):
                self.page_combo.addItem(f"Page {i+1}/{self.total_pages}")
                
            # Display the first page
            self.display_page(self.current_page)
            
            # Update window title with filename
            filename = os.path.basename(file_path)
            self.setWindowTitle(f"PDF Viewer - {filename}")
            
            # Add to recent files
            self.add_to_recent_files(file_path)
            
            self.statusBar.showMessage(f"Loaded: {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open PDF: {str(e)}")
            self.statusBar.showMessage(f"Error: {str(e)}")
            
    def display_page(self, page_num):
        if not self.doc or page_num < 0 or page_num >= self.total_pages:
            return
            
        try:
            # Get the page
            page = self.doc[page_num]
            
            # Render to PNG in memory
            zoom = 1.5 * self.zoom_factor  # Base zoom factor
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert pixmap to PNG data
            png_data = pix.tobytes("png")
            
            # Load PNG data into QImage
            pixmap = QPixmap()
            pixmap.loadFromData(png_data)
            
            # Set the pixmap
            self.image_label.setPixmap(pixmap)
            
            # Update current page
            self.current_page = page_num
            self.page_combo.setCurrentIndex(page_num)
            
            self.statusBar.showMessage(f"Page {page_num + 1} of {self.total_pages}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to display page: {str(e)}")
            self.statusBar.showMessage(f"Error displaying page: {str(e)}")
    
    def extract_text(self):
        if not self.doc:
            self.statusBar.showMessage("No document open")
            return
            
        try:
            page = self.doc[self.current_page]
            text = page.get_text()
            
            # Create a dialog to display the text
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Extracted Text")
            msg_box.setText(text[:500] + ("..." if len(text) > 500 else ""))
            msg_box.setDetailedText(text)
            msg_box.exec()
            
        except Exception as e:
            self.statusBar.showMessage(f"Error extracting text: {str(e)}")
            
    def prev_page(self):
        if self.doc and self.current_page > 0:
            self.display_page(self.current_page - 1)
            
    def next_page(self):
        if self.doc and self.current_page < self.total_pages - 1:
            self.display_page(self.current_page + 1)
            
    def go_to_page(self, index):
        if self.doc:
            self.display_page(index)
            
    def zoom_in(self):
        self.zoom_factor *= 1.2
        self.zoom_slider.setValue(int(self.zoom_factor * 100))
        self.display_page(self.current_page)
        
    def zoom_out(self):
        self.zoom_factor /= 1.2
        self.zoom_slider.setValue(int(self.zoom_factor * 100))
        self.display_page(self.current_page)
        
    def zoom_slider_changed(self, value):
        self.zoom_factor = value / 100
        self.display_page(self.current_page)
                
    def closeEvent(self, event):
        """Handle application close event"""
        if self.doc:
            self.doc.close()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = PDFEditorWindow()
    window.show()
    sys.exit(app.exec()) 