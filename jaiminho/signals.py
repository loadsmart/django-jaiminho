from django import dispatch

event_published = dispatch.Signal()
event_failed_to_publish = dispatch.Signal()
event_published_by_events_relay = dispatch.Signal()
event_failed_to_publish_by_events_relay = dispatch.Signal()
