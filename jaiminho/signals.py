from django import dispatch

event_published = dispatch.Signal()
event_failed_to_publish = dispatch.Signal()
