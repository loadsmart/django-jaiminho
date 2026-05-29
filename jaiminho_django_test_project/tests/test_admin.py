from django.urls import reverse

from jaiminho.tests.factories import EventFactory


def test_events_changelist_is_accessible(admin_client):
    url = reverse("admin:jaiminho_event_changelist")
    response = admin_client.get(url)

    assert response.status_code == 200


def test_events_are_not_addable(admin_client):
    url = reverse("admin:jaiminho_event_add")
    response = admin_client.get(url)

    assert response.status_code == 403


def test_events_can_be_edited(admin_client):
    event = EventFactory.create()
    url = reverse("admin:jaiminho_event_change", kwargs={"object_id": event.pk})
    response = admin_client.get(url)

    assert response.status_code == 200
