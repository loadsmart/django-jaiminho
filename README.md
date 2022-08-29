# jaiminho

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)
[![codecov](https://codecov.io/gh/loadsmart/jaiminho/branch/master/graph/badge.svg?token=gf7apAoU7A)](https://codecov.io/gh/loadsmart/jaiminho)

A broker agnostic implementation of outbox and other message resilience patterns for django apps. 

![Jaiminho](https://github.com/loadsmart/jaiminho/blob/master/docs/images/jaiminho.jpg?raw=true)

## Installation

Install it from our private PyPI repository. Make sure you have the `PIP_EXTRA_INDEX_URL` environment variable correctly configured.

```sh
python -m pip install jaiminho
```

Add `jaiminho` in the `INSTALLED_APPS` section of your Django app

## Usage

We provide a @save_to_outbox decorator that you can use in the functions responsible to communicate with external systems (brokers, external APIs, etc). 
Behind the scenes, jaiminho can store those functions calls in a local table in the same database within the current transaction. It can relay those functions calls after a success commit and/or a separate relay command, fixing the dual writes issue.

```python
from jaiminho.send import save_to_outbox

@save_to_outbox
def any_external_call(**kwargs):
    # do something
    return
```

Configure jaiminho options in Django settings.py:
```python

# JAIMINHO

JAIMINHO_CONFIG = {
    "PERSIST_ALL_EVENTS": False,
    "DELETE_AFTER_SEND": True,
    "DEFAULT_ENCODER": DjangoJSONEncoder,
    "PUBLISH_STRATEGY: "publish-on-commit"
    }

```

### Configuration options

- PUBLISH_STRATEGY - Which strategy use to publish events (publish-on-commit, keep-order)
- PERSIST_ALL_EVENTS - Saves all events and not only the ones that fail, default is False. Only applicable for `"PUBLISH_STRATEGY": "publish-on-commit"` since all events needs to be stored on keep-order strategy. 
- DELETE_AFTER_SEND - Delete the event from the outbox table immediately after a successful send
- DEFAULT_ENCODER - Default Encoder for the payload (overwritable in the function call)

### Strategies

#### Keep Order
This strategy is similar to transactional outbox [described by Chris Richardson](https://microservices.io/patterns/data/transactional-outbox.html). The decorated function intercepts the function call and saves it on local DB to be executed later. A separate command relayer will keep polling local DB and executing those functions in the same order it was stored. 
Be carefully with this approach, **if any execution fails, the relayer will get stuck**. Otherwise, would not possible to guarantee delivery order.  

#### Publish on commit

This strategy will always execute the decorated function after current transaction commit. With this approach, we don't depend on a relayer (separate process / cronjob) to execute the decorated function and deliver the message. Failed items will only be executed
through relayer. Despite we can decrease the delay to execute the decorated function with this approach, **we cannot guarantee delivery order**.

Detailed documentation is available at https://docs.loadsmart.io/jaiminho/latest/index.html

### Relay Command
We already provide a command to relay items from DB, [EventRelayCommand](https://github.com/loadsmart/jaiminho/tree/master/jaiminho/management/event_relay.py). The way you should configure depends on the strategy you choose. 
For example, on **Publish on Commit Strategy** you can configure a cronjob to run every a couple of minutes since only failed items are published by the command relay. If you are using **Keep Order Strategy**, you should run relay command in loop mode as all items will be published by the command, e.g `call_command(events_relay.Command(), run_in_loop=True, loop_interval=0.1)`.  



### Signals

Jaiminho triggers the following Django signals:

| Signal                  | Description                                                                   |
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

You can use Jaiminho's [EventCleanerCommand](https://github.com/loadsmart/jaiminho/tree/master/jaiminho/management/event_cleaner.py) in order to do that. It will query for all events that were sent before a given time interval (e.g. last 7 days) and will delete them from the outbox table.

The default time interval is `7 days`. You can use the `TIME_TO_DELETE` setting to change it. It should be added to `JAIMINHO_CONFIG` and must be a valid [timedelta](https://docs.python.org/3/library/datetime.html#timedelta-objects).


## Development

Create a virtualenv

```bash
virtualenv venv
pip install -r requirements-dev.txt
tox -e py39
```


## License

This project is licensed under Private.
