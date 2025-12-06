"""
Setup script for RetroArch Toolkit
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="retroarch-playlist-tools",
    version="1.0.0",
    author="RetroArch Toolkit Contributors",
    description="A tool for managing RetroArch playlists and ROM collections",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/puterjam/retroarch-playlist-tools",
    packages=find_packages(),
    package_data={
        "": ["config/*.json", "config/libretro-core-info/*.info"],
    },
    include_package_data=True,
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Games/Entertainment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "prompt-toolkit>=3.0.0",  # For interactive matcher
    ],
    extras_require={
        "7z": ["py7zr>=0.20.0"],  # For 7z file support
    },
    entry_points={
        "console_scripts": [
            "rap=main:main",
        ],
    },
    py_modules=["main"],  # Include main.py as a top-level module
)
