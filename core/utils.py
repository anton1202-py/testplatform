import logging
from functools import wraps


def sort_products_key(sort_by, product: dict) -> str:
    if "market" in sort_by:
        if not product["other_marketplace"]:
            return ""

        return product["other_marketplace"]["name"]

    if not product["moy_sklad"]:
        return ""

    return product["moy_sklad"]["name"]


def skip_if_running(func):
    task_name = f"{func.__module__}.{func.__name__}"

    @wraps(func)
    def wrapped(self, *args, **kwargs):
        workers = self.app.control.inspect().active()

        for worker, tasks in workers.items():
            for task in tasks:
                if (
                    task_name == task["name"]
                    and tuple(args) == tuple(task["args"])
                    and kwargs == task["kwargs"]
                    and self.request.id != task["id"]
                ):
                    logging.warning(f"task {task_name} ({args}, {kwargs}) is running on {worker}, skipping")

                    return None

        return func(self, *args, **kwargs)

    return wrapped
