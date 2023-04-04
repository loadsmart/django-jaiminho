# jaiminho

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/python/black)

A broker agnostic implementation of the outbox and other message resilience patterns for Django apps. 

![Jaiminho](https://github.com/loadsmart/django-jaiminho/blob/master/assets/jaiminho.jpg?raw=true)

## Installation


```sh
python -m pip install jaiminho
```

Add `jaiminho` to the `INSTALLED_APPS` section of your Django app

## Getting Started

To integrate jaiminho with your project, you just need to do 3 steps:

### 1 - Decorate your functions with save_to_outbox_decorator
```python
from jaiminho.send import save_to_outbox

@save_to_outbox
def any_external_call(**kwargs):
    # do something
    return
```

### 2 - Configure jaiminho options in Django settings.py:
```python

# JAIMINHO

JAIMINHO_CONFIG = {
    "PERSIST_ALL_EVENTS": False,
    "DELETE_AFTER_SEND": True,
    "DEFAULT_ENCODER": DjangoJSONEncoder,
    "PUBLISH_STRATEGY: "publish-on-commit"
}

```

### 3 - Run the relay events command

```
python manage.py events_relay --run-in-loop --loop-interval 1

```

If you don't use --run-in-loop option, the relay command will run only 1 time. This is useful in case you want to configure it as a cronjob.


## Details

Jaiminho @save_on_commit decorator will intercept decorated function and persist it in a database table in the same transaction that is active in the decorated function context. The event relay command, is a separated process that fetches the rows from this table and execute the functions. When an outage happens, the event relay command will keep retrying until it succeeds. This way, eventual consistency is ensured by design.

### Configuration options

- `PUBLISH_STRATEGY` - Strategy used to publish events (publish-on-commit, keep-order)
- `PERSIST_ALL_EVENTS` - Saves all events and not only the ones that fail, default is `False`. Only applicable for `{ "PUBLISH_STRATEGY": "publish-on-commit" }` since all events needs to be stored on keep-order strategy. 
- `DELETE_AFTER_SEND` - Delete the event from the outbox table immediately, after a successful send
- `DEFAULT_ENCODER` - Default Encoder for the payload (overwritable in the function call)

### Strategies

#### Keep Order
This strategy is similar to transactional outbox [described by Chris Richardson](https://microservices.io/patterns/data/transactional-outbox.html). The decorated function intercepts the function call and saves it on the local DB to be executed later. A separate command relayer will keep polling local DB and executing those functions in the same order it was stored. 
Be carefully with this approach, **if any execution fails, the relayer will get stuck** as it would not be possible to guarantee delivery order.  

#### Publish on commit

This strategy will always execute the decorated function after current transaction commit. With this approach, we don't depend on a relayer (separate process / cronjob) to execute the decorated function and deliver the message. Failed items will only be retried
through relayer. Although this solution has a better performance as only failed items is delivered by the relay command, **we cannot guarantee delivery order**.


### Relay Command
We already provide a command to relay items from DB, [EventRelayCommand](https://github.com/loadsmart/django-jaiminho/blob/master/jaiminho/management/commands/events_relay.py). The way you should configure depends on the strategy you choose. 
For example, on **Publish on Commit Strategy** you can configure a cronjob to run every a couple of minutes since only failed items are published by the command relay. If you are using **Keep Order Strategy**, you should run relay command in loop mode as all items will be published by the command, e.g `call_command(events_relay.Command(), run_in_loop=True, loop_interval=0.1)`.  


### How to clean older events

You can use Jaiminho's [EventCleanerCommand](https://github.com/loadsmart/django-jaiminho/blob/master/jaiminho/management/commands/event_cleaner.py) in order to do that. It will query for all events that were sent before a given time interval (e.g. last 7 days) and will delete them from the outbox table.

The default time interval is `7 days`. You can use the `TIME_TO_DELETE` setting to change it. It should be added to `JAIMINHO_CONFIG` and must be a valid [timedelta](https://docs.python.org/3/library/datetime.html#timedelta-objects).

### Relay per stream and Overwrite publish strategy

Different streams can have different requirements. You can save separate events per streams by using the `@save_to_outbox_stream` decorator:

````python
@save_to_outbox_stream("my-stream")
def any_external_call(payload, **kwargs):
    # do something
    pass
````

you can also overwrite publish strategy configure on settings:

````python
@save_to_outbox_stream("my-stream", PublishStrategyType.KEEP_ORDER)
def any_external_call(payload, **kwargs):
    # do something
    pass
````

And then, run relay command with stream filter option
````shell
python manage.py relay_event True 0.1 my-stream
````

In the example above, `True` is the option for run_in_loop; `0.1` for loop_interval; and `my_stream` is the name of the stream.

### Signals

Jaiminho triggers the following Django signals:

| Signal                  | Description                                                                     |
|-------------------------|---------------------------------------------------------------------------------|
| event_published         | Triggered when an event is sent successfully                                    |
| event_failed_to_publish | Triggered when an event is not sent, being added to the Outbox table queue      |


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

## Development

Create a virtualenv

```bash
virtualenv venv
pip install -r requirements-dev.txt
tox -e py39
```
## Collaboration

If you want to improve or suggest improvements, check our [CONTRIBUTING.md](https://github.com/loadsmart/django-jaiminho/blob/master/CONTRIBUTING.md) file.


## License

This project is licensed under MIT License.

## Security

If you have any security concern or report feel free to reach out to security@loadsmart.com;
