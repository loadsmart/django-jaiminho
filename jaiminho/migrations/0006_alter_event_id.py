# Generated by Django 3.2.5 on 2023-06-12 13:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jaiminho", "0005_event_strategy"),
    ]

    operations = [
        migrations.AlterField(
            model_name="event",
            name="id",
            field=models.BigAutoField(primary_key=True, serialize=False),
        ),
    ]