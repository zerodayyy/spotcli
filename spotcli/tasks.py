import sys
from abc import ABC, abstractmethod
from collections import UserList
from collections.abc import Iterable
from typing import List, Optional, Union

import attr
import pexecute.thread
import rich.console

from spotcli.elastigroup import Elastigroup, ElastigroupProcess

console = rich.console.Console(highlight=False)

PARALLEL_THREADS = 32


class Alias(UserList):
    def __init__(self, name, targets):
        self.name = name
        self.targets = targets

    @property
    def data(self):
        return self.targets


class TargetList(UserList):
    def __init__(self, spot, aliases, targets):
        self.spot = spot
        self.aliases = aliases
        self.targets = targets

    @property
    def data(self):
        def reduce(array, result=[]):
            for item in array:
                if isinstance(item, str):
                    if item in self.aliases:
                        reduce(self.aliases[item], result)
                    else:
                        result.append(item)
                elif isinstance(item, Iterable):
                    reduce(item, result)
            return result

        if isinstance(self.targets, Iterable) and not isinstance(self.targets, str):
            targets = []
            for target in reduce(self.targets):
                targets.extend(Elastigroup.find(self.spot.client(), target))
            return targets
        return Elastigroup.find(self.spot.client(), self.targets)


@attr.s(auto_attribs=True)
class Task(ABC):
    kind: str
    targets: TargetList

    task_kinds = dict()

    @abstractmethod
    def run(self):
        pass

    @classmethod
    def register(cls, kind):
        def decorator(subcls):
            cls.task_kinds[kind] = subcls
            return subcls

        return decorator

    def __new__(cls, kind, *args, **kwargs):
        if cls is not Task:
            return super(Task, cls).__new__(cls, kind, *args, **kwargs)
        try:
            task = cls.task_kinds[kind]
            return super(Task, cls).__new__(task)
        except KeyError:
            console.print(f"[bold red]ERROR:[/] Invalid action: {kind}")
            sys.exit(1)


@Task.register("roll")
@attr.s(auto_attribs=True)
class RollTask(Task):
    batch: Optional[Union[str, int]] = ""
    grace: Optional[Union[str, int]] = ""

    def run(self):
        def work(target, batch, grace, console):
            try:
                target.roll(batch, grace)
                console.print(
                    f"Started roll on [bold blue]{target.name}[/] with [bold cyan]"
                    f"{self.batch if '%' in str(self.batch) else self.batch + ' instances'}[/] batch size"
                )
                return True
            except Exception:
                console.print(
                    f"[bold red]ERROR:[/] Failed to roll [bold]{target.name}[/]"
                )
                console.print_exception()
                return False
        loom = pexecute.thread.ThreadLoom(max_runner_cap=PARALLEL_THREADS)
        for target in self.targets:
            loom.add_function(work, [], dict(target=target, batch=self.batch, grace=self.grace, console=console))
        return loom.execute()


@Task.register("upscale")
@attr.s(auto_attribs=True)
class UpscaleTask(Task):
    amount: Union[int, str]

    def run(self):
        def work(target, amount, console):
            try:
                target.scale_up(amount)
                console.print(
                    f"Scaled up [bold blue]{target.name}[/] by [bold cyan]{amount if '%' in str(amount) else amount + ' instances'}[/]"
                )
                return True
            except Exception:
                console.print(
                    f"[bold red]ERROR:[/] Failed to scale up [bold]{target.name}[/]"
                )
                console.print_exception()
                return False
        loom = pexecute.thread.ThreadLoom(max_runner_cap=PARALLEL_THREADS)
        for target in self.targets:
            loom.add_function(work, [], dict(target=target, amount=self.amount, console=console))
        return loom.execute()


@Task.register("downscale")
@attr.s(auto_attribs=True)
class DownscaleTask(Task):
    amount: Union[int, str]

    def run(self):
        def work(target, amount, console):
            try:
                target.scale_down(amount)
                console.print(
                    f"Scaled down [bold blue]{target.name}[/] by [bold cyan]{amount if '%' in str(amount) else amount + ' instances'}[/]"
                )
                return True
            except Exception:
                console.print(
                    f"[bold red]ERROR:[/] Failed to scale down [bold blue]{target.name}[/]"
                )
                console.print_exception()
                return False
        loom = pexecute.thread.ThreadLoom(max_runner_cap=PARALLEL_THREADS)
        for target in self.targets:
            loom.add_function(work, [], dict(target=target, amount=self.amount, console=console))
        return loom.execute()


@Task.register("suspend")
@attr.s(auto_attribs=True)
class SuspendTask(Task):
    processes: List[str]

    def run(self):
        def work(target, process, console):
            process = ElastigroupProcess(process)
            try:
                target.suspend(process)
                console.print(
                    f"Suspended [bold cyan]{process.name}[/] on [bold blue]{target.name}[/]"
                )
                return True
            except Exception:
                console.print(
                    f"[bold red]ERROR:[/] Failed to suspend [bold cyan]{process.name}[/] on [bold blue]{target.name}[/]"
                )
                console.print_exception()
                return False
        loom = pexecute.thread.ThreadLoom(max_runner_cap=PARALLEL_THREADS)
        for target in self.targets:
            for process in self.processes:
                loom.add_function(work, [], dict(target=target, process=process, console=console))
        return loom.execute()


@Task.register("unsuspend")
@attr.s(auto_attribs=True)
class UnsuspendTask(Task):
    processes: List[str]

    def run(self):
        def work(target, process, console):
            process = ElastigroupProcess(process)
            try:
                target.unsuspend(process)
                console.print(
                    f"Unsuspended [bold cyan]{process.name}[/] on [bold blue]{target.name}[/]"
                )
                return True
            except Exception:
                console.print(
                    f"[bold red]ERROR:[/] Failed to unsuspend [bold cyan]{process.name}[/] on [bold blue]{target.name}[/]"
                )
                console.print_exception()
                return False
        loom = pexecute.thread.ThreadLoom(max_runner_cap=PARALLEL_THREADS)
        for target in self.targets:
            for process in self.processes:
                loom.add_function(work, [], dict(target=target, process=process, console=console))
        return loom.execute()


@attr.s(auto_attribs=True)
class Scenario:
    name: str
    tasks: List[Task]
    description: Optional[str] = ""

    def run(self):
        results = []
        for task in self.tasks:
            results.extend(task.run())
        return results
