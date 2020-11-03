import os
import sys
from abc import ABC, abstractmethod
from typing import Optional

import attr
import consulate
import rich.console
import spotinst_sdk

console = rich.console.Console(highlight=False)


@attr.s(auto_attribs=True)
class Provider(ABC):
    name: str
    kind: str = ""

    @abstractmethod
    def client(self):
        pass

    @abstractmethod
    def get(self):
        pass

    @abstractmethod
    def put(self):
        pass

    def __new__(cls, name, kind, *args, **kwargs):
        providers_mapping = {
            "file": FileProvider,
            "consul": ConsulProvider,
            "spot": SpotProvider
        }
        if cls is not Provider:
            return super(Provider, cls).__new__(cls, name, kind, *args, **kwargs)
        try:
            provider = providers_mapping[kind]
            return super(Provider, cls).__new__(provider)
        except KeyError:
            console.print(f"Invalid provider kind: {kind}")
            sys.exit(os.EX_CONFIG)
        except Exception:
            console.print_exception()


@attr.s(auto_attribs=True)
class FileProvider(Provider):
    name: str
    kind: str
    path: str

    def client(self):
        raise NotImplementedError

    def get(self, path):
        file_path = os.path.join(self.path, path)
        try:
            with open(file_path, "r") as file:
                content = file.read()
            return content
        except FileNotFoundError:
            console.print(f"File not found: {file_path}")
            sys.exit(1)
        except (PermissionError, OSError, IOError):
            console.print(f"Unable to read file: {file_path}")
            sys.exit(1)
        except Exception:
            console.print_exception()

    def put(self, path, content):
        file_path = os.path.join(self.path, path)
        try:
            with open(file_path, "w") as file:
                file.write(content)
        except (PermissionError, OSError, IOError):
            console.print(f"Unable to write to file: {file_path}")
            sys.exit(os.EX_IOERR)
        except Exception:
            console.print_exception()


@attr.s(auto_attribs=True)
class ConsulProvider(Provider):
    name: str
    kind: str
    server: str
    path: str
    datacenter: Optional[str] = ""
    token: Optional[str] = ""

    def client(self):
        try:
            return self._consul
        except AttributeError:
            # Initialize Consul client
            host, *port = self.server.split(":")
            port = int(port[0]) if port else 8500
            datacenter = self.datacenter or None
            token = self.token or None
            consul = consulate.Consul(host, port, datacenter, token)
            self._consul = consul
            return consul

    def get(self, path):
        kv_path = os.path.join(self.path, path)
        consul = self.client()
        try:
            content = consul.kv.get(kv_path)
            return content
        except KeyError:
            console.print(f"Consul key not found: {kv_path}")
            sys.exit(os.EX_NOTFOUND)
        except Exception:
            console.print_exception()

    def put(self, path, content):
        kv_path = os.path.join(self.path, path)
        consul = self.client()
        consul.kv.set(kv_path, content)


@attr.s(auto_attribs=True)
class SpotProvider(Provider):
    name: str
    kind: str
    account: str
    token: str

    def client(self):
        try:
            return self._spot
        except AttributeError:
            spot = spotinst_sdk.SpotinstClient(account_id=self.account, auth_token=self.token)
            self._spot = spot
            return spot

    def get(self):
        raise NotImplementedError

    def put(self):
        raise NotImplementedError
