# jaiminho

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![codecov](https://codecov.io/gh/loadsmart/jaiminho/branch/master/graph/badge.svg?token=gf7apAoU7A)](https://codecov.io/gh/loadsmart/jaiminho)

Python library which implement outbox and other message resilence patterns.

![Jaiminho](https://github.com/loadsmart/jaiminho/blob/master/docs/images/jaiminho.jpg?raw=true)

## Installation


```sh
python -m pip install jaiminho
```

Add `jaiminho` in the `INSTALLED_APPS` section of your Django app

## Usage

Configure jaiminho options in Django settings.py:
```python

# JAIMINHO

JAIMINHO_CONFIG = {
    "PERSIST_ALL_EVENTS": False
    "SEND_EVENT_FUNCTION": "jaiminho_django_project.send.send",
}

```
### Configuration options

- PERSIST_ALL_EVENTS - Saves all events and not only the ones that fail
- SEND_EVENT_FUNCTION - Function with foo(payload:dict) signature that will send the event and raise an exception if failed.


## Development

Create a virtualenv

```bash
virtualenv venv
pip install -r requirements-dev.txt
tox -e py39
```


## License

This project is licensed under Private.
