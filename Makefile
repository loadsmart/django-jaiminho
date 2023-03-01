clean: clean-build clean-pyc clean-test

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

install:
	python -m venv .venv
	./.venv/bin/python -m pip install -r requirements-dev.txt

fmt:
	black .

test:
	pytest .

test-all:
	tox

dist: clean
	python setup.py bdist_wheel --universal

release: dist
	pip install twine
	python -m twine upload --non-interactive --username __token__ --password ${PYPI_TOKEN} dist/*
