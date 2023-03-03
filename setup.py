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
    name="django-jaiminho",
    version=version,
    description="A broker agnostic implementation of outbox and other message resilience patterns for Django apps",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/loadsmart/django-jaiminho",
    author="Loadsmart",
    author_email="jaiminho@loadsmart.com",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: Other/Proprietary License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    packages=find_packages(exclude=["docs", "tests", "jaiminho_django_test_project"]),
    python_requires=">=3.7, <4",
    install_requires=["Django", "sentry_sdk", "dill==0.3.6"],
    project_urls={
        "Documentation": "https://github.com/loadsmart/django-jaiminho/blob/master/README.md",
        "Source": "https://github.com/loadsmart/django-jaiminho",
        "Changelog": "https://github.com/loadsmart/django-jaiminho/blob/master/CHANGELOG.md",
    },
)
