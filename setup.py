"""Setup configuration for gh-graveyard package."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="gh-graveyard",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A tool to identify unused API endpoints from OpenAPI specs and logs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/api-graveyard",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "pyyaml>=6.0",
        "click>=8.0",
        "python-dateutil>=2.8.0",
        "GitPython>=3.1.0",
        "PyGithub>=2.1.0",
    ],
    entry_points={
        "console_scripts": [
            "gh-graveyard=detector.cli:cli",
        ],
    },
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
)
