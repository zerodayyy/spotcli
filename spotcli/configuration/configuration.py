import os
import sys

import attr
import rich.console
from config import ConfigurationSet, config_from_yaml
from spotcli.configuration.tasks import Alias, Scenario, TargetList, Task
from spotcli.providers import Provider

console = rich.console.Console(highlight=False)


@attr.s(auto_attribs=True)
class Source:
    provider: Provider
    path: str

    def read(self):
        config_raw = self.provider.get(self.path)
        config = config_from_yaml(config_raw, lowercase_keys=True)
        return config


@attr.s(auto_attribs=True)
class Config:
    config: ConfigurationSet

    @property
    def version(self):
        try:
            return self.config.version
        except KeyError:
            console.print(
                "[bold red]ERROR:[/] Missing [italic]version[/] in the config"
            )
            sys.exit(1)

    @property
    def sources(self):
        try:
            return self._sources
        except AttributeError:
            sources = []
            try:
                for source in self.config.sources:
                    sources.append(
                        Source(
                            provider=self.providers[source["provider"]],
                            path=source["path"],
                        )
                    )
                self._sources = sources
                return sources
            except KeyError:
                console.print(
                    "[bold red]ERROR:[/] Missing [italic]sources[/] in the config"
                )
                sys.exit(1)

    @property
    def providers(self):
        try:
            return self._providers
        except AttributeError:
            providers = {}
            try:
                providers_raw = (
                    {
                        p: self.config.providers[p].as_dict()
                        for p in list(self.config.providers)
                    }
                    if "providers" in self.config
                    else {}
                )
            except KeyError:
                console.print(
                    "[bold red]ERROR:[/] Missing [italic]providers[/] in the config"
                )
                sys.exit(1)
            for name, provider in providers_raw.items():
                providers[name] = Provider(name=name, **provider)
            self._providers = providers
            return providers

    @property
    def scenarios(self):
        try:
            return self._scenarios
        except AttributeError:
            s = {}
            if "scenarios" in self.config:
                try:
                    scenarios_raw = (
                        {
                            s: self.config.scenarios[s].as_dict()
                            for s in list(self.config.scenarios)
                        }
                        if "scenarios" in self.config
                        else {}
                    )
                except KeyError:
                    console.print(
                        "[bold red]ERROR:[/] Missing [italic]scenarios[/] in the config"
                    )
                    sys.exit(1)
                for name, scenario in scenarios_raw.items():
                    tasks = []
                    for task in scenario["tasks"]:
                        task["targets"] = TargetList(
                            self.providers["spot"], self.aliases, task["targets"]
                        )
                        tasks.append(Task(**task))
                    s.update(
                        {
                            name: Scenario(
                                name=name,
                                tasks=tasks,
                                description=scenario["description"],
                            )
                        }
                    )
            scenarios = s
            self._scenarios = scenarios
            return scenarios

    @property
    def aliases(self):
        try:
            return self._aliases
        except AttributeError:
            try:
                aliases = (
                    {
                        k: Alias(name=k, targets=v)
                        for k, v in self.config.aliases.as_dict().items()
                    }
                    if "aliases" in self.config
                    else {}
                )
            except KeyError:
                console.print(
                    "[bold red]ERROR:[/] Missing [italic]aliases[/] in the config"
                )
                sys.exit(1)
            self._aliases = aliases
            return aliases


def load():
    # Load bootstrap configuration
    try:
        bootstrap_provider = Provider(
            name="bootstrap", kind="file", path=os.path.expanduser("~/.spot")
        )
        bootstrap_source = Source(provider=bootstrap_provider, path="config.yaml")
        bootstrap_config_data = ConfigurationSet(bootstrap_source.read())
        bootstrap_config = Config(bootstrap_config_data)
    except Exception:
        console.print("[bold red]ERROR:[/] Unable to load config")
        console.print_exception()
        sys.exit(1)

    # Load actual configuration
    try:
        config_data = ConfigurationSet(
            bootstrap_config_data,
            *[source.read() for source in bootstrap_config.sources]
        )
        config = Config(config_data)
        return config
    except Exception:
        console.print("[bold red]ERROR:[/] Unable to load config")
        console.print_exception()
        sys.exit(1)
