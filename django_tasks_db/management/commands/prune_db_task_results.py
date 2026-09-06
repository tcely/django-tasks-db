import logging
from argparse import ArgumentParser, ArgumentTypeError
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from django_tasks_db.backend import DatabaseBackend
from django_tasks_db.compat import (
    DEFAULT_TASK_BACKEND_ALIAS,
    DEFAULT_TASK_QUEUE_NAME,
    InvalidTaskBackend,
    TaskResultStatus,
    task_backends,
)
from django_tasks_db.models import DBTaskResult

logger = logging.getLogger("django_tasks_db.prune_db_task_results")


def valid_backend_name(val: str) -> DatabaseBackend:
    try:
        backend = task_backends[val]
    except InvalidTaskBackend as e:
        # TODO: update tests for the changed output
        # msg = str(e).replace(" connection '", " backend '", 1)
        msg = str(e)
        raise ArgumentTypeError(msg) from e
    if not isinstance(backend, DatabaseBackend):
        raise ArgumentTypeError(f"Backend '{val}' is not a database backend")
    return backend


def valid_positive_int(val: str) -> int:
    num = int(val)
    if num < 0:
        raise ArgumentTypeError("Must be greater than zero")
    return num


class Command(BaseCommand):
    help = "Prune finished database task results"

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "--backend",
            default=DEFAULT_TASK_BACKEND_ALIAS,
            type=valid_backend_name,
            dest="backend",
            help="The backend to operate on (default: %(default)r)",
        )
        parser.add_argument(
            "--queue-name",
            default=DEFAULT_TASK_QUEUE_NAME,
            type=str,
            help="The queues to process. Separate multiple with a comma. To process all queues, use '*' (default: %(default)r)",
        )
        parser.add_argument(
            "--min-age-days",
            default=14,
            type=valid_positive_int,
            help="The minimum age (in days) of a finished task result to be pruned (default: %(default)r)",
        )
        parser.add_argument(
            "--failed-min-age-days",
            type=valid_positive_int,
            help="The minimum age (in days) of a failed task result to be pruned (default: min-age-days)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Don't delete the task results, just show how many would be deleted",
        )

    def configure_logging(self, verbosity: int) -> None:
        if verbosity == 0:
            logger.setLevel(logging.WARNING)
        elif verbosity == 1:
            logger.setLevel(logging.INFO)
        else:
            logger.setLevel(logging.DEBUG)

        # If no handler is configured, the logs won't show,
        # regardless of the set level.
        if not logger.hasHandlers():
            logger.addHandler(logging.StreamHandler(self.stdout))

    def handle(
        self,
        *,
        verbosity: int,
        backend: DatabaseBackend,
        min_age_days: int,
        failed_min_age_days: int | None,
        queue_name: str,
        dry_run: bool,
        **options: dict,
    ) -> None:
        self.configure_logging(verbosity)

        # set-up all the ages from the same version of now
        now_dt = timezone.now()
        min_age = now_dt - timedelta(days=min_age_days)
        failed_min_age = (
            min_age
            if failed_min_age_days is None
            else (
                now_dt - timedelta(days=failed_min_age_days)
            )
        )

        results = DBTaskResult.objects.finished().filter(backend_name=backend.alias)

        # set-up queue names without "*" included
        queue_names = set(queue_name.split(","))
        all_queues = "*" in queue_names
        queue_names.discard("*")
        if not all_queues:
            results = results.filter(queue_name__in=queue_names)

        if failed_min_age_days is None:
            results = results.filter(
                status__in={TaskResultStatus.SUCCESSFUL, TaskResultStatus.FAILED},
                finished_at__lte=min_age,
            )
        else:
            results = results.filter(
                Q(status=TaskResultStatus.SUCCESSFUL, finished_at__lte=min_age)
                | Q(status=TaskResultStatus.FAILED, finished_at__lte=failed_min_age)
            )

        if dry_run:
            logger.info("Would delete %d task result(s)", results.count())
        else:
            deleted, _ = results.delete()
            logger.info("Deleted %d task result(s)", deleted)
