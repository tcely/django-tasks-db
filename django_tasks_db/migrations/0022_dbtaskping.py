from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("django_tasks_database", "0021_conditional_partial_index_ordering"),
    ]
    operations = [
        migrations.CreateModel(
            name="DBTaskPing",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "worker_id",
                    models.CharField(max_length=256, verbose_name="worker id"),
                ),
                (
                    "queue_name",
                    models.CharField(
                        default="default", max_length=32, verbose_name="queue name"
                    ),
                ),
                (
                    "backend_name",
                    models.CharField(max_length=32, verbose_name="backend name"),
                ),
                ("task_id", models.UUIDField()),
                ("pongs", models.IntegerField(default=0, verbose_name="responses")),
            ],
            options={
                "verbose_name": "DB Worker Ping",
                "verbose_name_plural": "DB Worker Pings",
                "indexes": [
                    models.Index(
                        fields=["task_id", "queue_name", "backend_name"],
                        name="django_task_task_id_8a8162_idx",
                    ),
                    models.Index(
                        fields=["worker_id", "queue_name", "backend_name"],
                        name="django_task_worker__3a4ddb_idx",
                    ),
                ],
                "unique_together": {
                    ("worker_id", "task_id", "queue_name", "backend_name")
                },
            },
        ),
    ]
