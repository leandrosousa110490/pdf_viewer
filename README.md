# PDF Editor

A feature-rich PDF viewer and editor built with Python, PySide6, and PyMuPDF.

## Features

- **PDF Viewing**: Open and view PDF files with smooth navigation between pages
- **Annotation Tools**: Draw, highlight, and annotate PDF documents
- **Text Extraction**: Extract text from PDF pages
- **Modern UI**: Clean, dark-themed interface with intuitive controls
- **File Explorer**: Built-in file browser for quick access to your PDF files
- **Zoom Controls**: Easily zoom in and out of documents

## Installation

1. Ensure you have Python 3.8+ installed
2. Clone this repository
3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Run the application:

```bash
python pdf_app.py
```

### Controls

- **Open**: Open a PDF file from your system
- **Navigation**: Use the Previous/Next buttons or the page selector to navigate between pages
- **Zoom**: Use the zoom slider or zoom in/out buttons to adjust the view
- **Annotations**:
  - **Select**: Choose this tool to navigate without drawing
  - **Highlight**: Highlight text or areas with a semi-transparent color
  - **Pen**: Draw freehand on the document
  - **Eraser**: (Coming soon) Remove annotations
  - **Text**: (Coming soon) Add text annotations
- **Extract Text**: Extract and view the text content of the current page
- **Save**: Save the current document with annotations

## GitHub Setup

To upload this project to GitHub:

1. Create a new repository on GitHub (without initializing it with a README, license, or .gitignore)
2. Initialize the local repository and make the first commit:

```bash
git init
git add .
git commit -m "Initial commit"
```

3. Link your local repository to the GitHub repository:

```bash
git remote add origin https://github.com/yourusername/pdf-viewer.git
git branch -M main
git push -u origin main
```

4. Your code should now be available on GitHub!

## Dependencies

- PySide6: Modern UI framework
- PyMuPDF: PDF manipulation library
- Pillow: Image processing

## Future Enhancements

- Text annotation tool implementation
- Eraser functionality for removing annotations
- PDF form filling capabilities
- Document metadata editing
- Text search functionality
- Annotation management panel

## License

MIT 