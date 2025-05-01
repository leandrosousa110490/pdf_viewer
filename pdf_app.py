import sys
import fitz  # PyMuPDF
import pandas as pd
import openpyxl
import pyarrow  # For Parquet support
import pyarrow.parquet as pq
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QFileDialog, QScrollArea, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QToolBar, QStatusBar, QSpinBox,
    QMessageBox, QDialog, QTextEdit, QSplitter, QTableView, QHeaderView,
    QAbstractItemView, QComboBox, QStackedLayout, QProgressDialog
)
from PySide6.QtGui import (
    QPixmap, QImage, QAction, QIcon, QPainter, QPen, QColor, 
    QBrush, QFont, QLinearGradient, QPainterPath, QStandardItemModel,
    QStandardItem
)
from PySide6.QtCore import (
    Qt, QRectF, QSize, QAbstractTableModel, QModelIndex, QTimer
)

# --- Configuration ---
DEFAULT_ZOOM_STEP = 0.2
MAX_ZOOM = 5.0
MIN_ZOOM = 0.1
ANNOTATION_COLOR = (1, 1, 0) # Yellow for highlight (RGB, 0-1 range)
ANNOTATION_OPACITY = 0.4

# --- Excel Table Model ---
class ExcelTableModel(QAbstractTableModel):
    """Table model for displaying and editing Excel data using pandas DataFrame."""
    
    def __init__(self, data=None, parent=None):
        super().__init__(parent)
        self.df = pd.DataFrame() if data is None else data
        
    def rowCount(self, parent=QModelIndex()):
        return len(self.df)
        
    def columnCount(self, parent=QModelIndex()):
        return len(self.df.columns)
        
    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
            
        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = self.df.iloc[index.row(), index.column()]
            # Handle various data types appropriately
            if pd.isna(value):
                return "" if role == Qt.DisplayRole else None
            elif isinstance(value, (float, int)):
                return str(value)
            else:
                return str(value)
                
        return None
        
    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return str(self.df.columns[section])
            elif orientation == Qt.Vertical:
                return str(self.df.index[section])
        return None
        
    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            try:
                row, col = index.row(), index.column()
                # Try to auto-convert types (e.g., numeric strings to numbers)
                try:
                    # First try to convert to numeric
                    if value.strip() == "":
                        converted_value = None  # Empty cell
                    else:
                        # Check if it's a number
                        try:
                            if '.' in value:
                                converted_value = float(value)
                            else:
                                converted_value = int(value)
                        except ValueError:
                            converted_value = value  # Keep as string
                except:
                    converted_value = value
                    
                self.df.iloc[row, col] = converted_value
                self.dataChanged.emit(index, index)
                return True
            except Exception as e:
                print(f"Error setting data: {e}")
                return False
        return False
        
    def flags(self, index):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable
        
    def setDataFrame(self, dataframe):
        """Update the model with a new DataFrame."""
        self.beginResetModel()
        self.df = dataframe
        self.endResetModel()

# --- Icon Helper Function ---
def create_icon(icon_type):
    """Create program icons programmatically instead of loading from files."""
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    
    if icon_type == "open":
        # Folder icon
        painter.setPen(QPen(QColor(50, 150, 200), 2))
        painter.setBrush(QBrush(QColor(100, 180, 255, 180)))
        painter.drawRect(8, 16, 48, 36)
        painter.drawRect(20, 8, 24, 12)
        
    elif icon_type == "open_pdf":
        # PDF file icon
        painter.setPen(QPen(QColor(200, 50, 50), 2))
        painter.setBrush(QBrush(QColor(240, 100, 100, 200)))
        painter.drawRect(8, 8, 48, 48)
        
        # PDF text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(8, 8, 48, 48), Qt.AlignCenter, "PDF")
        
    elif icon_type == "open_excel":
        # Excel file icon
        painter.setPen(QPen(QColor(0, 100, 0), 2))
        painter.setBrush(QBrush(QColor(0, 120, 0)))
        painter.drawRect(8, 8, 48, 48)
        
        # "XLS" text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(8, 8, 48, 48), Qt.AlignCenter, "XLS")
        
    elif icon_type == "open_csv":
        # CSV icon
        painter.setPen(QPen(QColor(180, 100, 20), 2))
        painter.setBrush(QBrush(QColor(220, 120, 30)))
        painter.drawRect(8, 8, 48, 48)
        
        # "CSV" text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(8, 8, 48, 48), Qt.AlignCenter, "CSV")
        
    elif icon_type == "open_parquet":
        # Parquet icon
        painter.setPen(QPen(QColor(30, 80, 150), 2))
        painter.setBrush(QBrush(QColor(40, 100, 180)))
        painter.drawRect(8, 8, 48, 48)
        
        # "PQ" text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(8, 8, 48, 48), Qt.AlignCenter, "PQ")
        
    elif icon_type == "save":
        # Generic save icon
        painter.setPen(QPen(QColor(50, 150, 50), 2))
        painter.setBrush(QBrush(QColor(200, 200, 200)))
        painter.drawRect(12, 12, 40, 40)
        painter.setBrush(QBrush(QColor(100, 200, 100)))
        painter.drawRect(22, 22, 20, 20)
        painter.setBrush(QBrush(QColor(200, 200, 200)))
        painter.drawRect(28, 8, 8, 8)
        
    elif icon_type == "save_pdf":
        # PDF save icon
        painter.setPen(QPen(QColor(200, 50, 50), 2))
        painter.setBrush(QBrush(QColor(240, 100, 100, 200)))
        painter.drawRect(12, 12, 40, 40)
        
        # PDF text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(QRectF(12, 12, 40, 40), Qt.AlignCenter, "PDF")
        
        # Save indicator
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRect(28, 8, 8, 8)
        
    elif icon_type == "save_excel":
        # Excel save icon
        painter.setPen(QPen(QColor(0, 100, 0), 2))
        painter.setBrush(QBrush(QColor(0, 120, 0)))
        painter.drawRect(12, 12, 40, 40)
        
        # XLS text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(QRectF(12, 12, 40, 40), Qt.AlignCenter, "XLS")
        
        # Save indicator
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRect(28, 8, 8, 8)
        
    elif icon_type == "save_csv":
        # CSV save icon
        painter.setPen(QPen(QColor(180, 100, 20), 2))
        painter.setBrush(QBrush(QColor(220, 120, 30)))
        painter.drawRect(12, 12, 40, 40)
        
        # CSV text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(QRectF(12, 12, 40, 40), Qt.AlignCenter, "CSV")
        
        # Save indicator
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRect(28, 8, 8, 8)
        
    elif icon_type == "save_parquet":
        # Parquet save icon
        painter.setPen(QPen(QColor(30, 80, 150), 2))
        painter.setBrush(QBrush(QColor(40, 100, 180)))
        painter.drawRect(12, 12, 40, 40)
        
        # PQ text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(QRectF(12, 12, 40, 40), Qt.AlignCenter, "PQ")
        
        # Save indicator
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.drawRect(28, 8, 8, 8)
    
    elif icon_type == "excel":
        # Excel icon (original)
        painter.setPen(QPen(QColor(0, 100, 0), 2))
        painter.setBrush(QBrush(QColor(0, 120, 0)))
        painter.drawRect(8, 8, 48, 48)
        
        # "X" for Excel
        painter.setPen(QPen(QColor(255, 255, 255), 4))
        painter.drawLine(18, 18, 46, 46)
        painter.drawLine(46, 18, 18, 46)
        
    elif icon_type == "csv":
        # CSV icon (original)
        painter.setPen(QPen(QColor(180, 100, 20), 2))
        painter.setBrush(QBrush(QColor(220, 120, 30)))
        painter.drawRect(8, 8, 48, 48)
        
        # "CSV" text
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(QRectF(8, 8, 48, 48), Qt.AlignCenter, "CSV")
        
    elif icon_type == "parquet":
        # Parquet icon (original)
        painter.setPen(QPen(QColor(30, 80, 150), 2))
        painter.setBrush(QBrush(QColor(40, 100, 180)))
        painter.drawRect(8, 8, 48, 48)
        
        # "PQ" text (short for parquet)
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        painter.setFont(QFont("Arial", 14, QFont.Bold))
        painter.drawText(QRectF(8, 8, 48, 48), Qt.AlignCenter, "PQ")
        
    elif icon_type == "prev":
        # Previous page icon
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(150, 150, 150)))
        path = QPainterPath()
        path.moveTo(44, 12)
        path.lineTo(20, 32)
        path.lineTo(44, 52)
        path.closeSubpath()
        painter.drawPath(path)
        
    elif icon_type == "next":
        # Next page icon
        painter.setPen(QPen(QColor(100, 100, 100), 2))
        painter.setBrush(QBrush(QColor(150, 150, 150)))
        path = QPainterPath()
        path.moveTo(20, 12)
        path.lineTo(44, 32)
        path.lineTo(20, 52)
        path.closeSubpath()
        painter.drawPath(path)
        
    elif icon_type == "zoom_in":
        # Zoom in icon
        painter.setPen(QPen(QColor(100, 100, 100), 3))
        painter.setBrush(QBrush(Qt.transparent))
        painter.drawEllipse(12, 12, 30, 30)
        painter.drawLine(38, 38, 52, 52)
        painter.drawLine(27, 18, 27, 36)
        painter.drawLine(18, 27, 36, 27)
        
    elif icon_type == "zoom_out":
        # Zoom out icon
        painter.setPen(QPen(QColor(100, 100, 100), 3))
        painter.setBrush(QBrush(Qt.transparent))
        painter.drawEllipse(12, 12, 30, 30)
        painter.drawLine(38, 38, 52, 52)
        painter.drawLine(18, 27, 36, 27)
        
    elif icon_type == "text_view":
        # Text view icon
        painter.setPen(QPen(QColor(70, 130, 180), 2))
        painter.setBrush(QBrush(QColor(240, 240, 240)))
        painter.drawRect(10, 10, 44, 44)
        
        # Draw text lines
        painter.setPen(QPen(QColor(70, 130, 180), 2))
        painter.drawLine(15, 20, 48, 20)
        painter.drawLine(15, 30, 48, 30)
        painter.drawLine(15, 40, 35, 40)
        
    elif icon_type == "dark_mode":
        # Dark mode icon
        gradient = QLinearGradient(0, 0, 64, 64)
        gradient.setColorAt(0, QColor(30, 30, 50))
        gradient.setColorAt(1, QColor(80, 80, 120))
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(100, 100, 140), 2))
        painter.drawEllipse(10, 10, 44, 44)
        
        # Moon shape
        painter.setBrush(QBrush(QColor(220, 220, 255)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(18, 14, 30, 30)
        painter.setBrush(QBrush(gradient))
        painter.drawEllipse(26, 14, 30, 30)
    
    painter.end()
    return QIcon(pixmap)

# --- Custom Graphics View for Annotations ---
class PDFPageView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag) # Allow panning
        self.parent_app = parent # Reference to the main app window


# --- Main Application Window ---
class PDFViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF & Excel Viewer")
        self.setGeometry(100, 100, 1200, 800)

        # Current document tracking
        self.pdf_documents = {}  # Map of filepath -> document
        self.excel_filepaths = []  # List of open excel files
        self.csv_filepaths = []  # List of open CSV files
        self.parquet_filepaths = []  # List of open Parquet files
        
        # Current active document
        self.current_pdf = None
        self.current_pdf_path = None
        self.current_page_num = 0
        self.zoom_factor = 1.0
        self.pdf_display_item = None # QGraphicsPixmapItem
        self.modified = False # Track if changes need saving
        
        # View mode
        self.is_side_by_side = False
        self.dark_mode = False
        
        # Data file attributes
        self.excel_filepath = None
        self.excel_model = ExcelTableModel()
        self.excel_modified = False
        self.current_sheet = None
        self.excel_sheets = []
        
        # Data file type tracking
        self.current_data_type = None  # 'excel', 'csv', 'parquet'
        
        # Loading dialog
        self.progress_dialog = None
        self.loading_timer = QTimer()
        self.loading_timer.timeout.connect(self.update_progress_dialog)

        # --- Setup UI ---
        self.setup_ui()
        self.create_actions()
        self.create_toolbars()
        self.create_menus() # Optional: If you want menus
        self.create_statusbar()

        self.update_ui_state()

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Add file selector dropdown at the top
        file_selector_layout = QHBoxLayout()
        file_selector_layout.addWidget(QLabel("Current File:"))
        self.file_selector = QComboBox()
        self.file_selector.currentIndexChanged.connect(self.switch_current_file)
        file_selector_layout.addWidget(self.file_selector)
        
        # View mode toggle
        self.view_mode_button = QPushButton("Toggle Side-by-Side View")
        self.view_mode_button.clicked.connect(self.toggle_view_mode)
        file_selector_layout.addWidget(self.view_mode_button)
        
        main_layout.addLayout(file_selector_layout)
        
        # Create stacked widget for switching between single and side-by-side views
        self.stacked_widget = QWidget()
        self.stacked_layout = QStackedLayout(self.stacked_widget)
        
        # Create single view widget
        self.single_view_widget = QWidget()
        single_layout = QVBoxLayout(self.single_view_widget)
        
        # Create splitter for side-by-side view
        self.split_view_widget = QWidget()
        split_layout = QVBoxLayout(self.split_view_widget)
        self.splitter = QSplitter(Qt.Horizontal)
        split_layout.addWidget(self.splitter)
        
        # --- PDF Viewer for both modes ---
        self.pdf_widget = QWidget()
        pdf_layout = QVBoxLayout(self.pdf_widget)

        # Graphics View for PDF display and interaction
        self.scene = QGraphicsScene(self)
        self.view = PDFPageView(self.scene, self) # Use custom view
        pdf_layout.addWidget(self.view)
        
        # --- Excel Viewer for both modes ---
        self.excel_widget = QWidget()
        excel_layout = QVBoxLayout(self.excel_widget)
        
        # Sheet selector
        sheet_layout = QHBoxLayout()
        sheet_layout.addWidget(QLabel("Sheet:"))
        self.sheet_selector = QComboBox()
        self.sheet_selector.currentIndexChanged.connect(self.change_excel_sheet)
        sheet_layout.addWidget(self.sheet_selector)
        excel_layout.addLayout(sheet_layout)
        
        # Excel table view
        self.excel_view = QTableView()
        self.excel_view.setModel(self.excel_model)
        self.excel_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.excel_view.verticalHeader().setDefaultSectionSize(25)
        self.excel_view.setAlternatingRowColors(True)
        self.excel_view.setSelectionMode(QAbstractItemView.SingleSelection)
        excel_layout.addWidget(self.excel_view)
        
        # Set up single view mode - starts with PDF by default
        single_layout.addWidget(self.pdf_widget)
        
        # Set up side-by-side view mode
        self.splitter.addWidget(self.pdf_widget)
        self.splitter.addWidget(self.excel_widget)
        self.splitter.setSizes([600, 600])
        
        # Add both view modes to the stacked layout
        self.stacked_layout.addWidget(self.single_view_widget)
        self.stacked_layout.addWidget(self.split_view_widget)
        
        # Add stacked widget to main layout
        main_layout.addWidget(self.stacked_widget)
        
        # Set default view mode to single
        self.stacked_layout.setCurrentIndex(0)
    
    def toggle_view_mode(self):
        """Toggle between single view and side-by-side view."""
        # If we're currently in single view mode
        if not self.is_side_by_side:
            # Reparent widgets to their respective containers in the split view
            self.pdf_widget.setParent(None)
            self.excel_widget.setParent(None)
            
            self.splitter.addWidget(self.pdf_widget)
            self.splitter.addWidget(self.excel_widget)
            
            # Switch to split view
            self.stacked_layout.setCurrentIndex(1)
            self.is_side_by_side = True
            self.view_mode_button.setText("Switch to Single View")
            self.status_bar.showMessage("Side-by-side view enabled")
        else:
            # Determine which view is currently being shown in single mode
            current_index = self.stacked_layout.currentIndex()
            
            # Reparent widgets from the splitter
            self.pdf_widget.setParent(None)
            self.excel_widget.setParent(None)
            
            # Add current active widget to single view
            self.single_view_widget.layout().addWidget(
                self.pdf_widget if self.file_selector.currentText().lower().endswith(('.pdf')) else self.excel_widget
            )
            
            # Switch to single view
            self.stacked_layout.setCurrentIndex(0)
            self.is_side_by_side = False
            self.view_mode_button.setText("Switch to Side-by-Side View")
            self.status_bar.showMessage("Single view enabled")
    
    def switch_current_file(self, index):
        """Switch between open files when user selects from dropdown."""
        if index < 0 or self.file_selector.count() == 0:
            return
            
        selected_file = self.file_selector.currentText()
        if not selected_file:
            return
            
        # Check if we're switching file types
        is_pdf = selected_file.lower().endswith(('.pdf'))
        
        # Save any pending changes in current document
        if not self.check_for_unsaved_changes():
            # User cancelled the operation, revert to previous selection
            current_file = None
            if self.current_pdf_path:
                current_file = self.current_pdf_path
            elif self.excel_filepath:
                current_file = self.excel_filepath
                
            if current_file:
                # Block signals to avoid recursive calls
                self.file_selector.blockSignals(True)
                for i in range(self.file_selector.count()):
                    if self.file_selector.itemText(i) == current_file:
                        self.file_selector.setCurrentIndex(i)
                        break
                self.file_selector.blockSignals(False)
            return
        
        if is_pdf:
            # Load the selected PDF
            if selected_file in self.pdf_documents:
                self.load_selected_pdf(selected_file)
                
                # In single view mode, make sure PDF view is visible
                if not self.is_side_by_side:
                    # Remove any existing widgets from single view
                    self.clear_single_view()
                    
                    # Add PDF widget
                    self.single_view_widget.layout().addWidget(self.pdf_widget)
            else:
                QMessageBox.warning(self, "File Error", f"Cannot find PDF file: {selected_file}")
                return
        else:
            # Load the selected data file
            if selected_file in self.excel_filepaths:
                self.current_data_type = 'excel'
                self.load_selected_excel(selected_file)
            elif selected_file in self.csv_filepaths:
                self.current_data_type = 'csv'
                self.load_selected_csv(selected_file)
            elif selected_file in self.parquet_filepaths:
                self.current_data_type = 'parquet'
                self.load_selected_parquet(selected_file)
            else:
                QMessageBox.warning(self, "File Error", f"Cannot find data file: {selected_file}")
                return
                
            # In single view mode, make sure Excel view is visible
            if not self.is_side_by_side:
                # Remove any existing widgets from single view
                self.clear_single_view()
                
                # Add Excel widget
                self.single_view_widget.layout().addWidget(self.excel_widget)
        
        # Update window title
        self.setWindowTitle(f"PDF & Excel Viewer - {selected_file}")
        self.update_ui_state()
    
    def clear_single_view(self):
        """Helper method to clear all widgets from single view layout."""
        for i in reversed(range(self.single_view_widget.layout().count())):
            widget = self.single_view_widget.layout().itemAt(i).widget()
            if widget:
                widget.setParent(None)
    
    def load_selected_csv(self, filepath):
        """Load a previously opened CSV file."""
        try:
            # Show loading dialog
            self.show_loading_dialog("Loading CSV", f"Loading {filepath}...")
            
            # Read the CSV file
            df = pd.read_csv(filepath)
            
            # Update the model with the data
            self.excel_model.setDataFrame(df)
            self.excel_filepath = filepath
            self.excel_modified = False
            
            # Clear sheet selector (CSV doesn't have sheets)
            self.sheet_selector.blockSignals(True)
            self.sheet_selector.clear()
            self.sheet_selector.blockSignals(False)
            
            self.status_bar.showMessage(f"Switched to: {filepath}")
            
            # Close loading dialog
            self.close_loading_dialog()
            
            # Fix for signal connection issue
            if hasattr(self.excel_model, "dataChanged"):
                try:
                    self.excel_model.dataChanged.disconnect(self.on_excel_data_changed)
                except:
                    pass  # No connection to disconnect
                self.excel_model.dataChanged.connect(self.on_excel_data_changed)
                
        except Exception as e:
            QMessageBox.warning(self, "Error Loading CSV", f"Could not load CSV file:\n{e}")
            self.close_loading_dialog()
    
    def load_selected_parquet(self, filepath):
        """Load a previously opened Parquet file."""
        try:
            # Show loading dialog
            self.show_loading_dialog("Loading Parquet", f"Loading {filepath}...")
            
            # Read the Parquet file
            df = pd.read_parquet(filepath)
            
            # Update the model with the data
            self.excel_model.setDataFrame(df)
            self.excel_filepath = filepath
            self.excel_modified = False
            
            # Clear sheet selector (Parquet doesn't have sheets)
            self.sheet_selector.blockSignals(True)
            self.sheet_selector.clear()
            self.sheet_selector.blockSignals(False)
            
            self.status_bar.showMessage(f"Switched to: {filepath}")
            
            # Close loading dialog
            self.close_loading_dialog()
            
            # Fix for signal connection issue
            if hasattr(self.excel_model, "dataChanged"):
                try:
                    self.excel_model.dataChanged.disconnect(self.on_excel_data_changed)
                except:
                    pass  # No connection to disconnect
                self.excel_model.dataChanged.connect(self.on_excel_data_changed)
                
        except Exception as e:
            QMessageBox.warning(self, "Error Loading Parquet", f"Could not load Parquet file:\n{e}")
            self.close_loading_dialog()
    
    def check_for_unsaved_changes(self):
        """Check for unsaved changes before switching files."""
        pdf_needs_saving = self.modified and self.current_pdf
        excel_needs_saving = self.excel_modified and self.excel_filepath
        
        if pdf_needs_saving or excel_needs_saving:
            message = ""
            if pdf_needs_saving and excel_needs_saving:
                message = "You have unsaved changes. Save before switching files?"
            elif pdf_needs_saving:
                message = "You have unsaved changes to the PDF. Save before switching?"
            else:
                message = "You have unsaved changes to the Excel file. Save before switching?"
                
            reply = QMessageBox.question(self, 'Unsaved Changes', message,
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                                         
            if reply == QMessageBox.Save:
                if pdf_needs_saving:
                    self.save_pdf()
                if excel_needs_saving:
                    self.save_excel()
            elif reply == QMessageBox.Cancel:
                # Restore the previous selection
                return False
        return True

    def create_actions(self):
        # --- File Actions ---
        self.open_action = QAction(create_icon("open_pdf"), "&Open PDF...", self)
        self.open_action.setStatusTip("Open PDF file")
        self.open_action.triggered.connect(self.open_pdf)
        
        self.open_excel_action = QAction(create_icon("open_excel"), "Open &Excel...", self)
        self.open_excel_action.setStatusTip("Open Excel file")
        self.open_excel_action.triggered.connect(self.open_excel)
        
        self.open_csv_action = QAction(create_icon("open_csv"), "Open &CSV...", self)
        self.open_csv_action.setStatusTip("Open CSV file")
        self.open_csv_action.triggered.connect(self.open_csv)
        
        self.open_parquet_action = QAction(create_icon("open_parquet"), "Open &Parquet...", self)
        self.open_parquet_action.setStatusTip("Open Parquet file")
        self.open_parquet_action.triggered.connect(self.open_parquet)

        self.save_action = QAction(create_icon("save_pdf"), "&Save PDF", self)
        self.save_action.setStatusTip("Save changes to the PDF")
        self.save_action.triggered.connect(self.save_pdf)
        self.save_action.setEnabled(False) # Disabled until modifications

        self.save_excel_action = QAction(create_icon("save_excel"), "Save &Excel", self)
        self.save_excel_action.setStatusTip("Save changes to the Excel file")
        self.save_excel_action.triggered.connect(self.save_excel)
        self.save_excel_action.setEnabled(False)  # Disabled until modifications
        
        self.save_csv_action = QAction(create_icon("save_csv"), "Save &CSV", self)
        self.save_csv_action.setStatusTip("Save changes to the CSV file")
        self.save_csv_action.triggered.connect(self.save_excel)  # Reuse save_excel
        self.save_csv_action.setEnabled(False)  # Disabled until modifications
        
        self.save_parquet_action = QAction(create_icon("save_parquet"), "Save &Parquet", self)
        self.save_parquet_action.setStatusTip("Save changes to the Parquet file")
        self.save_parquet_action.triggered.connect(self.save_excel)  # Reuse save_excel
        self.save_parquet_action.setEnabled(False)  # Disabled until modifications

        self.save_as_action = QAction(QIcon.fromTheme("document-save-as"), "Save PDF &As...", self)
        self.save_as_action.setStatusTip("Save the PDF to a new file")
        self.save_as_action.triggered.connect(self.save_pdf_as)
        self.save_as_action.setEnabled(False) # Disabled until doc loaded
        
        self.save_excel_as_action = QAction(QIcon.fromTheme("document-save-as"), "Save Excel As...", self)
        self.save_excel_as_action.setStatusTip("Save the Excel file to a new file")
        self.save_excel_as_action.triggered.connect(self.save_excel_as)
        self.save_excel_as_action.setEnabled(False)  # Disabled until excel loaded

        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "E&xit", self)
        self.exit_action.setStatusTip("Exit application")
        self.exit_action.triggered.connect(self.close)

        # --- Navigation Actions ---
        self.prev_page_action = QAction(create_icon("prev"), "Previous Page", self)
        self.prev_page_action.triggered.connect(self.prev_page)

        self.next_page_action = QAction(create_icon("next"), "Next Page", self)
        self.next_page_action.triggered.connect(self.next_page)

        self.zoom_in_action = QAction(create_icon("zoom_in"), "Zoom In", self)
        self.zoom_in_action.triggered.connect(self.zoom_in)

        self.zoom_out_action = QAction(create_icon("zoom_out"), "Zoom Out", self)
        self.zoom_out_action.triggered.connect(self.zoom_out)
        
        # --- View Actions ---
        self.dark_mode_action = QAction(create_icon("dark_mode"), "Toggle Dark Mode", self)
        self.dark_mode_action.setStatusTip("Switch between light and dark mode")
        self.dark_mode_action.setCheckable(True)
        self.dark_mode_action.triggered.connect(self.toggle_dark_mode)

        # --- Editing Actions ---
        self.text_view_action = QAction(create_icon("text_view"), "View as Text", self)
        self.text_view_action.setStatusTip("View PDF content as plain text")
        self.text_view_action.triggered.connect(self.show_text_view)
        self.text_view_action.setEnabled(False)  # Disabled until doc loaded

    def create_toolbars(self):
        # --- File Toolbar ---
        file_toolbar = QToolBar("File")
        file_toolbar.addAction(self.open_action)
        file_toolbar.addAction(self.open_excel_action)
        file_toolbar.addAction(self.open_csv_action)
        file_toolbar.addAction(self.open_parquet_action)
        file_toolbar.addSeparator()
        file_toolbar.addAction(self.save_action)
        file_toolbar.addAction(self.save_excel_action)
        file_toolbar.addAction(self.save_csv_action)
        file_toolbar.addAction(self.save_parquet_action)
        self.addToolBar(Qt.TopToolBarArea, file_toolbar)

        # --- Navigation Toolbar ---
        navigation_toolbar = QToolBar("Navigation")
        navigation_toolbar.addAction(self.prev_page_action)

        self.page_spinbox = QSpinBox(self)
        self.page_spinbox.setMinimum(1)
        self.page_spinbox.setMaximum(1) # Will be updated when PDF loads
        self.page_spinbox.valueChanged.connect(self.go_to_page_from_spinbox)
        self.page_spinbox.setFixedWidth(60)
        navigation_toolbar.addWidget(self.page_spinbox)

        self.total_pages_label = QLabel("/ 1")
        self.total_pages_label.setFixedWidth(40)
        navigation_toolbar.addWidget(self.total_pages_label)

        navigation_toolbar.addAction(self.next_page_action)
        navigation_toolbar.addSeparator()
        navigation_toolbar.addAction(self.zoom_out_action)
        navigation_toolbar.addAction(self.zoom_in_action)
        self.addToolBar(Qt.TopToolBarArea, navigation_toolbar)

        # --- Editing Toolbar ---
        edit_toolbar = QToolBar("Editing")
        edit_toolbar.addAction(self.text_view_action)
        edit_toolbar.addAction(self.dark_mode_action)
        self.addToolBar(Qt.TopToolBarArea, edit_toolbar)

    def create_menus(self):
         # Optional: Add menus if desired
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.open_excel_action)
        file_menu.addAction(self.open_csv_action)
        file_menu.addAction(self.open_parquet_action)
        file_menu.addSeparator()
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_excel_action)
        file_menu.addAction(self.save_csv_action)
        file_menu.addAction(self.save_parquet_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addAction(self.save_excel_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.prev_page_action)
        view_menu.addAction(self.next_page_action)
        view_menu.addSeparator()
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.text_view_action)
        edit_menu.addAction(self.dark_mode_action)

    def create_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def update_ui_state(self):
        """Enable/disable UI elements based on application state."""
        has_doc = self.current_pdf is not None
        has_excel = self.excel_filepath is not None
        page_count = self.current_pdf.page_count if has_doc else 0
        on_first_page = (self.current_page_num == 0)
        on_last_page = (self.current_page_num == page_count - 1) if has_doc else True

        # Update save buttons based on file type and modification state
        self.save_action.setEnabled(self.modified and has_doc)
        self.save_as_action.setEnabled(has_doc)
        
        # Enable Excel/CSV/Parquet save buttons based on file type
        is_excel = has_excel and self.excel_filepath.lower().endswith(('.xlsx', '.xls'))
        is_csv = has_excel and self.excel_filepath.lower().endswith('.csv')
        is_parquet = has_excel and self.excel_filepath.lower().endswith(('.parquet', '.pq'))
        
        self.save_excel_action.setEnabled(self.excel_modified and is_excel)
        self.save_csv_action.setEnabled(self.excel_modified and is_csv)
        self.save_parquet_action.setEnabled(self.excel_modified and is_parquet)
        self.save_excel_as_action.setEnabled(has_excel)

        self.prev_page_action.setEnabled(has_doc and not on_first_page)
        self.next_page_action.setEnabled(has_doc and not on_last_page)
        self.page_spinbox.setEnabled(has_doc)
        self.zoom_in_action.setEnabled(has_doc and self.zoom_factor < MAX_ZOOM)
        self.zoom_out_action.setEnabled(has_doc and self.zoom_factor > MIN_ZOOM)
        self.text_view_action.setEnabled(has_doc)

        if has_doc:
            self.page_spinbox.setMaximum(page_count)
            # Block signals temporarily to prevent recursive call during update
            self.page_spinbox.blockSignals(True)
            self.page_spinbox.setValue(self.current_page_num + 1)
            self.page_spinbox.blockSignals(False)
            self.total_pages_label.setText(f"/ {page_count}")
        else:
            self.page_spinbox.setMaximum(1)
            self.page_spinbox.setValue(1)
            self.total_pages_label.setText("/ 1")

    def show_loading_dialog(self, title, message, max_steps=0):
        """Show a loading dialog for long operations."""
        # Only show loading dialogs for potentially lengthy operations
        # Skip dialog for operations that should be nearly instant
        
        # Don't show another dialog if one is already visible
        if self.progress_dialog and self.progress_dialog.isVisible():
            if max_steps > 0 and self.progress_dialog.maximum() > 0:
                self.progress_dialog.setMaximum(max_steps)
            self.progress_dialog.setLabelText(message)
            return
            
        self.progress_dialog = QProgressDialog(message, "Cancel", 0, max_steps, self)
        self.progress_dialog.setWindowTitle(title)
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        
        # If max_steps is 0, use an undetermined progress bar
        if max_steps == 0:
            self.progress_dialog.setRange(0, 0)  # Undetermined progress
            
        # Set a minimum delay before showing the dialog (in milliseconds)
        # This prevents the dialog from flashing for quick operations
        self.progress_dialog.setMinimumDuration(800)  # Only show if operation takes longer than 800ms
        
        self.progress_dialog.setAutoClose(True)
        self.progress_dialog.setAutoReset(True)
        self.progress_dialog.setValue(0)
        
        # For undetermined progress, start a timer to keep UI responsive
        if max_steps == 0:
            self.loading_timer.start(100)  # Update every 100ms
    
    def update_progress_dialog(self):
        """Update the progress dialog to keep the UI responsive."""
        if self.progress_dialog and self.progress_dialog.isVisible():
            # Just process events to keep UI responsive
            QApplication.processEvents()
    
    def close_loading_dialog(self):
        """Close the loading dialog."""
        if self.progress_dialog:
            self.loading_timer.stop()
            self.progress_dialog.close()
            self.progress_dialog = None
            # Force processing of events to ensure dialog is removed from screen
            QApplication.processEvents()
            
    def open_excel(self):
        """Opens Excel files selected by the user."""
        if self.excel_modified and self.excel_filepath:
            if not self.check_for_unsaved_changes():
                return
                
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, "Open Excel Files", "", "Excel Files (*.xlsx *.xls);;All Files (*)"
        )
        
        if not filepaths:
            return
        
        # Check for large files
        large_files = []
        if len(filepaths) <= 1:
            import os
            try:
                for filepath in filepaths:
                    filesize = os.path.getsize(filepath)
                    if filesize > 2_000_000:  # 2MB threshold for Excel
                        large_files.append(filepath)
            except:
                pass
        
        # Show loading dialog only for multiple or large files
        if len(filepaths) > 1:
            self.show_loading_dialog("Opening Excel Files", 
                                    f"Opening {len(filepaths)} Excel files...", 
                                    len(filepaths))
        
        # Process each selected file
        for i, filepath in enumerate(filepaths):
            try:
                # Show loading dialog only when needed
                is_large = filepath in large_files
                is_multiple = len(filepaths) > 1
                
                if is_large or is_multiple:
                    if len(filepaths) == 1:
                        self.show_loading_dialog("Opening Excel File", 
                                              f"Loading {filepath}...")
                    else:
                        # Update progress for multiple files
                        if self.progress_dialog:
                            self.progress_dialog.setValue(i)
                            self.progress_dialog.setLabelText(f"Loading {filepath}...")
                
                # Check if we can open the file
                excel_file = pd.ExcelFile(filepath)
                
                # Add to our list of open Excel files if not already there
                if filepath not in self.excel_filepaths:
                    self.excel_filepaths.append(filepath)
                    
                    # Add to file selector dropdown
                    existing_items = [self.file_selector.itemText(i) for i in range(self.file_selector.count())]
                    if filepath not in existing_items:
                        self.file_selector.addItem(filepath)
                
                # If this is the first Excel file or we don't have an active one, make it active
                if len(self.excel_filepaths) == 1 or self.excel_filepath is None:
                    # Get sheets
                    self.excel_sheets = excel_file.sheet_names
                    
                    # Read the first sheet
                    if self.excel_sheets:
                        self.current_sheet = self.excel_sheets[0]
                        df = pd.read_excel(filepath, sheet_name=self.current_sheet)
                        
                        # Show loading dialog for large datasets
                        if len(df) > 5000 or len(df.columns) > 20:
                            self.show_loading_dialog("Loading Data", 
                                                  f"Loading {len(df)} rows of data...")
                            
                        self.excel_model.setDataFrame(df)
                        
                        # Update sheet selector
                        self.sheet_selector.blockSignals(True)
                        self.sheet_selector.clear()
                        self.sheet_selector.addItems(self.excel_sheets)
                        self.sheet_selector.blockSignals(False)
                    
                    self.excel_filepath = filepath
                    self.excel_modified = False
                    self.current_data_type = 'excel'
                    
                    # Select this file in the dropdown
                    self.file_selector.setCurrentText(filepath)
                
                self.status_bar.showMessage(f"Opened Excel: {filepath}")
                
                # Fix for signal connection issue
                if hasattr(self.excel_model, "dataChanged"):
                    try:
                        self.excel_model.dataChanged.disconnect(self.on_excel_data_changed)
                    except:
                        pass  # No connection to disconnect
                    self.excel_model.dataChanged.connect(self.on_excel_data_changed)
                
            except Exception as e:
                QMessageBox.critical(self, "Error Opening Excel", f"Could not open Excel file '{filepath}':\n{e}")
                # Ensure dialog is closed on error
                self.close_loading_dialog()
                
            # Process events to keep UI responsive
            QApplication.processEvents()
        
        # Close the loading dialog
        self.close_loading_dialog()
        
        # In single view mode, ensure Excel widget is visible when Excel file is active
        if not self.is_side_by_side and self.excel_filepath and filepaths:
            # Remove current widget from single view
            self.clear_single_view()
            
            # Add Excel widget
            self.single_view_widget.layout().addWidget(self.excel_widget)
        
        self.update_ui_state()
    
    def change_excel_sheet(self, index):
        """Change to a different sheet in the Excel workbook."""
        if index >= 0 and index < len(self.excel_sheets):
            try:
                sheet_name = self.excel_sheets[index]
                if self.excel_filepath and sheet_name != self.current_sheet:
                    # Check for unsaved changes first
                    if self.excel_modified:
                        reply = QMessageBox.question(self, 'Unsaved Changes',
                                                f"Save changes to sheet '{self.current_sheet}' before switching?",
                                                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                        if reply == QMessageBox.Save:
                            self.save_excel()
                        elif reply == QMessageBox.Cancel:
                            # Revert the combobox to the previous selection
                            self.sheet_selector.blockSignals(True)
                            self.sheet_selector.setCurrentText(self.current_sheet)
                            self.sheet_selector.blockSignals(False)
                            return
                    
                    # Show loading dialog
                    self.show_loading_dialog("Switching Sheet", f"Loading sheet '{sheet_name}'...")
                    
                    # Load the new sheet
                    df = pd.read_excel(self.excel_filepath, sheet_name=sheet_name)
                    
                    # Check if this is a large sheet (show longer loading time)
                    if len(df) > 1000 or len(df.columns) > 20:
                        # Update loading message for large sheets
                        if self.progress_dialog:
                            self.progress_dialog.setLabelText(f"Loading large sheet '{sheet_name}' ({len(df)} rows)...")
                    
                    # Update the model with new data
                    self.excel_model.setDataFrame(df)
                    self.current_sheet = sheet_name
                    self.excel_modified = False
                    self.status_bar.showMessage(f"Switched to sheet: {sheet_name}")
                    
                    # Close loading dialog
                    self.close_loading_dialog()
                    
                    self.update_ui_state()
            except Exception as e:
                QMessageBox.warning(self, "Sheet Change Error", f"Could not switch to sheet '{sheet_name}':\n{e}")
                # Close loading dialog on error
                self.close_loading_dialog()
    
    def on_excel_data_changed(self, topLeft, bottomRight):
        """Handle changes to Excel data."""
        self.excel_modified = True
        self.update_ui_state()
    
    def save_excel(self):
        """Save the Excel file to its current filepath."""
        if not self.excel_filepath or not self.excel_modified:
            if not self.excel_modified and self.excel_filepath:
                self.status_bar.showMessage("No Excel changes to save.")
                return True
            else:
                self.status_bar.showMessage("No Excel file to save.")
                return False
        
        return self.save_excel_as(self.excel_filepath)
    
    def save_excel_as(self, target_path=None):
        """Save the tabular data file to a new filepath."""
        if not self.excel_model.df.empty:
            # Determine file types based on data type or extension
            if not target_path:
                file_filter = ""
                default_ext = ""
                
                if self.current_data_type == 'excel':
                    file_filter = "Excel Files (*.xlsx);;All Files (*)"
                    default_ext = '.xlsx'
                elif self.current_data_type == 'csv':
                    file_filter = "CSV Files (*.csv);;All Files (*)"
                    default_ext = '.csv'
                elif self.current_data_type == 'parquet':
                    file_filter = "Parquet Files (*.parquet);;All Files (*)"
                    default_ext = '.parquet'
                else:
                    # Default to Excel if type not set
                    file_filter = "Excel Files (*.xlsx);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)"
                    default_ext = '.xlsx'
                
                target_path, selected_filter = QFileDialog.getSaveFileName(
                    self, "Save Data As...", self.excel_filepath or "", file_filter
                )
                
                # Check the selected filter to determine format if needed
                if selected_filter == "CSV Files (*.csv)" and not target_path.lower().endswith('.csv'):
                    target_path += '.csv'
                    self.current_data_type = 'csv'
                elif selected_filter == "Parquet Files (*.parquet)" and not target_path.lower().endswith(('.parquet', '.pq')):
                    target_path += '.parquet'
                    self.current_data_type = 'parquet'
                elif selected_filter == "Excel Files (*.xlsx)" and not target_path.lower().endswith(('.xlsx', '.xls')):
                    target_path += '.xlsx'
                    self.current_data_type = 'excel'
            
            if not target_path:
                self.status_bar.showMessage("Save cancelled.")
                return False
            
            # Add default extension if needed based on current data type
            if not target_path.lower().endswith(('.xlsx', '.xls', '.csv', '.parquet', '.pq')):
                if self.current_data_type == 'excel':
                    target_path += '.xlsx'
                elif self.current_data_type == 'csv':
                    target_path += '.csv'
                elif self.current_data_type == 'parquet':
                    target_path += '.parquet'
                else:
                    # Default to Excel
                    target_path += '.xlsx' 
            
            try:
                # Show loading dialog with message based on file size and type
                row_count = len(self.excel_model.df)
                file_type = "file"
                if target_path.lower().endswith(('.xlsx', '.xls')):
                    file_type = "Excel file"
                elif target_path.lower().endswith('.csv'):
                    file_type = "CSV file"
                elif target_path.lower().endswith(('.parquet', '.pq')):
                    file_type = "Parquet file"
                
                message = f"Saving {file_type} to {target_path}..."
                if row_count > 10000:
                    message = f"Saving large {file_type} ({row_count} rows) to {target_path}..."
                
                self.show_loading_dialog(f"Saving {file_type.title()}", message)
                
                # Save based on file extension or current data type
                if target_path.lower().endswith(('.xlsx', '.xls')) or self.current_data_type == 'excel':
                    # Excel file saving, check for multi-sheet
                    if self.current_data_type == 'excel' and len(self.excel_sheets) > 1:
                        # Update progress dialog for multi-sheet files
                        if self.progress_dialog:
                            self.progress_dialog.setLabelText("Processing multiple sheets...")
                        
                        # Read the existing workbook
                        with pd.ExcelWriter(target_path, engine='openpyxl', mode='w') as writer:
                            # Write current sheet with changes
                            self.excel_model.df.to_excel(writer, sheet_name=self.current_sheet, index=False)
                            
                            # Write other sheets (unchanged)
                            for sheet in self.excel_sheets:
                                if sheet != self.current_sheet:
                                    if self.progress_dialog:
                                        self.progress_dialog.setLabelText(f"Saving sheet: {sheet}")
                                    df = pd.read_excel(self.excel_filepath, sheet_name=sheet)
                                    df.to_excel(writer, sheet_name=sheet, index=False)
                    else:
                        # Single sheet or new file
                        self.excel_model.df.to_excel(target_path, sheet_name=self.current_sheet or 'Sheet1', index=False)
                    
                    self.current_data_type = 'excel'
                    
                    # Update file list if new Excel file
                    if target_path not in self.excel_filepaths:
                        self.excel_filepaths.append(target_path)
                        self.file_selector.addItem(target_path)
                
                elif target_path.lower().endswith('.csv') or self.current_data_type == 'csv':
                    # CSV file saving
                    self.excel_model.df.to_csv(target_path, index=False)
                    self.current_data_type = 'csv'
                    
                    # Update file list if new CSV file
                    if target_path not in self.csv_filepaths:
                        self.csv_filepaths.append(target_path)
                        self.file_selector.addItem(target_path)
                
                elif target_path.lower().endswith(('.parquet', '.pq')) or self.current_data_type == 'parquet':
                    # Parquet file saving
                    self.excel_model.df.to_parquet(target_path, index=False)
                    self.current_data_type = 'parquet'
                    
                    # Update file list if new Parquet file
                    if target_path not in self.parquet_filepaths:
                        self.parquet_filepaths.append(target_path)
                        self.file_selector.addItem(target_path)
                
                self.excel_filepath = target_path
                self.excel_modified = False
                self.status_bar.showMessage(f"Saved to: {target_path}")
                self.update_ui_state()
                
                # Close the loading dialog
                self.close_loading_dialog()
                return True
                
            except Exception as e:
                QMessageBox.critical(self, "Error Saving File", f"Could not save file:\n{e}")
                self.status_bar.showMessage("Failed to save file.")
                
                # Close loading dialog on error
                self.close_loading_dialog()
                return False
        else:
            self.status_bar.showMessage("No data to save.")
            return False

    def open_pdf(self):
        """Opens PDF files selected by the user."""
        if self.modified and self.current_pdf:
            if not self.check_for_unsaved_changes():
                return
            
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, "Open PDF Files", "", "PDF Files (*.pdf);;All Files (*)"
        )
        
        if not filepaths:
            return
        
        # Only show loading dialog for multiple files
        if len(filepaths) > 1:
            self.show_loading_dialog("Opening PDF Files", 
                                    f"Opening {len(filepaths)} PDF files...", 
                                    len(filepaths))
        
        # Check for large files that might need loading indicators
        large_files = []
        if len(filepaths) == 1:
            import os
            try:
                filesize = os.path.getsize(filepaths[0])
                if filesize > 5_000_000:  # 5MB threshold for showing loading dialog
                    large_files.append(filepaths[0])
            except:
                pass
            
        # Process each selected file
        for i, filepath in enumerate(filepaths):
            try:
                # Show loading dialog only for large files or when opening multiple files
                if len(filepaths) > 1 or filepath in large_files:
                    if len(filepaths) == 1:
                        self.show_loading_dialog("Opening PDF File", 
                                               f"Loading {filepath}...")
                    else:
                        # Update progress for multiple files
                        if self.progress_dialog:
                            self.progress_dialog.setValue(i)
                            self.progress_dialog.setLabelText(f"Loading {filepath}...")
                
                # Open the PDF file
                pdf_doc = fitz.open(filepath)
                
                # Add to our collection of open documents
                self.pdf_documents[filepath] = pdf_doc
                
                # Add to file selector dropdown if not already there
                existing_items = [self.file_selector.itemText(i) for i in range(self.file_selector.count())]
                if filepath not in existing_items:
                    self.file_selector.addItem(filepath)
                
                # If this is the first file, make it active
                if len(self.pdf_documents) == 1 or self.current_pdf is None:
                    self.current_pdf = pdf_doc
                    self.current_pdf_path = filepath
                    self.current_page_num = 0
                    self.zoom_factor = 1.0
                    self.modified = False
                    
                    # Show the first page
                    self.show_page()
                    
                    # Select this file in the dropdown
                    self.file_selector.setCurrentText(filepath)
                
                self.status_bar.showMessage(f"Opened: {filepath}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error Opening PDF", f"Could not open file '{filepath}':\n{e}")
                # Ensure dialog is closed on error
                self.close_loading_dialog()
                
            # Process events to keep UI responsive
            QApplication.processEvents()
        
        # Close the loading dialog - ensure it's closed even after multiple files
        self.close_loading_dialog()
                
        # In single view mode, ensure PDF widget is visible
        if not self.is_side_by_side and self.current_pdf:
            # Remove current widget from single view
            self.clear_single_view()
            
            # Add PDF widget
            self.single_view_widget.layout().addWidget(self.pdf_widget)
        
        self.update_ui_state()
        
    def show_page(self):
        """Renders and displays the current page."""
        if not self.current_pdf:
            self.scene.clear()
            return

        try:
            # Only show loading indicator for very large/complex pages
            show_loading = False
            if self.current_pdf.page_count > 100:  # Very large document
                show_loading = True
            elif self.current_page_num < self.current_pdf.page_count:
                page = self.current_pdf.load_page(self.current_page_num)
                # Check if page is complex (large dimensions or lots of content)
                if page.rect.width > 1000 or page.rect.height > 1000:
                    show_loading = True
                
            if show_loading:
                self.show_loading_dialog("Rendering Page", 
                                       f"Rendering page {self.current_page_num + 1}...")
            
            page = self.current_pdf.load_page(self.current_page_num)

            # Create a transformation matrix for zooming
            matrix = fitz.Matrix(self.zoom_factor, self.zoom_factor)

            # Render page to a pixmap
            pix = page.get_pixmap(matrix=matrix, alpha=False) # alpha=False for performance

            # Convert fitz.Pixmap to QImage/QPixmap
            if pix.alpha:
                image_format = QImage.Format_RGBA8888
            else:
                image_format = QImage.Format_RGB888 # Common format

            qimage = QImage(pix.samples, pix.width, pix.height, pix.stride, image_format)

            qpixmap = QPixmap.fromImage(qimage)

            # Display the pixmap in the scene
            self.scene.clear() # Clear previous page/items
            self.pdf_display_item = self.scene.addPixmap(qpixmap)
            self.scene.setSceneRect(self.pdf_display_item.boundingRect()) # Fit scene to pixmap

            self.status_bar.showMessage(f"Page {self.current_page_num + 1}/{self.current_pdf.page_count} | Zoom: {self.zoom_factor:.1f}x")
            
            # Close loading dialog if it was shown
            self.close_loading_dialog()

        except Exception as e:
            QMessageBox.warning(self, "Error Displaying Page", f"Could not display page {self.current_page_num + 1}:\n{e}")
            self.scene.clear() # Clear on error
            self.status_bar.showMessage(f"Error displaying page {self.current_page_num + 1}")
            # Close loading dialog on error
            self.close_loading_dialog()
        finally:
            # Ensure loading dialog is closed even if there's an unexpected error
            self.close_loading_dialog()
            self.update_ui_state()

    def prev_page(self):
        if self.current_pdf and self.current_page_num > 0:
            self.current_page_num -= 1
            self.show_page()

    def next_page(self):
        if self.current_pdf and self.current_page_num < self.current_pdf.page_count - 1:
            self.current_page_num += 1
            self.show_page()

    def go_to_page_from_spinbox(self, page_num):
         # Spinbox value is 1-based, internal is 0-based
        target_page = page_num - 1
        if self.current_pdf and 0 <= target_page < self.current_pdf.page_count:
            if target_page != self.current_page_num:
                self.current_page_num = target_page
                self.show_page()

    def zoom_in(self):
        if self.current_pdf and self.zoom_factor < MAX_ZOOM:
            self.zoom_factor += DEFAULT_ZOOM_STEP
            self.zoom_factor = min(self.zoom_factor, MAX_ZOOM) # Ensure max not exceeded
            self.show_page() # Re-render with new zoom

    def zoom_out(self):
        if self.current_pdf and self.zoom_factor > MIN_ZOOM:
            self.zoom_factor -= DEFAULT_ZOOM_STEP
            self.zoom_factor = max(self.zoom_factor, MIN_ZOOM) # Ensure min not exceeded
            self.show_page() # Re-render with new zoom

    # --- Editing Functionality ---

    def toggle_dark_mode(self, checked):
        """Toggle between light and dark mode."""
        self.dark_mode = checked
        
        if checked:
            # Apply dark mode stylesheet
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #2D2D30; color: #E1E1E1; }
                QGraphicsView { background-color: #1E1E1E; border: 1px solid #3F3F46; }
                QToolBar { background-color: #333337; border: 1px solid #3F3F46; }
                QMenuBar { background-color: #333337; color: #E1E1E1; }
                QMenuBar::item:selected { background-color: #3F3F46; }
                QMenu { background-color: #2D2D30; color: #E1E1E1; border: 1px solid #3F3F46; }
                QMenu::item:selected { background-color: #3F3F46; }
                QToolButton { background-color: #333337; color: #E1E1E1; border: none; }
                QToolButton:hover { background-color: #3F3F46; }
                QStatusBar { background-color: #333337; color: #E1E1E1; }
                QSpinBox { background-color: #333337; color: #E1E1E1; border: 1px solid #3F3F46; }
                QLabel { color: #E1E1E1; }
                QHeaderView { background-color: #333337; color: #E1E1E1; }
                QHeaderView::section { background-color: #3F3F46; color: #E1E1E1; border: 1px solid #555555; }
                QTableView { background-color: #2D2D30; color: #E1E1E1; gridline-color: #3F3F46; }
                QTableView::item:selected { background-color: #264F78; }
                QComboBox { background-color: #333337; color: #E1E1E1; border: 1px solid #3F3F46; }
                QComboBox QAbstractItemView { background-color: #2D2D30; color: #E1E1E1; selection-background-color: #3F3F46; }
            """)
            self.status_bar.showMessage("Dark mode enabled")
        else:
            # Reset to light mode (default system style)
            self.setStyleSheet("")
            self.status_bar.showMessage("Light mode enabled")
    
    # --- Text View ---
    
    def show_text_view(self):
        """Display the current page as text in a dialog with copy capability."""
        if not self.current_pdf:
            return

        try:
            page = self.current_pdf.load_page(self.current_page_num)
            text = page.get_text()
            
            # Create a dialog to display text
            dialog = QDialog(self)
            dialog.setWindowTitle(f"Text View - Page {self.current_page_num + 1}")
            dialog.setMinimumSize(700, 600)
            
            # Create layout
            layout = QVBoxLayout(dialog)
            
            # Add information label
            info_label = QLabel(
                "View the text content below. You can select text and copy it using Ctrl+C or right-click menu."
            )
            info_label.setWordWrap(True)
            layout.addWidget(info_label)
            
            # Create a text edit for viewing text (read-only)
            text_edit = QTextEdit(dialog)
            text_edit.setPlainText(text)
            text_edit.setReadOnly(True)  # Set to read-only
            
            # Apply dark mode if active
            if self.dark_mode:
                text_edit.setStyleSheet("""
                    QTextEdit { 
                        background-color: #1E1E1E; 
                        color: #E1E1E1; 
                        border: 1px solid #3F3F46; 
                    }
                """)
                info_label.setStyleSheet("color: #E1E1E1;")
            
            # Add buttons for copying and closing
            buttons_layout = QHBoxLayout()
            
            copy_button = QPushButton("Copy All Text")
            copy_button.clicked.connect(lambda: self.copy_to_clipboard(text))
            
            close_button = QPushButton("Close")
            close_button.clicked.connect(dialog.accept)
            
            buttons_layout.addWidget(copy_button)
            buttons_layout.addWidget(close_button)
            
            # Add widgets to layout
            layout.addWidget(text_edit)
            layout.addLayout(buttons_layout)
            
            # Show the dialog
            dialog.exec()

        except Exception as e:
            QMessageBox.warning(self, "Text View Error", f"Could not extract text from page {self.current_page_num + 1}:\n{e}")
            self.status_bar.showMessage("Error displaying text view")
    
    def copy_to_clipboard(self, text):
        """Copy the provided text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        self.status_bar.showMessage("Text copied to clipboard")

    # --- Saving ---

    def save_pdf(self):
        """Saves the document to its current filepath."""
        if not self.current_pdf or not self.current_pdf_path or not self.modified:
            # Maybe save was clicked accidentally, or no changes made
            if not self.modified and self.current_pdf_path:
                self.status_bar.showMessage("No changes to save.")
                return True # Indicate success (nothing needed saving)
            else:
                self.status_bar.showMessage("Nothing to save.")
                return False # Indicate failure/nothing done

        try:
            # Show loading dialog
            self.show_loading_dialog("Saving PDF", f"Saving to {self.current_pdf_path}...")
            
            # Use garbage collection to allow overwriting, incremental=False ensures changes are embedded
            self.current_pdf.save(self.current_pdf_path, garbage=4, deflate=True, incremental=False)
            self.modified = False
            self.status_bar.showMessage(f"Saved: {self.current_pdf_path}")
            self.update_ui_state()
            
            # Close loading dialog
            self.close_loading_dialog()
            return True # Indicate success
        except Exception as e:
            QMessageBox.critical(self, "Error Saving PDF", f"Could not save file:\n{e}")
            self.status_bar.showMessage("Error saving file.")
            
            # Close loading dialog on error
            self.close_loading_dialog()
            return False # Indicate failure

    def save_pdf_as(self):
        """Saves the document to a new filepath."""
        if not self.current_pdf:
            self.status_bar.showMessage("No document loaded to save.")
            return False

        new_filepath, _ = QFileDialog.getSaveFileName(
            self, "Save PDF As...", self.current_pdf_path, "PDF Files (*.pdf);;All Files (*)"
        )

        if new_filepath:
            # Ensure it has a .pdf extension if not provided
            if not new_filepath.lower().endswith('.pdf'):
                new_filepath += '.pdf'

            try:
                # Show loading dialog
                self.show_loading_dialog("Saving PDF", f"Saving to {new_filepath}...")
                
                # Save to the new location
                self.current_pdf.save(new_filepath, garbage=4, deflate=True, incremental=False)
                self.current_pdf_path = new_filepath # Update current filepath
                self.modified = False # Changes are now saved
                self.setWindowTitle(f"PDF & Excel Viewer - {self.current_pdf_path}")
                self.status_bar.showMessage(f"Saved As: {self.current_pdf_path}")
                self.update_ui_state()
                
                # Close loading dialog
                self.close_loading_dialog()
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error Saving PDF", f"Could not save file to '{new_filepath}':\n{e}")
                self.status_bar.showMessage("Error saving file.")
                
                # Close loading dialog on error
                self.close_loading_dialog()
                return False
        else:
            # User cancelled Save As dialog
            self.status_bar.showMessage("Save As cancelled.")
            return False # Indicate cancellation/failure
    
    def save_excel(self):
        """Save the Excel file to its current filepath."""
        if not self.excel_filepath or not self.excel_modified:
            if not self.excel_modified and self.excel_filepath:
                self.status_bar.showMessage("No Excel changes to save.")
                return True
            else:
                self.status_bar.showMessage("No Excel file to save.")
                return False
        
        return self.save_excel_as(self.excel_filepath)
    
    def save_excel_as(self, target_path=None):
        """Save the tabular data file to a new filepath."""
        if not self.excel_model.df.empty:
            # Determine file types based on data type or extension
            if not target_path:
                file_filter = ""
                default_ext = ""
                
                if self.current_data_type == 'excel':
                    file_filter = "Excel Files (*.xlsx);;All Files (*)"
                    default_ext = '.xlsx'
                elif self.current_data_type == 'csv':
                    file_filter = "CSV Files (*.csv);;All Files (*)"
                    default_ext = '.csv'
                elif self.current_data_type == 'parquet':
                    file_filter = "Parquet Files (*.parquet);;All Files (*)"
                    default_ext = '.parquet'
                else:
                    # Default to Excel if type not set
                    file_filter = "Excel Files (*.xlsx);;CSV Files (*.csv);;Parquet Files (*.parquet);;All Files (*)"
                    default_ext = '.xlsx'
                
                target_path, selected_filter = QFileDialog.getSaveFileName(
                    self, "Save Data As...", self.excel_filepath or "", file_filter
                )
                
                # Check the selected filter to determine format if needed
                if selected_filter == "CSV Files (*.csv)" and not target_path.lower().endswith('.csv'):
                    target_path += '.csv'
                    self.current_data_type = 'csv'
                elif selected_filter == "Parquet Files (*.parquet)" and not target_path.lower().endswith(('.parquet', '.pq')):
                    target_path += '.parquet'
                    self.current_data_type = 'parquet'
                elif selected_filter == "Excel Files (*.xlsx)" and not target_path.lower().endswith(('.xlsx', '.xls')):
                    target_path += '.xlsx'
                    self.current_data_type = 'excel'
            
            if not target_path:
                self.status_bar.showMessage("Save cancelled.")
                return False
            
            # Add default extension if needed based on current data type
            if not target_path.lower().endswith(('.xlsx', '.xls', '.csv', '.parquet', '.pq')):
                if self.current_data_type == 'excel':
                    target_path += '.xlsx'
                elif self.current_data_type == 'csv':
                    target_path += '.csv'
                elif self.current_data_type == 'parquet':
                    target_path += '.parquet'
                else:
                    # Default to Excel
                    target_path += '.xlsx' 
            
            try:
                # Show loading dialog with message based on file size and type
                row_count = len(self.excel_model.df)
                file_type = "file"
                if target_path.lower().endswith(('.xlsx', '.xls')):
                    file_type = "Excel file"
                elif target_path.lower().endswith('.csv'):
                    file_type = "CSV file"
                elif target_path.lower().endswith(('.parquet', '.pq')):
                    file_type = "Parquet file"
                
                message = f"Saving {file_type} to {target_path}..."
                if row_count > 10000:
                    message = f"Saving large {file_type} ({row_count} rows) to {target_path}..."
                
                self.show_loading_dialog(f"Saving {file_type.title()}", message)
                
                # Save based on file extension or current data type
                if target_path.lower().endswith(('.xlsx', '.xls')) or self.current_data_type == 'excel':
                    # Excel file saving, check for multi-sheet
                    if self.current_data_type == 'excel' and len(self.excel_sheets) > 1:
                        # Update progress dialog for multi-sheet files
                        if self.progress_dialog:
                            self.progress_dialog.setLabelText("Processing multiple sheets...")
                        
                        # Read the existing workbook
                        with pd.ExcelWriter(target_path, engine='openpyxl', mode='w') as writer:
                            # Write current sheet with changes
                            self.excel_model.df.to_excel(writer, sheet_name=self.current_sheet, index=False)
                            
                            # Write other sheets (unchanged)
                            for sheet in self.excel_sheets:
                                if sheet != self.current_sheet:
                                    if self.progress_dialog:
                                        self.progress_dialog.setLabelText(f"Saving sheet: {sheet}")
                                    df = pd.read_excel(self.excel_filepath, sheet_name=sheet)
                                    df.to_excel(writer, sheet_name=sheet, index=False)
                    else:
                        # Single sheet or new file
                        self.excel_model.df.to_excel(target_path, sheet_name=self.current_sheet or 'Sheet1', index=False)
                    
                    self.current_data_type = 'excel'
                    
                    # Update file list if new Excel file
                    if target_path not in self.excel_filepaths:
                        self.excel_filepaths.append(target_path)
                        self.file_selector.addItem(target_path)
                
                elif target_path.lower().endswith('.csv') or self.current_data_type == 'csv':
                    # CSV file saving
                    self.excel_model.df.to_csv(target_path, index=False)
                    self.current_data_type = 'csv'
                    
                    # Update file list if new CSV file
                    if target_path not in self.csv_filepaths:
                        self.csv_filepaths.append(target_path)
                        self.file_selector.addItem(target_path)
                
                elif target_path.lower().endswith(('.parquet', '.pq')) or self.current_data_type == 'parquet':
                    # Parquet file saving
                    self.excel_model.df.to_parquet(target_path, index=False)
                    self.current_data_type = 'parquet'
                    
                    # Update file list if new Parquet file
                    if target_path not in self.parquet_filepaths:
                        self.parquet_filepaths.append(target_path)
                        self.file_selector.addItem(target_path)
                
                self.excel_filepath = target_path
                self.excel_modified = False
                self.status_bar.showMessage(f"Saved to: {target_path}")
                self.update_ui_state()
                
                # Close the loading dialog
                self.close_loading_dialog()
                return True
                
            except Exception as e:
                QMessageBox.critical(self, "Error Saving File", f"Could not save file:\n{e}")
                self.status_bar.showMessage("Failed to save file.")
                
                # Close loading dialog on error
                self.close_loading_dialog()
                return False
        else:
            self.status_bar.showMessage("No data to save.")
            return False

    def open_csv(self):
        """Opens CSV files selected by the user."""
        if self.excel_modified and self.excel_filepath:
            if not self.check_for_unsaved_changes():
                return
                
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, "Open CSV Files", "", "CSV Files (*.csv);;All Files (*)"
        )
        
        if not filepaths:
            return
        
        # Check for large files
        large_files = []
        if len(filepaths) <= 1:
            import os
            try:
                for filepath in filepaths:
                    filesize = os.path.getsize(filepath)
                    if filesize > 5_000_000:  # 5MB threshold for CSV
                        large_files.append(filepath)
            except:
                pass
        
        # Show loading dialog only for multiple or large files
        if len(filepaths) > 1:
            self.show_loading_dialog("Opening CSV Files", 
                                    f"Opening {len(filepaths)} CSV files...", 
                                    len(filepaths))
        
        # Process each selected file
        for i, filepath in enumerate(filepaths):
            try:
                # Show loading dialog only when needed
                is_large = filepath in large_files
                is_multiple = len(filepaths) > 1
                
                if is_large or is_multiple:
                    if len(filepaths) == 1:
                        self.show_loading_dialog("Opening CSV File", 
                                              f"Loading {filepath}...")
                    else:
                        # Update progress for multiple files
                        if self.progress_dialog:
                            self.progress_dialog.setValue(i)
                            self.progress_dialog.setLabelText(f"Loading {filepath}...")
                
                # Check if file size is large (for better loading indication)
                import os
                file_size = os.path.getsize(filepath)
                if file_size > 10_000_000:  # 10MB
                    if self.progress_dialog:
                        self.progress_dialog.setLabelText(f"Loading large CSV file ({file_size//1_000_000}MB)...")
                
                # Read the CSV file into pandas
                df = pd.read_csv(filepath)
                
                # Show loading dialog for large datasets
                if len(df) > 10000 or len(df.columns) > 20:
                    self.show_loading_dialog("Processing Data", 
                                          f"Processing {len(df)} rows of CSV data...")
                
                # Add to our list of open CSV files if not already there
                if filepath not in self.csv_filepaths:
                    self.csv_filepaths.append(filepath)
                    
                    # Add to file selector dropdown
                    existing_items = [self.file_selector.itemText(i) for i in range(self.file_selector.count())]
                    if filepath not in existing_items:
                        self.file_selector.addItem(filepath)
                
                # Make this the active data file
                # Update the table model with the data
                self.excel_model.setDataFrame(df)
                self.excel_filepath = filepath
                self.excel_modified = False
                self.current_data_type = 'csv'
                
                # Clear sheet selector (CSV doesn't have sheets)
                self.sheet_selector.blockSignals(True)
                self.sheet_selector.clear()
                self.sheet_selector.blockSignals(False)
                
                # Select this file in the dropdown
                self.file_selector.setCurrentText(filepath)
                
                self.status_bar.showMessage(f"Opened CSV: {filepath}")
                
                # Fix for signal connection issue
                if hasattr(self.excel_model, "dataChanged"):
                    try:
                        self.excel_model.dataChanged.disconnect(self.on_excel_data_changed)
                    except:
                        pass  # No connection to disconnect
                    self.excel_model.dataChanged.connect(self.on_excel_data_changed)
                
            except Exception as e:
                QMessageBox.critical(self, "Error Opening CSV", f"Could not open CSV file '{filepath}':\n{e}")
                # Ensure dialog is closed on error
                self.close_loading_dialog()
                
            # Process events to keep UI responsive
            QApplication.processEvents()
        
        # Close the loading dialog
        self.close_loading_dialog()
        
        # In single view mode, ensure Excel widget is visible for CSV files
        if not self.is_side_by_side and self.excel_filepath and filepaths:
            # Remove current widget from single view
            self.clear_single_view()
            
            # Add Excel widget
            self.single_view_widget.layout().addWidget(self.excel_widget)
        
        self.update_ui_state()
        
    def open_parquet(self):
        """Opens Parquet files selected by the user."""
        if self.excel_modified and self.excel_filepath:
            if not self.check_for_unsaved_changes():
                return
                
        filepaths, _ = QFileDialog.getOpenFileNames(
            self, "Open Parquet Files", "", "Parquet Files (*.parquet *.pq);;All Files (*)"
        )
        
        if not filepaths:
            return
        
        # Check for large files
        large_files = []
        if len(filepaths) <= 1:
            import os
            try:
                for filepath in filepaths:
                    filesize = os.path.getsize(filepath)
                    if filesize > 10_000_000:  # 10MB threshold for Parquet (typically larger)
                        large_files.append(filepath)
            except:
                pass
        
        # Show loading dialog only for multiple or large files
        if len(filepaths) > 1:
            self.show_loading_dialog("Opening Parquet Files", 
                                    f"Opening {len(filepaths)} Parquet files...", 
                                    len(filepaths))
        
        # Process each selected file
        for i, filepath in enumerate(filepaths):
            try:
                # Show loading dialog only when needed
                is_large = filepath in large_files
                is_multiple = len(filepaths) > 1
                
                if is_large or is_multiple:
                    if len(filepaths) == 1:
                        self.show_loading_dialog("Opening Parquet File", 
                                              f"Loading {filepath}...")
                    else:
                        # Update progress for multiple files
                        if self.progress_dialog:
                            self.progress_dialog.setValue(i)
                            self.progress_dialog.setLabelText(f"Loading {filepath}...")
                
                # Check if file size is large (for better loading indication)
                import os
                file_size = os.path.getsize(filepath)
                if file_size > 50_000_000:  # 50MB
                    if self.progress_dialog:
                        self.progress_dialog.setLabelText(f"Loading large Parquet file ({file_size//1_000_000}MB)...")
                
                # Read the Parquet file
                df = pd.read_parquet(filepath)
                
                # Show loading dialog for large datasets
                if len(df) > 20000 or len(df.columns) > 50:
                    self.show_loading_dialog("Processing Data", 
                                          f"Processing {len(df)} rows of Parquet data...")
                
                # Add to our list of open Parquet files if not already there
                if filepath not in self.parquet_filepaths:
                    self.parquet_filepaths.append(filepath)
                    
                    # Add to file selector dropdown
                    existing_items = [self.file_selector.itemText(i) for i in range(self.file_selector.count())]
                    if filepath not in existing_items:
                        self.file_selector.addItem(filepath)
                
                # Make this the active data file
                # Update the table model with the data
                self.excel_model.setDataFrame(df)
                self.excel_filepath = filepath
                self.excel_modified = False
                self.current_data_type = 'parquet'
                
                # Clear sheet selector (Parquet doesn't have sheets)
                self.sheet_selector.blockSignals(True)
                self.sheet_selector.clear()
                self.sheet_selector.blockSignals(False)
                
                # Select this file in the dropdown
                self.file_selector.setCurrentText(filepath)
                
                self.status_bar.showMessage(f"Opened Parquet: {filepath}")
                
                # Fix for signal connection issue
                if hasattr(self.excel_model, "dataChanged"):
                    try:
                        self.excel_model.dataChanged.disconnect(self.on_excel_data_changed)
                    except:
                        pass  # No connection to disconnect
                    self.excel_model.dataChanged.connect(self.on_excel_data_changed)
                
            except Exception as e:
                QMessageBox.critical(self, "Error Opening Parquet", f"Could not open Parquet file '{filepath}':\n{e}")
                # Ensure dialog is closed on error
                self.close_loading_dialog()
                
            # Process events to keep UI responsive
            QApplication.processEvents()
        
        # Close the loading dialog
        self.close_loading_dialog()
        
        # In single view mode, ensure Excel widget is visible for Parquet files
        if not self.is_side_by_side and self.excel_filepath and filepaths:
            # Remove current widget from single view
            self.clear_single_view()
            
            # Add Excel widget
            self.single_view_widget.layout().addWidget(self.excel_widget)
        
        self.update_ui_state()

    def closeEvent(self, event):
        """Handle closing the application, check for unsaved changes."""
        need_to_check_pdf = self.modified and self.current_pdf
        need_to_check_excel = self.excel_modified and self.excel_filepath
        
        if need_to_check_pdf or need_to_check_excel:
            message = ""
            if need_to_check_pdf and need_to_check_excel:
                message = "You have unsaved changes in both PDF and Excel files. Do you want to save them before exiting?"
            elif need_to_check_pdf:
                message = "You have unsaved changes to the PDF. Do you want to save them before exiting?"
            else:
                message = "You have unsaved changes to the Excel file. Do you want to save them before exiting?"
                
            reply = QMessageBox.question(self, 'Unsaved Changes', message,
                                           QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

            if reply == QMessageBox.Save:
                save_ok = True
                if need_to_check_pdf:
                    save_ok = self.save_pdf() and save_ok
                if need_to_check_excel:
                    save_ok = self.save_excel() and save_ok
                    
                if save_ok:
                    event.accept() # Close if save successful
                else:
                    event.ignore() # Don't close if save failed/cancelled
            elif reply == QMessageBox.Cancel:
                event.ignore() # Don't close
            else: # Discard
                event.accept() # Close without saving
        else:
            event.accept() # No changes, close normally

        # Clean up resources - close all open documents
        for path, doc in self.pdf_documents.items():
            if doc:
                doc.close()
        
        self.pdf_documents.clear()
        self.current_pdf = None

    # --- UI Theme ---

    def load_selected_pdf(self, filepath):
        """Load a previously opened PDF document."""
        try:
            # Show loading dialog
            self.show_loading_dialog("Loading PDF", f"Loading {filepath}...")
            
            self.current_pdf_path = filepath
            self.current_pdf = self.pdf_documents[filepath]
            self.current_page_num = 0
            self.show_page()
            self.status_bar.showMessage(f"Switched to: {filepath}")
            
            # Close loading dialog
            self.close_loading_dialog()
        except Exception as e:
            QMessageBox.warning(self, "Error Loading PDF", f"Could not load PDF file:\n{e}")
            self.close_loading_dialog()

    def load_selected_excel(self, filepath):
        """Load a previously opened Excel file."""
        try:
            # Show loading dialog
            self.show_loading_dialog("Loading Excel", f"Loading {filepath}...")
            
            # Load the Excel file again
            excel_file = pd.ExcelFile(filepath)
            self.excel_sheets = excel_file.sheet_names
            
            # Read the first sheet by default
            if len(self.excel_sheets) > 0:
                self.current_sheet = self.excel_sheets[0]
                df = pd.read_excel(filepath, sheet_name=self.current_sheet)
                self.excel_model.setDataFrame(df)
                
                # Update sheet selector
                self.sheet_selector.blockSignals(True)
                self.sheet_selector.clear()
                self.sheet_selector.addItems(self.excel_sheets)
                self.sheet_selector.blockSignals(False)
            
            self.excel_filepath = filepath
            self.excel_modified = False
            self.status_bar.showMessage(f"Switched to: {filepath}")
            
            # Close loading dialog
            self.close_loading_dialog()
            
            # Fix for signal connection issue
            if hasattr(self.excel_model, "dataChanged"):
                try:
                    self.excel_model.dataChanged.disconnect(self.on_excel_data_changed)
                except:
                    pass  # No connection to disconnect
                self.excel_model.dataChanged.connect(self.on_excel_data_changed)
                
        except Exception as e:
            QMessageBox.warning(self, "Error Loading Excel", f"Could not load Excel file:\n{e}")
            self.close_loading_dialog()

# --- Main Execution ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = PDFViewerApp()
    main_window.show()
    sys.exit(app.exec())
