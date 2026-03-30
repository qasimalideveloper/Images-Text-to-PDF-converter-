import sys
import os
import tempfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QFileDialog, QLabel, 
                             QMessageBox, QScrollArea, QGridLayout, QFrame,
                             QDialog, QRubberBand, QTabWidget, QTextEdit)
from PyQt6.QtGui import QIcon, QPixmap, QDrag
from PyQt6.QtCore import Qt, QSize, QMimeData, QPoint, QRect
from PyQt6.QtPrintSupport import QPrinter
from PIL import Image

class CropLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rubberBand = QRubberBand(QRubberBand.Shape.Rectangle, self)
        self.origin = QPoint()
        self.setCursor(Qt.CursorShape.CrossCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.origin = event.position().toPoint()
            self.rubberBand.setGeometry(QRect(self.origin, QSize()))
            self.rubberBand.show()
        
    def mouseMoveEvent(self, event):
        if not self.origin.isNull() and (event.buttons() & Qt.MouseButton.LeftButton):
            rect = QRect(self.origin, event.position().toPoint()).normalized()
            rect = rect.intersected(self.rect())
            self.rubberBand.setGeometry(rect)
        
    def mouseReleaseEvent(self, event):
        pass

    def get_selection_rect(self):
        return self.rubberBand.geometry()


class CropDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.cropped_path = None
        
        self.setWindowTitle("Crop Image")
        self.resize(900, 700)
        
        self.setStyleSheet("""
            QDialog { background-color: #1A1A2E; }
            QLabel { color: #A0A0A0; font-family: 'Segoe UI', Arial, sans-serif; }
            QPushButton {
                background-color: #E94560;
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #FF5A76; }
            QPushButton#cancelBtn { background-color: #0F3460; border: 1px solid #16213E;}
            QPushButton#cancelBtn:hover { background-color: #1A4A87; }
            QScrollArea {
                border: 2px dashed #0F3460;
                border-radius: 12px;
                background-color: #16213E;
            }
            QScrollBar:vertical {
                border: none;
                background: #1A1A2E;
                width: 14px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical { background: #0F3460; min-height: 20px; border-radius: 7px; }
            QScrollBar::handle:vertical:hover { background: #E94560; }
            QScrollBar:horizontal {
                border: none;
                background: #1A1A2E;
                height: 14px;
                border-radius: 7px;
            }
            QScrollBar::handle:horizontal { background: #0F3460; min-width: 20px; border-radius: 7px; }
            QScrollBar::handle:horizontal:hover { background: #E94560; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setWidgetResizable(False)
        
        self.image_label = CropLabel()
        self.pixmap = QPixmap(self.image_path)
        
        max_size = 1500
        if self.pixmap.width() > max_size or self.pixmap.height() > max_size:
            scaled = self.pixmap.scaled(max_size, max_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.scale_factor_w = self.pixmap.width() / scaled.width()
            self.scale_factor_h = self.pixmap.height() / scaled.height()
            self.display_pixmap = scaled
        else:
            self.scale_factor_w = 1.0
            self.scale_factor_h = 1.0
            self.display_pixmap = self.pixmap
            
        self.image_label.setPixmap(self.display_pixmap)
        self.image_label.setFixedSize(self.display_pixmap.size())
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        btn_layout = QHBoxLayout()
        self.info_label = QLabel("Tip: Click and drag over the image to select the crop area.")
        self.info_label.setStyleSheet("font-size: 14px; font-style: italic;")
        btn_layout.addWidget(self.info_label)
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)
        
        crop_btn = QPushButton("✂️ Crop && Apply")
        crop_btn.clicked.connect(self.crop)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(crop_btn)
        layout.addLayout(btn_layout)

    def crop(self):
        rect = self.image_label.get_selection_rect()
        if not rect.isValid() or rect.width() == 0 or rect.height() == 0:
            QMessageBox.warning(self, "Select Area", "Please drag an area on the image to crop.", QMessageBox.StandardButton.Ok)
            return
            
        real_rect = QRect(
            int(rect.x() * self.scale_factor_w),
            int(rect.y() * self.scale_factor_h),
            int(rect.width() * self.scale_factor_w),
            int(rect.height() * self.scale_factor_h)
        )
        
        try:
            img = Image.open(self.image_path)
            cropped_img = img.crop((real_rect.left(), real_rect.top(), real_rect.right(), real_rect.bottom()))
            
            fd, temp_path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            
            cropped_img.save(temp_path)
            self.cropped_path = temp_path
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to crop:\n{str(e)}", QMessageBox.StandardButton.Ok)


class ImageContainer(QFrame):
    def __init__(self, parent_app, index):
        super().__init__()
        self.parent_app = parent_app
        self.index = index
        self.image_path = None
        self.is_selected = False
        
        self.setFixedSize(220, 260)
        self.setAcceptDrops(True)
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.image_label)
        
        self.page_label = QLabel(f"Page {self.index + 1}")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.page_label.setStyleSheet("color: #E94560; font-weight: bold; font-size: 14px; font-family: 'Segoe UI'; margin-top: 5px;")
        self.page_label.setFixedHeight(25)
        self.layout.addWidget(self.page_label)
        
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.page_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.update_appearance()

    def update_appearance(self):
        self.page_label.setText(f"Page {self.index + 1}")
        if self.image_path:
            border_col = "#FFD700" if getattr(self, 'is_selected', False) else "#E94560"
            bg_col = "#123e72" if getattr(self, 'is_selected', False) else "#0F3460"
            
            self.setStyleSheet(f"""
                ImageContainer {{
                    background-color: {bg_col};
                    border: 3px solid {border_col};
                    border-radius: 12px;
                }}
            """)
            pixmap = QPixmap(self.image_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.image_label.setPixmap(pixmap)
            else:
                self.image_label.setText("Invalid Image")
                self.image_label.setPixmap(QPixmap())
                self.image_label.setStyleSheet("color: #FFFFFF;")
        else:
            self.setStyleSheet("""
                ImageContainer {
                    background-color: #16213E;
                    border: 3px dashed #30475E;
                    border-radius: 12px;
                }
            """)
            self.image_label.clear()
            self.image_label.setText("Empty\nDrop Here")
            self.image_label.setStyleSheet("color: #556677; font-size: 16px; font-weight: bold;")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.image_path:
            if hasattr(self, 'drag_start_pos'):
                if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
                    self.is_selected = not getattr(self, 'is_selected', False)
                    self.update_appearance()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if not self.image_path:
            return
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return
        if not hasattr(self, 'drag_start_pos'):
            return
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
            
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(str(self.index))
        drag.setMimeData(mime_data)
        
        if self.image_label.pixmap():
            drag.setPixmap(self.image_label.pixmap().scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))
            drag.setHotSpot(QPoint(50, 50))
            
        drag.exec(Qt.DropAction.MoveAction)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event):
        source_index_str = event.mimeData().text()
        if source_index_str.isdigit():
            source_index = int(source_index_str)
            if source_index != self.index:
                self.parent_app.swap_containers(source_index, self.index)
                event.acceptProposedAction()


class ImageToPdfApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pro Document Converter - Dark Theme")
        self.resize(1150, 800)
        
        self.containers = []
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1A1A2E;
            }
            QLabel#title {
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 34px;
                font-weight: 800;
                color: #E94560;
                margin-bottom: 5px;
            }
            QPushButton {
                background-color: #0F3460;
                color: #FFFFFF;
                border-radius: 8px;
                padding: 12px 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                border: 1px solid #16213E;
            }
            QPushButton:hover {
                background-color: #1A4A87;
                border: 1px solid #1A4A87;
            }
            QPushButton:pressed {
                background-color: #0d284a;
            }
            QPushButton#convertBtn {
                background-color: #E94560;
                font-size: 16px;
                padding: 14px 35px;
            }
            QPushButton#convertBtn:hover {
                background-color: #FF5A76;
            }
            QPushButton#convertBtn:pressed {
                background-color: #CC3D54;
            }
            QPushButton#removeBtn {
                background-color: #B92B27;
            }
            QPushButton#removeBtn:hover {
                background-color: #D32F2F;
            }
            QPushButton#removeBtn:pressed {
                background-color: #8E0000;
            }
            QPushButton#cropBtn {
                background-color: #E27D60;
            }
            QPushButton#cropBtn:hover {
                background-color: #E8A87C;
            }
            QPushButton#cropBtn:pressed {
                background-color: #C38D9E;
            }
            QScrollArea {
                border: none;
                background-color: #1A1A2E;
            }
            QWidget#gridWidget {
                background-color: #1A1A2E;
            }
            QScrollBar:vertical {
                border: none;
                background: #1A1A2E;
                width: 14px;
                border-radius: 7px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #0F3460;
                min-height: 20px;
                border-radius: 7px;
            }
            QScrollBar::handle:vertical:hover {
                background: #E94560;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QTabWidget::pane {
                border: 2px solid #0F3460;
                border-radius: 8px;
                background-color: #1A1A2E;
            }
            QTabBar::tab {
                background: #0F3460;
                color: #A0A0A0;
                padding: 12px 30px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                font-family: 'Segoe UI';
                font-size: 15px;
                font-weight: bold;
                margin-right: 5px;
                border: 1px solid #0F3460;
            }
            QTabBar::tab:selected {
                background: #E94560;
                color: white;
                border: 1px solid #E94560;
            }
            QTabBar::tab:hover:!selected {
                background: #1A4A87;
                color: white;
            }
            QTextEdit {
                background-color: #FFFFFF;
                color: #000000;
                border: 2px dashed #30475E;
                border-radius: 12px;
                padding: 20px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 16px;
                line-height: 1.5;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Tabs Layout
        self.tabs = QTabWidget()
        self.tab_image = QWidget()
        self.tab_text = QWidget()
        
        self.tabs.addTab(self.tab_image, "🖼️ Image to PDF")
        self.tabs.addTab(self.tab_text, "📝 Text to PDF")
        main_layout.addWidget(self.tabs)
        
        self.setup_image_tab()
        self.setup_text_tab()

    def setup_image_tab(self):
        layout = QVBoxLayout(self.tab_image)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(20)

        title_label = QLabel("Image to PDF Converter")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        sub_title = QLabel("Fixed page layouts. Drag to swap. Click to select boxes.")
        sub_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_title.setStyleSheet("font-size: 15px; margin-bottom: 10px; color: #B0B0C0;")
        layout.addWidget(sub_title)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        
        self.grid_widget = QWidget()
        self.grid_widget.setObjectName("gridWidget")
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        
        self.scroll_area.setWidget(self.grid_widget)
        layout.addWidget(self.scroll_area, stretch=1)

        for i in range(20):
            self.add_new_container()

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)

        self.add_btn = QPushButton("📸 Add Images")
        self.add_btn.clicked.connect(self.add_images)
        
        self.crop_btn = QPushButton("✂️ Crop Selected")
        self.crop_btn.setObjectName("cropBtn")
        self.crop_btn.clicked.connect(self.crop_selected_image)
        
        self.remove_btn = QPushButton("🗑️ Remove Selected")
        self.remove_btn.setObjectName("removeBtn")
        self.remove_btn.clicked.connect(self.remove_images)
        
        self.clear_btn = QPushButton("❌ Clear All")
        self.clear_btn.setObjectName("removeBtn") 
        self.clear_btn.clicked.connect(self.clear_all_images)

        self.convert_btn = QPushButton("📑 Convert to PDF")
        self.convert_btn.setObjectName("convertBtn")
        self.convert_btn.clicked.connect(self.convert_to_pdf)

        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.crop_btn)
        btn_layout.addWidget(self.remove_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.convert_btn)

        layout.addLayout(btn_layout)
        
        self.status_label = QLabel("Ready. Pre-loaded with 20 empty pages.")
        self.status_label.setStyleSheet("color: #E94560; font-size: 13px; font-weight: bold; margin-top: 5px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def setup_text_tab(self):
        layout = QVBoxLayout(self.tab_text)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        title_label = QLabel("Text to PDF Converter")
        title_label.setObjectName("title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        sub_title = QLabel("Type or paste your text below to generate a formatted PDF document.")
        sub_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_title.setStyleSheet("font-size: 15px; margin-bottom: 10px; color: #B0B0C0;")
        layout.addWidget(sub_title)

        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setPlaceholderText("Paste your rich text here (e.g., from Word) to preserve formatting...")
        layout.addWidget(self.text_edit, stretch=1)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.clear_text_btn = QPushButton("❌ Clear Text")
        self.clear_text_btn.setObjectName("removeBtn")
        self.clear_text_btn.clicked.connect(self.text_edit.clear)
        
        self.convert_text_btn = QPushButton("📑 Save as PDF")
        self.convert_text_btn.setObjectName("convertBtn")
        self.convert_text_btn.clicked.connect(self.convert_text_to_pdf)

        btn_layout.addWidget(self.clear_text_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.convert_text_btn)
        
        layout.addLayout(btn_layout)

        self.text_status_label = QLabel("Ready. Enter some text.")
        self.text_status_label.setStyleSheet("color: #E94560; font-size: 13px; font-weight: bold; margin-top: 5px;")
        self.text_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.text_status_label)

    # -------- IMAGE TAB METHODS --------
    def add_new_container(self):
        index = len(self.containers)
        container = ImageContainer(self, index)
        self.containers.append(container)
        
        cols = 4
        row = index // cols
        col = index % cols
        self.grid_layout.addWidget(container, row, col)

    def swap_containers(self, idx1, idx2):
        c1 = self.containers[idx1]
        c2 = self.containers[idx2]
        
        path_temp = c1.image_path
        c1.image_path = c2.image_path
        c2.image_path = path_temp
        
        sel_temp = getattr(c1, 'is_selected', False)
        c1.is_selected = getattr(c2, 'is_selected', False)
        c2.is_selected = sel_temp
        
        c1.update_appearance()
        c2.update_appearance()
        
        self.status_label.setText(f"Swapped Page {idx1 + 1} with Page {idx2 + 1}")

    def add_images(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, 
            "Select Images", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.webp)"
        )
        if not file_paths:
            return
            
        path_idx = 0
        
        for c in self.containers:
            if c.image_path is None:
                c.image_path = file_paths[path_idx]
                c.is_selected = False
                c.update_appearance()
                path_idx += 1
                if path_idx >= len(file_paths):
                    break
                    
        while path_idx < len(file_paths):
            self.add_new_container()
            c = self.containers[-1]
            c.image_path = file_paths[path_idx]
            c.is_selected = False
            c.update_appearance()
            path_idx += 1
            
        while len(self.containers) % 4 != 0:
            self.add_new_container()
            
        self.status_label.setText(f"Added {len(file_paths)} image(s) to the pages.")

    def crop_selected_image(self):
        selected_containers = [c for c in self.containers if getattr(c, 'is_selected', False) and c.image_path is not None]
        
        if len(selected_containers) == 0:
            QMessageBox.warning(self, "No Selection", "Please click on a page to select it for cropping.", QMessageBox.StandardButton.Ok)
            return
        elif len(selected_containers) > 1:
            QMessageBox.warning(self, "Multiple Selection", "Please select only one page to crop at a time.", QMessageBox.StandardButton.Ok)
            return
            
        container = selected_containers[0]
        
        dialog = CropDialog(container.image_path, self)
        if dialog.exec():
            if dialog.cropped_path:
                container.image_path = dialog.cropped_path
                container.update_appearance()
                self.status_label.setText(f"Cropped image on Page {container.index + 1}.")

    def remove_images(self):
        removed = 0
        for c in self.containers:
            if getattr(c, 'is_selected', False) and c.image_path is not None:
                c.image_path = None
                c.is_selected = False
                c.update_appearance()
                removed += 1
        self.status_label.setText(f"Emptied {removed} selected page(s).")

    def clear_all_images(self):
        for c in self.containers:
            if c.image_path is not None:
                c.image_path = None
                c.is_selected = False
                c.update_appearance()
        self.status_label.setText("Cleared all pages.")

    def convert_to_pdf(self):
        image_paths = []
        for c in self.containers:
            if c.image_path:
                image_paths.append(c.image_path)
                
        if not image_paths:
            QMessageBox.warning(self, "No Images", "Please add some images to the pages first.", QMessageBox.StandardButton.Ok)
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "output.pdf", "PDF Files (*.pdf)")
        if not save_path:
            return

        try:
            self.status_label.setText("Converting to PDF, please wait...")
            QApplication.processEvents()

            images = []
            for path in image_paths:
                img = Image.open(path)
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                images.append(img)

            if images:
                images[0].save(save_path, save_all=True, append_images=images[1:], resolution=100.0)
            
            self.status_label.setText(f"Success! PDF saved to {os.path.basename(save_path)}")
            QMessageBox.information(self, "Success", f"PDF with {len(images)} pages saved successfully at:\n{save_path}", QMessageBox.StandardButton.Ok)

        except Exception as e:
            self.status_label.setText("Error occurred during conversion.")
            QMessageBox.critical(self, "Error", f"Failed to convert to PDF:\n{str(e)}", QMessageBox.StandardButton.Ok)

    # -------- TEXT TAB METHODS --------
    def convert_text_to_pdf(self):
        if self.text_edit.document().isEmpty():
            QMessageBox.warning(self, "No Text", "Please enter some text to convert to PDF.", QMessageBox.StandardButton.Ok)
            return

        save_path, _ = QFileDialog.getSaveFileName(self, "Save PDF", "text_output.pdf", "PDF Files (*.pdf)")
        if not save_path:
            return

        try:
            self.text_status_label.setText("Converting Rich Text to PDF...")
            QApplication.processEvents()

            printer = QPrinter(QPrinter.PrinterMode.ScreenResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            printer.setOutputFileName(save_path)
            
            self.text_edit.document().print(printer)
            
            self.text_status_label.setText(f"Success! Saved to {os.path.basename(save_path)}")
            QMessageBox.information(self, "Success", f"Text successfully converted and saved to PDF at:\n{save_path}", QMessageBox.StandardButton.Ok)
            
        except Exception as e:
            self.text_status_label.setText("Error occurred during text conversion.")
            QMessageBox.critical(self, "Error", f"Failed to convert text to PDF:\n{str(e)}", QMessageBox.StandardButton.Ok)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setWindowIcon(QIcon(resource_path("icon.png")))
    
    window = ImageToPdfApp()
    window.show()
    sys.exit(app.exec())
