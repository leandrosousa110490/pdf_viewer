import sys
import fitz  # PyMuPDF
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QFileDialog, QScrollArea, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QToolBar, QStatusBar, QSpinBox,
    QMessageBox
)
from PySide6.QtGui import QPixmap, QImage, QAction, QIcon, QPainter, QPen, QColor
from PySide6.QtCore import Qt, QRectF

# --- Configuration ---
DEFAULT_ZOOM_STEP = 0.2
MAX_ZOOM = 5.0
MIN_ZOOM = 0.1
ANNOTATION_COLOR = (1, 1, 0) # Yellow for highlight (RGB, 0-1 range)
ANNOTATION_OPACITY = 0.4

# --- Custom Graphics View for Annotations ---
class PDFPageView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.ScrollHandDrag) # Allow panning
        self.parent_app = parent # Reference to the main app window
        self.drawing = False
        self.start_point = None
        self.current_rect_item = None

    def mousePressEvent(self, event):
        if self.parent_app and self.parent_app.current_tool == "highlight" and event.button() == Qt.LeftButton:
            self.drawing = True
            self.start_point = self.mapToScene(event.pos())
            # Create a temporary visual feedback rectangle
            pen = QPen(QColor(255, 255, 0, 100)) # Semi-transparent yellow
            pen.setWidth(1)
            self.current_rect_item = self.scene().addRect(QRectF(self.start_point, self.start_point), pen)
            self.current_rect_item.setZValue(10) # Ensure it's visible on top
        else:
            super().mousePressEvent(event) # Default drag/pan behavior

    def mouseMoveEvent(self, event):
        if self.drawing and self.start_point and self.current_rect_item:
            end_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, end_point).normalized()
            self.current_rect_item.setRect(rect)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self.drawing and self.start_point and event.button() == Qt.LeftButton:
            self.drawing = False
            end_point = self.mapToScene(event.pos())
            if self.current_rect_item:
                self.scene().removeItem(self.current_rect_item) # Remove visual feedback item
                self.current_rect_item = None

            # Convert scene coordinates to PDF coordinates and add annotation
            if self.parent_app and self.parent_app.pdf_document:
                rect = QRectF(self.start_point, end_point).normalized()
                self.parent_app.add_highlight_annotation(rect)
            self.start_point = None
        else:
            super().mouseReleaseEvent(event)


# --- Main Application Window ---
class PDFViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Python PDF Reader & Annotator")
        self.setGeometry(100, 100, 900, 700)

        self.pdf_document = None
        self.current_page_num = 0
        self.zoom_factor = 1.0
        self.pdf_display_item = None # QGraphicsPixmapItem
        self.current_tool = None # e.g., "highlight"
        self.modified = False # Track if changes need saving

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

        # Graphics View for PDF display and interaction
        self.scene = QGraphicsScene(self)
        self.view = PDFPageView(self.scene, self) # Use custom view

        main_layout.addWidget(self.view)

    def create_actions(self):
        # --- File Actions ---
        self.open_action = QAction(QIcon.fromTheme("document-open", QIcon("icons/open.png")), "&Open...", self)
        self.open_action.setStatusTip("Open PDF file")
        self.open_action.triggered.connect(self.open_pdf)

        self.save_action = QAction(QIcon.fromTheme("document-save", QIcon("icons/save.png")), "&Save", self)
        self.save_action.setStatusTip("Save changes to the PDF")
        self.save_action.triggered.connect(self.save_pdf)
        self.save_action.setEnabled(False) # Disabled until modifications

        self.save_as_action = QAction(QIcon.fromTheme("document-save-as"), "Save &As...", self)
        self.save_as_action.setStatusTip("Save the PDF to a new file")
        self.save_as_action.triggered.connect(self.save_pdf_as)
        self.save_as_action.setEnabled(False) # Disabled until doc loaded

        self.exit_action = QAction(QIcon.fromTheme("application-exit"), "E&xit", self)
        self.exit_action.setStatusTip("Exit application")
        self.exit_action.triggered.connect(self.close)

        # --- Navigation Actions ---
        self.prev_page_action = QAction(QIcon.fromTheme("go-previous", QIcon("icons/prev.png")), "Previous Page", self)
        self.prev_page_action.triggered.connect(self.prev_page)

        self.next_page_action = QAction(QIcon.fromTheme("go-next", QIcon("icons/next.png")), "Next Page", self)
        self.next_page_action.triggered.connect(self.next_page)

        self.zoom_in_action = QAction(QIcon.fromTheme("zoom-in", QIcon("icons/zoom_in.png")), "Zoom In", self)
        self.zoom_in_action.triggered.connect(self.zoom_in)

        self.zoom_out_action = QAction(QIcon.fromTheme("zoom-out", QIcon("icons/zoom_out.png")), "Zoom Out", self)
        self.zoom_out_action.triggered.connect(self.zoom_out)

        # --- Editing Actions ---
        self.highlight_action = QAction(QIcon("icons/highlight.png"), "Highlight Text", self) # Add an icon
        self.highlight_action.setStatusTip("Select area to highlight")
        self.highlight_action.setCheckable(True)
        self.highlight_action.triggered.connect(self.toggle_highlight_tool)


    def create_toolbars(self):
        # --- File Toolbar ---
        file_toolbar = QToolBar("File")
        file_toolbar.addAction(self.open_action)
        file_toolbar.addAction(self.save_action)
        # file_toolbar.addAction(self.save_as_action) # Optional
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
        edit_toolbar.addAction(self.highlight_action)
        self.addToolBar(Qt.TopToolBarArea, edit_toolbar)


    def create_menus(self):
         # Optional: Add menus if desired
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addAction(self.save_as_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.prev_page_action)
        view_menu.addAction(self.next_page_action)
        view_menu.addSeparator()
        view_menu.addAction(self.zoom_in_action)
        view_menu.addAction(self.zoom_out_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(self.highlight_action)


    def create_statusbar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def update_ui_state(self):
        """Enable/disable UI elements based on application state."""
        has_doc = self.pdf_document is not None
        page_count = self.pdf_document.page_count if has_doc else 0
        on_first_page = (self.current_page_num == 0)
        on_last_page = (self.current_page_num == page_count - 1) if has_doc else True

        self.save_action.setEnabled(self.modified)
        self.save_as_action.setEnabled(has_doc)

        self.prev_page_action.setEnabled(has_doc and not on_first_page)
        self.next_page_action.setEnabled(has_doc and not on_last_page)
        self.page_spinbox.setEnabled(has_doc)
        self.zoom_in_action.setEnabled(has_doc and self.zoom_factor < MAX_ZOOM)
        self.zoom_out_action.setEnabled(has_doc and self.zoom_factor > MIN_ZOOM)
        self.highlight_action.setEnabled(has_doc)

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


    def open_pdf(self):
        """Opens a PDF file selected by the user."""
        if self.modified:
            reply = QMessageBox.question(self, 'Unsaved Changes',
                                           "You have unsaved changes. Do you want to save them before opening a new file?",
                                           QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if reply == QMessageBox.Save:
                if not self.save_pdf(): # If save fails or is cancelled
                    return
            elif reply == QMessageBox.Cancel:
                return
            # If Discard, continue opening

        filepath, _ = QFileDialog.getOpenFileName(
            self, "Open PDF File", "", "PDF Files (*.pdf);;All Files (*)"
        )
        if filepath:
            try:
                # Close previous document first
                if self.pdf_document:
                    self.pdf_document.close()

                self.pdf_document = fitz.open(filepath)
                self.current_page_num = 0
                self.zoom_factor = 1.0
                self.filepath = filepath # Store for saving
                self.modified = False
                self.setWindowTitle(f"Python PDF Reader - {filepath}")
                self.status_bar.showMessage(f"Opened: {filepath}")
                self.show_page()
            except Exception as e:
                QMessageBox.critical(self, "Error Opening PDF", f"Could not open file:\n{e}")
                self.pdf_document = None
                self.filepath = None
                self.setWindowTitle("Python PDF Reader & Annotator")
                self.status_bar.showMessage("Failed to open file.")
            finally:
                self.update_ui_state() # Always update UI

    def show_page(self):
        """Renders and displays the current page."""
        if not self.pdf_document:
            self.scene.clear()
            return

        try:
            page = self.pdf_document.load_page(self.current_page_num)

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
            # Ensure correct color order if needed (Fitz usually uses RGB)
            # if image_format == QImage.Format_RGB888:
            #     qimage = qimage.rgbSwapped() # If source was BGR

            qpixmap = QPixmap.fromImage(qimage)

            # Display the pixmap in the scene
            self.scene.clear() # Clear previous page/items
            self.pdf_display_item = self.scene.addPixmap(qpixmap)
            self.scene.setSceneRect(self.pdf_display_item.boundingRect()) # Fit scene to pixmap

            self.status_bar.showMessage(f"Page {self.current_page_num + 1}/{self.pdf_document.page_count} | Zoom: {self.zoom_factor:.1f}x")

        except Exception as e:
            QMessageBox.warning(self, "Error Displaying Page", f"Could not display page {self.current_page_num + 1}:\n{e}")
            self.scene.clear() # Clear on error
            self.status_bar.showMessage(f"Error displaying page {self.current_page_num + 1}")
        finally:
            self.update_ui_state()


    def prev_page(self):
        if self.pdf_document and self.current_page_num > 0:
            self.current_page_num -= 1
            self.show_page()

    def next_page(self):
        if self.pdf_document and self.current_page_num < self.pdf_document.page_count - 1:
            self.current_page_num += 1
            self.show_page()

    def go_to_page_from_spinbox(self, page_num):
         # Spinbox value is 1-based, internal is 0-based
        target_page = page_num - 1
        if self.pdf_document and 0 <= target_page < self.pdf_document.page_count:
            if target_page != self.current_page_num:
                self.current_page_num = target_page
                self.show_page()

    def zoom_in(self):
        if self.pdf_document and self.zoom_factor < MAX_ZOOM:
            self.zoom_factor += DEFAULT_ZOOM_STEP
            self.zoom_factor = min(self.zoom_factor, MAX_ZOOM) # Ensure max not exceeded
            self.show_page() # Re-render with new zoom

    def zoom_out(self):
        if self.pdf_document and self.zoom_factor > MIN_ZOOM:
            self.zoom_factor -= DEFAULT_ZOOM_STEP
            self.zoom_factor = max(self.zoom_factor, MIN_ZOOM) # Ensure min not exceeded
            self.show_page() # Re-render with new zoom

    # --- Editing Functionality ---

    def toggle_highlight_tool(self, checked):
        if checked:
            self.current_tool = "highlight"
            self.view.setDragMode(QGraphicsView.NoDrag) # Disable panning when drawing
            self.status_bar.showMessage("Highlight tool selected. Drag to highlight.")
            # Uncheck other tools if you add more
        else:
            self.current_tool = None
            self.view.setDragMode(QGraphicsView.ScrollHandDrag) # Re-enable panning
            self.status_bar.showMessage("Highlight tool deselected.")


    def add_highlight_annotation(self, scene_rect):
        """Adds a highlight annotation to the PDF based on scene coordinates."""
        if not self.pdf_document or not self.pdf_display_item:
            return

        try:
            page = self.pdf_document.load_page(self.current_page_num)

            # --- Coordinate Conversion ---
            # We need to convert scene coordinates (pixels in the view)
            # back to PDF coordinates (points on the page).
            # This requires knowing the page's original size and the current zoom.

            # Get the inverse transformation matrix (from display back to original page)
            # The matrix used for rendering was fitz.Matrix(zoom, zoom)
            inverse_matrix = fitz.Matrix(1/self.zoom_factor, 1/self.zoom_factor)

            # Transform the corners of the scene rectangle
            pdf_p1 = fitz.Point(scene_rect.topLeft()) * inverse_matrix
            pdf_p2 = fitz.Point(scene_rect.bottomRight()) * inverse_matrix

            # Create a fitz.Rect from the transformed points
            pdf_rect = fitz.Rect(pdf_p1, pdf_p2)

            # Add the highlight annotation using PyMuPDF
            annot = page.add_highlight_annot(pdf_rect)
            # Customize appearance (optional)
            annot.set_colors(stroke=ANNOTATION_COLOR) # PyMuPDF uses 'stroke' for highlight color
            annot.set_opacity(ANNOTATION_OPACITY)
            annot.update() # Apply changes to the annotation

            self.modified = True
            self.status_bar.showMessage("Highlight added.")
            self.show_page() # Re-render the page to show the new annotation immediately

        except Exception as e:
            QMessageBox.warning(self, "Annotation Error", f"Could not add highlight:\n{e}")
            self.status_bar.showMessage("Failed to add highlight.")
        finally:
             self.update_ui_state()


    # --- Saving ---

    def save_pdf(self):
        """Saves the document to its current filepath."""
        if not self.pdf_document or not self.filepath or not self.modified:
            # Maybe save was clicked accidentally, or no changes made
             if not self.modified and self.filepath:
                 self.status_bar.showMessage("No changes to save.")
                 return True # Indicate success (nothing needed saving)
             else:
                 self.status_bar.showMessage("Nothing to save.")
                 return False # Indicate failure/nothing done

        try:
            # Use garbage collection to allow overwriting, incremental=False ensures changes are embedded
            self.pdf_document.save(self.filepath, garbage=4, deflate=True, incremental=False)
            self.modified = False
            self.status_bar.showMessage(f"Saved: {self.filepath}")
            self.update_ui_state()
            return True # Indicate success
        except Exception as e:
            QMessageBox.critical(self, "Error Saving PDF", f"Could not save file:\n{e}")
            self.status_bar.showMessage("Error saving file.")
            return False # Indicate failure

    def save_pdf_as(self):
        """Saves the document to a new filepath."""
        if not self.pdf_document:
             self.status_bar.showMessage("No document loaded to save.")
             return False

        new_filepath, _ = QFileDialog.getSaveFileName(
            self, "Save PDF As...", self.filepath, "PDF Files (*.pdf);;All Files (*)"
        )

        if new_filepath:
            # Ensure it has a .pdf extension if not provided
            if not new_filepath.lower().endswith('.pdf'):
                new_filepath += '.pdf'

            try:
                # Save to the new location
                self.pdf_document.save(new_filepath, garbage=4, deflate=True, incremental=False)
                self.filepath = new_filepath # Update current filepath
                self.modified = False # Changes are now saved
                self.setWindowTitle(f"Python PDF Reader - {self.filepath}")
                self.status_bar.showMessage(f"Saved As: {self.filepath}")
                self.update_ui_state()
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error Saving PDF", f"Could not save file to '{new_filepath}':\n{e}")
                self.status_bar.showMessage("Error saving file.")
                return False
        else:
            # User cancelled Save As dialog
             self.status_bar.showMessage("Save As cancelled.")
             return False # Indicate cancellation/failure


    def closeEvent(self, event):
        """Handle closing the application, check for unsaved changes."""
        if self.modified:
            reply = QMessageBox.question(self, 'Unsaved Changes',
                                           "You have unsaved changes. Do you want to save them before exiting?",
                                           QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)

            if reply == QMessageBox.Save:
                if self.save_pdf():
                    event.accept() # Close if save successful
                else:
                    event.ignore() # Don't close if save failed/cancelled
            elif reply == QMessageBox.Cancel:
                event.ignore() # Don't close
            else: # Discard
                event.accept() # Close without saving
        else:
            event.accept() # No changes, close normally

        # Clean up PDF document if open
        if self.pdf_document:
            self.pdf_document.close()
            self.pdf_document = None


# --- Main Execution ---
if __name__ == "__main__":
    # Create dummy icon files if they don't exist (replace with real icons!)
    import os
    icon_dir = "icons"
    os.makedirs(icon_dir, exist_ok=True)
    dummy_icons = ["open.png", "save.png", "prev.png", "next.png", "zoom_in.png", "zoom_out.png", "highlight.png"]
    for icon_name in dummy_icons:
        icon_path = os.path.join(icon_dir, icon_name)
        if not os.path.exists(icon_path):
             try:
                 from PIL import Image # Optional: Create placeholder image if PIL installed
                 img = Image.new('RGB', (16, 16), color = 'gray')
                 img.save(icon_path)
             except ImportError:
                 # If PIL not installed, create empty file as placeholder
                 with open(icon_path, 'w') as f:
                     pass # Create empty file

    app = QApplication(sys.argv)
    main_window = PDFViewerApp()
    main_window.show()
    sys.exit(app.exec())
