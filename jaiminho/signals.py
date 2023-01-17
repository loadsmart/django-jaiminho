from django import dispatch

event_published = dispatch.Signal()
event_failed_to_publish = dispatch.Signal()
event_published_by_events_relay = dispatch.Signal()
event_failed_to_publish_by_events_relay = dispatch.Signal()


def get_event_payload(args):
    try:
        if isinstance(args, tuple):
            return args[0]
        return {}
    except IndexError:
        return {}
