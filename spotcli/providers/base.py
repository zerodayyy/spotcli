import sys
from abc import ABC, abstractmethod

import attr
import rich.console

console = rich.console.Console(highlight=False)


@attr.s(auto_attribs=True)
class Provider(ABC):
    name: str
    kind: str = ""

    @classmethod
    def register(cls, kind):
        def decorator(subcls):
            providers = getattr(cls, "providers", {})
            providers.update({kind: subcls})
            setattr(cls, "providers", providers)
            return subcls

        return decorator

    def __new__(cls, name: str, kind: str, *args, **kwargs) -> "Provider":
        if cls is not Provider:
            return super(Provider, cls).__new__(cls, name, kind, *args, **kwargs)  # type: ignore
        try:
            provider = getattr(cls, "providers", {})[kind]
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
