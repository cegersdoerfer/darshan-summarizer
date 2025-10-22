"""
Setup script for darshan-log-summarizer package.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="darshan-log-summarizer",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered analysis and summarization of Darshan I/O profiling logs",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/darshan-log-summarizer",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: System :: Monitoring",
        "Topic :: Scientific/Engineering",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "darshan-summarizer=darshan_summarizer.main:main",
        ],
    },
)

