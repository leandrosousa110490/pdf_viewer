from setuptools import setup

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="pdf-viewer",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A feature-rich PDF viewer and editor with Excel/CSV/Parquet support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/pdf-viewer",
    py_modules=["pdf_app"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "pdf-viewer=pdf_app:main",
        ],
    },
) 