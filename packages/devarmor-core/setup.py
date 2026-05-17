"""Setup script for devarmor-core."""

from setuptools import find_packages, setup

setup(
    name="devarmor-core",
    version="0.1.0",
    description="DevArmor Core - Skill Governance Platform",
    author="Craig Hoad",
    author_email="craig@craighoad.com",
    url="https://github.com/rhyscraig/python-packages",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        "pydantic>=1.9.0,<3.0.0",
        "pyyaml>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0",
            "black>=22.0",
            "ruff>=0.1.0",
            "mypy>=0.990",
            "bandit>=1.7.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries",
    ],
)
