import os
import sys

import attr
import rich.console
from spotcli.providers import Provider

console = rich.console.Console(highlight=False)


@Provider.register("file")
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
            console.print(f"[bold red]ERROR:[/] File not found: {file_path}")
            sys.exit(1)
        except (PermissionError, OSError, IOError):
            console.print(f"[bold red]ERROR:[/] Unable to read file: {file_path}")
            sys.exit(1)

    def put(self, path, content):
        file_path = os.path.join(self.path, path)
        try:
            with open(file_path, "w") as file:
                file.write(content)
        except (PermissionError, OSError, IOError):
            console.print(f"[bold red]ERROR:[/] Unable to write to file: {file_path}")
            sys.exit(1)
