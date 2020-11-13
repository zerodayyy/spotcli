import sys
from abc import ABC, abstractmethod

import attr
import rich.console

console = rich.console.Console(highlight=False)


@attr.s(auto_attribs=True)
class Provider(ABC):
    name: str
    kind: str = ""

    providers = {}

    @classmethod
    def register(cls, kind):
        def decorator(subcls):
            cls.providers[kind] = subcls
            return subcls

        return decorator

    def __new__(cls, name, kind, *args, **kwargs):
        if cls is not Provider:
            return super(Provider, cls).__new__(cls, name, kind, *args, **kwargs)
        try:
            provider = cls.providers[kind]
            return super(Provider, cls).__new__(provider)
        except KeyError:
            console.print(f"[bold red]ERROR:[/] Invalid provider kind: {kind}")
            sys.exit(1)

    @abstractmethod
    def client(self):
        pass

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def put(self):
        pass
