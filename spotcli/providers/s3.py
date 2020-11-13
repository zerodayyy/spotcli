import os
import sys
from typing import Optional

import attr
import boto3
import rich.console
from botocore.exceptions import ClientError
from spotcli.providers import Provider

console = rich.console.Console(highlight=False)


@Provider.register("s3")
@attr.s(auto_attribs=True)
class S3Provider(Provider):
    name: str
    kind: str
    bucket: str
    path: Optional[str] = ""
    access_key_id: Optional[str] = ""
    secret_access_key: Optional[str] = ""

    def client(self):
        try:
            return self._s3
        except AttributeError:
            # Initialize S3 client
            credentials = (
                {
                    "aws_access_key_id": self.access_key_id,
                    "aws_secret_access_key": self.secret_access_key,
                }
                if self.access_key_id and self.secret_access_key
                else {}
            )
            s3 = boto3.resource("s3", **credentials)
            self._s3 = s3
            return s3

    def get(self, path):
        object_path = os.path.join(self.path, path).lstrip("/")
        s3 = self.client()
        try:
            object = s3.Object(self.bucket, object_path)
            content = object.get()["Body"].read().decode("utf-8")
            return content
        except ClientError as e:
            errors = {
                "NoSuchBucket": f"[bold red]ERROR:[/] S3 bucket not found: {self.bucket}",
                "NoSuchKey": f"[bold red]ERROR:[/] S3 object not found: {object_path}",
                "AccessDenied": f"[bold red]ERROR:[/] Access denied to S3 bucket {self.bucket}",
                "default": f"[bold red]ERROR:[/] S3 error: {e.response.get('message', '')}",
            }
            console.print(errors.get(e.response["Error"]["Code"], errors["default"]))
            sys.exit(1)

    def put(self, path, content):
        object_path = os.path.join(self.path, path).lstrip("/")
        s3 = self.client()
        try:
            object = s3.Object(self.bucket, object_path)
            object.put(Body=content.encode("utf-8"))
        except ClientError as e:
            errors = {
                "NoSuchBucket": f"[bold red]ERROR:[/] S3 bucket not found: {self.bucket}",
                "AccessDenied": f"[bold red]ERROR:[/] Access denied to S3 bucket {self.bucket}",
                "UnknownError": f"[bold red]ERROR:[/] S3 error: {e.response.get('message', '')}",
            }
            console.print(errors.get(e.response["Error"]["Code"], errors["default"]))
            sys.exit(1)
