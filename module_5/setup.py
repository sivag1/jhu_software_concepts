"""Setup script for module_5 - Grad School Cafe Data Analysis."""

from setuptools import setup, find_packages

setup(
    name="module_5",
    version="1.0.0",
    description="Grad School Cafe Data Analysis - Module 5 (Software Assurance)",
    author="Siva Govindarajan",
    packages=find_packages(),
    install_requires=[
        "psycopg[binary]",
        "python-dotenv",
        "Flask>=2.3,<4",
    ],
    python_requires=">=3.10",
)
