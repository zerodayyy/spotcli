import attr
import spotinst_sdk  # type: ignore

from spotcli.providers import Provider


@Provider.register("spot")
@attr.s(auto_attribs=True)
class SpotProvider(Provider):
    name: str
    kind: str
    account: str
    token: str

    def client(self) -> spotinst_sdk.SpotinstClient:
        try:
            spot = getattr(self, "_spot")
        except AttributeError:
            spot = spotinst_sdk.SpotinstClient(
                account_id=self.account, auth_token=self.token
            )
            setattr(self, "_spot", spot)
        finally:
            return spot

    def get(self):
        raise NotImplementedError

    def put(self):
        raise NotImplementedError
