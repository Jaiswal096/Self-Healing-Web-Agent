"""
setup.py — Package installation configuration for Self-Healing Web Agent.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

with open("requirements.txt", "r", encoding="utf-8") as f:
    requirements = [
        line.strip()
        for line in f
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="self-healing-web-agent",
    version="0.1.0",
    author="Jaiswal096",
    description="Autonomous self-healing web scraping framework powered by Gemini Vision AI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Jaiswal096/Self-Healing-Web-Agent",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "self-healing-agent=main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Browsers",
        "Topic :: Software Development :: Testing",
    ],
    keywords="web-scraping self-healing playwright ai gemini automation",
)
