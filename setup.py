import os
import sys

# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open

from setuptools import setup, find_packages

here = os.path.abspath(os.path.dirname(__file__))

# Get the long description from the README file
with open(os.path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()


# The placeholder is to be able to install it as editable
version = os.getenv("CIRCLE_TAG", os.getenv("CIRCLE_SHA1")) or "0.0.0"


setup(
    name="jaiminho",
    version="0.1.0",
    description="Python library generated using cookiecutter template",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/loadsmart/jaiminho",
    author="Loadsmart",
    author_email="engineering@loadsmart.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    packages=find_packages(exclude=["docs", "tests", "jaiminho_django_project"]),
    python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*, !=3.4.*, !=3.5.*, <4",
    install_requires=["Django"],
    project_urls={
        "Documentation": "https://docs.loadsmart.io/jaiminho",
        "Source": "https://github.com/loadsmart/jaiminho",
    },
)
