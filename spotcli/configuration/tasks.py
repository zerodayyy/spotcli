import sys
import threading
from abc import ABC, abstractmethod
from collections import UserList
from typing import Dict, List, Optional, Union

import attr
import rich.console

from spotcli.providers.spot import SpotProvider
from spotcli.utils.elastigroup import Elastigroup, ElastigroupProcess

console = rich.console.Console(highlight=False)


class Alias(UserList):
    def __init__(self, name: str, targets: List[str]):
        self.name = name
        self.targets = targets

    @property
    def data(self):
        return self.targets


class TargetList(UserList):
    def __init__(
        self,
        spot: SpotProvider,
        aliases: Dict[str, Alias],
        targets: Union[str, List[str]],
    ):
        self.spot = spot
        self.aliases = aliases
        self.targets = targets

    @property
    def data(self):
        try:
            targets = getattr(self, "_targets")
        except AttributeError:

            def reduce(
                array: Union[List[str], Alias, str], result: List[str] = []
            ) -> List[str]:
                """Flatten a list with arbitrary dimensions."""
                if isinstance(array, str):
                    array = [array]
                for item in array:
                    if isinstance(item, str):
                        if item in self.aliases:
                            reduce(self.aliases[item], result)
                        else:
                            result.append(item)
                    else:
                        reduce(item, result)
                return result

            targets = Elastigroup.find(self.spot.client(), reduce(self.targets))
            setattr(self, "_targets", targets)
        finally:
            return targets


@attr.s(auto_attribs=True)
class Task(ABC):
    kind: str
    targets: TargetList

    @classmethod
    def register(cls, kind):
        def decorator(subcls):
            kinds = getattr(cls, "kinds", {})
            kinds.update({kind: subcls})
            setattr(cls, "kinds", kinds)
            return subcls

        return decorator

    def __new__(cls, kind: str, *args, **kwargs) -> "Task":
        if cls is not Task:
            return super(Task, cls).__new__(cls, kind, *args, **kwargs)  # type: ignore
        try:
            task = getattr(cls, "kinds", {})[kind]
            return super(Task, cls).__new__(task)
        except KeyError:
            console.print(f"[bold red]ERROR:[/] Invalid action: {kind}")
            sys.exit(1)

    @abstractmethod
    def run(self):
        pass


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

        threads = []
        for target in self.targets:
            thread = threading.Thread(
                None,
                work,
                kwargs=dict(
                    target=target, batch=self.batch, grace=self.grace, console=console
                ),
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()


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

        threads = []
        for target in self.targets:
            thread = threading.Thread(
                None,
                work,
                kwargs=dict(target=target, amount=self.amount, console=console),
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()


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

        threads = []
        for target in self.targets:
            thread = threading.Thread(
                None,
                work,
                kwargs=dict(target=target, amount=self.amount, console=console),
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()


@Task.register("suspend")
@attr.s(auto_attribs=True)
class SuspendTask(Task):
    processes: List[str]

    def run(self):
        def work(target, process, console):
            process = ElastigroupProcess[process]
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

        threads = []
        for target in self.targets:
            for process in self.processes:
                thread = threading.Thread(
                    None,
                    work,
                    kwargs=dict(target=target, process=process, console=console),
                )
                thread.start()
                threads.append(thread)

        for thread in threads:
            thread.join()


@Task.register("unsuspend")
@attr.s(auto_attribs=True)
class UnsuspendTask(Task):
    processes: List[str]

    def run(self):
        def work(target, process, console):
            process = ElastigroupProcess[process]
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

        threads = []
        for target in self.targets:
            for process in self.processes:
                thread = threading.Thread(
                    None,
                    work,
                    kwargs=dict(target=target, process=process, console=console),
                )
                thread.start()
                threads.append(thread)

        for thread in threads:
            thread.join()


@attr.s(auto_attribs=True)
class Scenario:
    name: str
    tasks: List[Task]
    description: Optional[str] = ""

    def run(self):
        results = []
        for task in self.tasks:
            task.run()
