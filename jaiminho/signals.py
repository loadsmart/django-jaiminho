from django import dispatch

event_published = dispatch.Signal()
event_failed_to_publish = dispatch.Signal()
event_published_by_events_relay = dispatch.Signal()
event_failed_to_publish_by_events_relay = dispatch.Signal()


def get_event_payload(args):
    try:
        iter(args)
        return args[0]
    except (IndexError, TypeError):
        return {}
