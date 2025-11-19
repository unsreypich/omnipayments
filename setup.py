"""
OmniPayments
Framework-agnostic payment provider system for Python
Supports multiple payment providers: Stripe, Bakong KHQR, and more
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="omnipayments",
    version="1.0.0",
    author="SMEAN Team",
    author_email="dev@smean.ai",
    description="Framework-agnostic multi-provider payment processing for Python (Django, Flask, FastAPI)",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/SMEAN-AI/omnipayments",
    packages=find_packages(exclude=["tests*", "docs*", "examples*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial :: Point-Of-Sale",
        "Framework :: Django",
        "Framework :: Flask",
        "Framework :: FastAPI",
    ],
    python_requires=">=3.10",
    install_requires=[
        "stripe>=5.0.0",
        "requests>=2.28.0",
        "Pillow>=10.0.0",
        "qrcode>=7.4.2",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "black>=23.0",
            "flake8>=6.0",
            "mypy>=1.0",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    keywords="payments stripe bakong khqr payment-gateway multi-provider django flask fastapi",
)
