import os
import sys
from typing import Optional

import attr
import consul as consul_client  # type: ignore
import rich.console

from spotcli.providers import Provider

console = rich.console.Console(highlight=False)


@Provider.register("consul")
@attr.s(auto_attribs=True)
class ConsulProvider(Provider):
    name: str
    kind: str
    server: str
    path: str
    scheme: Optional[str] = ""
    datacenter: Optional[str] = ""
    token: Optional[str] = ""

    def client(self):
        try:
            consul = getattr(self, "_consul")
        except AttributeError:
            # Initialize Consul client
            host, *port = self.server.split(":")
            port = int(port[0]) if port else 8500
            scheme = self.scheme or "http"
            datacenter = self.datacenter or None
            token = self.token or None
            consul = consul_client.Consul(
                host=host, port=port, scheme=scheme, dc=datacenter, token=token
            )
            setattr(self, "_consul", consul)
        finally:
            return consul

    def get(self, path):
        kv_path = os.path.join(self.path, path)
        consul = self.client()
        try:
            kv_path = kv_path.lstrip("/")
            _, document = consul.kv.get(kv_path)
            content = document["Value"].decode("utf-8")
            return content
        except (KeyError, TypeError):
            console.print(f"[bold red]ERROR:[/] Consul key not found: {kv_path}")
            sys.exit(1)

    def put(self, path, content):
        kv_path = os.path.join(self.path, path)
        consul = self.client()
        consul.kv.set(kv_path, content)
