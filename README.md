# jaiminho

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![codecov](https://codecov.io/gh/loadsmart/jaiminho/branch/master/graph/badge.svg?token=gf7apAoU7A)](https://codecov.io/gh/loadsmart/jaiminho)

Python library which implement outbox and other message resilence patterns.

![Jaiminho](https://github.com/loadsmart/jaiminho/blob/master/docs/images/jaiminho.jpg?raw=true)

## Installation

Install it from our private PyPI repository. Make sure you have the `PIP_EXTRA_INDEX_URL` environment variable correctly configured.

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
    }

```



### Configuration options

- PERSIST_ALL_EVENTS - Saves all events and not only the ones that fail, default is False
- DEFAULT_ENCODER - Default Encoder for the payload (overwritable in the function call)

Detailed documentation is available at https://docs.loadsmart.io/jaiminho/latest/index.html

### Signals

Jaiminho triggers the following Django signals:

| Signal                  | Descriptiopn                                                                   |
|-------------------------|--------------------------------------------------------------------------------|
| event_published         | Triggered when an event is sent successfully                                   |
| event_failed_to_publish | Triggered when an event failed to be send and it's enqueue to the Outbox table |


### How to collect metrics from Jaiminho?

You could use the Django signals triggered by Jaiminho to collect metrics. 
Consider the following code as example:

````python
from django.dispatch import receiver

@receiver(event_published)
def on_event_sent(sender, event_payload, **kwargs):
    metrics.count(f"event_sent_successfully {event_payload.get('type')}")

@receiver(event_failed_to_publish)
def on_event_send_error(sender, event_payload, **kwargs):
    metrics.count(f"event_failed {event_payload.get('type')}")

````

### How to clean older events

You can use Jaiminho's [EventCleanerCommand](https://github.com/loadsmart/jaiminho/tree/master/jaiminho/management/event_cleaner.py) in order to do that. It will query for all events that were sent before a given time interval (e.g. last 14 days) and will delete them from the outbox table.

The default time interval is `14 days`. You can use the `TIME_TO_DELETE` setting to change it. It should be added to `JAIMINHO_CONFIG` and must be a valid [timedelta](https://docs.python.org/3/library/datetime.html#timedelta-objects).


## Development

Create a virtualenv

```bash
virtualenv venv
pip install -r requirements-dev.txt
tox -e py39
```


## License

This project is licensed under Private.
