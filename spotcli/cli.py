#!/usr/bin/env python3
import sys
import time
from typing import List

import click
import requests
import rich.console
import rich.table
import rich.traceback
import semver  # type: ignore

import spotcli
import spotcli.configuration
from spotcli.configuration.tasks import TargetList, Task
from spotcli.utils.elastigroup import ElastigroupProcess

UPDATE_URL = "https://api.github.com/repos/SupersonicAds/spotcli/releases/latest"
UPDATE_COMMAND = 'bash -c "$(curl -fsSL https://raw.githubusercontent.com/SupersonicAds/spotcli/main/install.sh)"'


console = rich.console.Console(highlight=False)
rich.traceback.install()


@click.group()
def main():
    pass


@click.command()
def version() -> None:
    """Get SpotCLI version."""
    console.print(f"SpotCLI version {spotcli.__version__}")


@click.command()
@click.argument("kind", type=click.Choice(("aliases", "scenarios")), required=True)
@click.option(
    "-f",
    "--filter",
    type=click.STRING,
    default=[],
    multiple=True,
    help="Filter expression",
)
def list(kind: str, filter: List[str]) -> None:
    """List entities.

    KIND is either `aliases` or `scenarios`.
    """
    console.print(f"[bold]SpotCLI version {spotcli.__version__}")
    new_version = updates_available()
    if new_version:
        console.print(f"\n[green]New version [bold]{new_version}[/] is available\n")
        console.print(
            f"You can update SpotCLI by running:\n[bold]{UPDATE_COMMAND}[/]\n"
        )
    config = spotcli.configuration.load()
    table = rich.table.Table(title=kind.title(), show_lines=True)
    if kind == "aliases":
        table.add_column("Name", style="cyan")
        table.add_column("Targets", style="green")
        aliases = (
            spotcli.utils.filter(config.aliases.keys(), filter)
            if filter
            else config.aliases.keys()
        )
        for alias in aliases:
            table.add_row(alias, "\n".join(config.aliases[alias].targets))
        if not aliases:
            console.print("No aliases found!")
            return
    else:
        table.add_column("Name", style="magenta")
        table.add_column("Description")
        scenarios = (
            spotcli.utils.filter(config.scenarios.keys(), filter)
            if filter
            else config.scenarios.keys()
        )
        for scenario in scenarios:
            table.add_row(scenario, config.scenarios[scenario].description)
        if not scenarios:
            console.print("No aliases found!")
            return
    console.print(table)


@click.command()
@click.argument("scenario", type=click.STRING, required=True)
@click.option(
    "-y",
    "--auto-approve",
    type=click.BOOL,
    default=False,
    is_flag=True,
    help="Skip interactive approval before executing actions",
)
def run(scenario: str, auto_approve: bool) -> None:
    """Run a scenario.

    SCENARIO is the name of the scenario to run.
    """
    console.print(f"[bold]SpotCLI version {spotcli.__version__}")
    new_version = updates_available()
    if new_version:
        console.print(f"\n[green]New version [bold]{new_version}[/] is available\n")
        console.print(
            f"You can update SpotCLI by running:\n[bold]{UPDATE_COMMAND}[/]\n"
        )
    config = spotcli.configuration.load()
    try:
        s = config.scenarios[scenario]
        console.print(
            f"Loading scenario [bold green]{scenario}[/]"
            + f" [italic]({s.description})[/]"
            if s.description
            else ""
        )
    except KeyError:
        console.print(f"Scenario [bold red]{scenario}[/] not found")
        sys.exit(1)
    for task in s.tasks:
        table = rich.table.Table(
            title=f"Going to [bold]{task.kind}[/] these elastigroups:", show_lines=True
        )
        table.add_column("ID", justify="center", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Instances", style="green")
        for target in task.targets:
            table.add_row(target.id, target.name, str(target.capacity["target"]))
        console.print(table)
        console.print("\n")
    auto_approve or click.confirm("Continue?", abort=True)
    t_start = time.time()
    s.run()
    t_end = time.time()
    duration = t_end - t_start
    console.print(
        f"\n[bold green]Scenario run complete! Executed {len(s.tasks)} tasks in {duration:.2f} seconds."
    )


@click.command()
@click.argument("group", type=click.STRING, required=True)
@click.option(
    "-p",
    "--show-processes",
    type=click.BOOL,
    default=False,
    is_flag=True,
    help="Show process suspension status",
)
def status(group: str, show_processes: bool) -> None:
    """Get elastigroup status.

    GROUP is elastigroup name, alias or regex.
    """
    console.print(f"[bold]SpotCLI version {spotcli.__version__}")
    new_version = updates_available()
    if new_version:
        console.print(f"\n[green]New version [bold]{new_version}[/] is available\n")
        console.print(
            f"You can update SpotCLI by running:\n[bold]{UPDATE_COMMAND}[/]\n"
        )
    config = spotcli.configuration.load()
    targets = TargetList(config.providers["spot"], config.aliases, group)
    table = rich.table.Table(title="Elastigroup status", show_lines=True)
    table.add_column("ID", justify="center", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Instances", style="green")
    if show_processes:
        table.add_column("Processes", style="yellow")
    for target in targets:
        if show_processes:
            processes_raw = target.processes
            processes = "\n".join(
                [
                    f"[bold]{proc}[/]: "
                    f"{'[green]' if 'active' in processes_raw[proc] else '[red]'}"
                    f"{processes_raw[proc]}[/]"
                    for proc in processes_raw
                ]
            )
            table.add_row(
                target.id, target.name, str(target.capacity["target"]), processes
            )
        else:
            table.add_row(target.id, target.name, str(target.capacity["target"]))
    console.print(table)


@click.command()
@click.argument("group", type=click.STRING, required=True)
@click.option(
    "-b",
    "--batch",
    type=click.STRING,
    default="20%",
    help="Batch size, instances or percentage",
    show_default=True,
)
@click.option(
    "-g",
    "--grace",
    type=click.STRING,
    default="5m",
    callback=lambda _1, _2, g: g + "s" if g.isdigit() else g,
    help="Grace period, number with units (seconds if omitted)",
    show_default=True,
)
@click.option(
    "-y",
    "--auto-approve",
    type=click.BOOL,
    default=False,
    is_flag=True,
    help="Skip interactive approval before executing actions",
)
def roll(group: str, batch: str, grace: str, auto_approve: bool) -> None:
    """Roll an elastigroup.

    GROUP is elastigroup name, alias or regex.
    """
    action(
        action="roll", target=group, batch=batch, grace=grace, auto_approve=auto_approve
    )


@click.command()
@click.argument("group", type=click.STRING, required=True)
@click.option(
    "-p",
    "--processes",
    type=click.Choice([p.name for p in ElastigroupProcess]),
    default=[],
    multiple=True,
    required=True,
    help="Processes to suspend",
)
@click.option(
    "-y",
    "--auto-approve",
    type=click.BOOL,
    default=False,
    is_flag=True,
    help="Skip interactive approval before executing actions",
)
def suspend(group: str, processes: List[str], auto_approve: bool) -> None:
    """Suspend a process in an elastigroup.

    GROUP is elastigroup name, alias or regex.
    """
    action(
        action="suspend", target=group, processes=processes, auto_approve=auto_approve
    )


@click.command()
@click.argument("group", type=click.STRING, required=True)
@click.option(
    "-p",
    "--processes",
    type=click.Choice([p.name for p in ElastigroupProcess]),
    default=[],
    multiple=True,
    required=True,
    help="Processes to unsuspend",
)
@click.option(
    "-y",
    "--auto-approve",
    type=click.BOOL,
    default=False,
    is_flag=True,
    help="Skip interactive approval before executing actions",
)
def unsuspend(group: str, processes: List[str], auto_approve: bool) -> None:
    """Unsuspend a process in an elastigroup.

    GROUP is elastigroup name, alias or regex.
    """
    action(
        action="unsuspend", target=group, processes=processes, auto_approve=auto_approve
    )


@click.command()
@click.argument("kind", type=click.Choice(("down", "up")), required=True)
@click.argument("group", type=click.STRING, required=True)
@click.option(
    "-a",
    "--amount",
    type=click.STRING,
    default="10%",
    help="How many instances to add or remove; amount or percentage",
    show_default=True,
)
@click.option(
    "-y",
    "--auto-approve",
    type=click.BOOL,
    default=False,
    is_flag=True,
    help="Skip interactive approval before executing actions",
)
def scale(kind: str, group: str, amount: str, auto_approve: bool) -> None:
    """Scale an elastigroup up or down.

    KIND is the scaling direction: up or down.
    GROUP is elastigroup name, alias or regex.
    """
    action(
        action=f"{kind}scale", target=group, amount=amount, auto_approve=auto_approve
    )


main.add_command(version)
main.add_command(list)
main.add_command(run)
main.add_command(status)
main.add_command(roll)
main.add_command(suspend)
main.add_command(unsuspend)
main.add_command(scale)


def action(action: str, target: str, auto_approve: bool, **kwargs) -> None:
    console.print(f"[bold]SpotCLI version {spotcli.__version__}")
    new_version = updates_available()
    if new_version:
        console.print(f"\n[green]New version [bold]{new_version}[/] is available\n")
        console.print(
            f"You can update SpotCLI by running:\n[bold]{UPDATE_COMMAND}[/]\n"
        )
    config = spotcli.configuration.load()
    targets = TargetList(config.providers["spot"], config.aliases, [target])
    task = Task(kind=action, targets=targets, **kwargs)  # type: ignore
    table = rich.table.Table(
        title=f"Going to [bold]{task.kind}[/] these elastigroups:", show_lines=True
    )
    table.add_column("ID", justify="center", style="cyan")
    table.add_column("Name", style="magenta")
    table.add_column("Instances", style="green")
    for t in task.targets:
        table.add_row(t.id, t.name, str(t.capacity["target"]))
    console.print(table)
    console.print("\n")
    auto_approve or click.confirm("Continue?", abort=True)
    t_start = time.time()
    task.run()
    t_end = time.time()
    duration = t_end - t_start
    console.print(
        f"\n[bold green]Task run complete! Ran 1 task in {duration:.2f} seconds."
    )


def updates_available() -> str:
    url = UPDATE_URL
    update = ""
    try:
        current_version = spotcli.__version__
        upstream_version = (
            requests.get(url, timeout=1).json().get("name", current_version).lstrip("v")
        )
        if semver.compare(upstream_version, current_version) == 1:
            update = upstream_version
    finally:
        return update


if __name__ == "__main__":
    main()
