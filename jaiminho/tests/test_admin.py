from jaiminho.admin import EventAdmin
from jaiminho.models import Event
from django.contrib.admin import AdminSite


class TestEventAdmin:
    def test_has_add_permission(self):
        assert EventAdmin(Event, AdminSite).has_add_permission(None) is False

    def test_fields(self):
        assert EventAdmin.fields == (
            "id",
            "signature",
            "sent_at",
            "stream",
            "strategy",
            "created_at",
        )

    def test_readonly_fields(self):
        assert EventAdmin.readonly_fields == (
            "id",
            "message",
            "function",
            "kwargs",
            "signature",
            "sent_at",
            "stream",
            "strategy",
            "created_at",
        )

    def test_list_display(self):
        assert EventAdmin.list_display == (
            "id",
            "signature",
            "sent_at",
            "stream",
            "strategy",
            "created_at",
        )
