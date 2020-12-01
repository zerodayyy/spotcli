"""Elastigroup module.

This module accomodates an interface for Spot Elastigroup.
"""

import enum
from typing import List, Union

import attr
import durations
import spotcli.utils
import spotinst_sdk


@attr.s(auto_attribs=True)
class Elastigroup:
    """Interface for a Spot Elastigroup.

    This class is a minimalistic high-level representation of
    an Elastigroup with only stanzas required by spotcli project:
        * group capacity
        * processes & scaling policies
        * rolls

    Attributes:
        id (str): Elastigroup ID.

    """

    spot: spotinst_sdk.SpotinstClient
    id: str

    @classmethod
    def find(
        cls, spot: spotinst_sdk.SpotinstClient, query: Union[str, List[str]]
    ) -> List["Elastigroup"]:
        """Find Elastigroups.

        Finds Elastigroups by name via a regular expression or a name value.

        Args:
            spot (spotinst_sdk.SpotinstClient): Spot client.
            query (Union[str, List[str]]): Elastigroup names or regular expressions.

        Returns:
            List[Elastigroup]: Found Elastigroups.
        """

        try:
            groups = cls._elastigroups
        except AttributeError:
            groups = {group["name"]: group["id"] for group in spot.get_elastigroups()}
            cls._elastigroups = groups

        if isinstance(query, str):
            query = [query]

        matches_keys = spotcli.utils.filter(groups.keys(), query)
        matches = [cls(spot, groups[key]) for key in matches_keys]
        return matches

    @property
    def _group(self):
        try:
            return self._group_data
        except AttributeError:
            self._group_data = self.spot.get_elastigroup(self.id)
            return self._group_data

    @property
    def processes(self):
        """Get status of Elastigroup processes.

        This function iterates over all known processes, including custom aliases for
        up and down auto-scaling policies (see `ElastigroupProcess` class docs), checks
        Elastigroup for suspended processes and scaling policies and returns corresponding
        statuses.

        Value:
            dict of str: str: Elastigroup processes and their statuses.

        """
        process_suspensions = self.spot.list_suspended_process(self.id)
        policy_suspensions = self.spot.list_suspended_scaling_policies(self.id)
        policies = dict()
        policies_raw = {
            "down": self._group["scaling"].get("down") or [],
            "up": self._group["scaling"].get("up") or [],
        }
        policies[ElastigroupProcess.AUTO_SCALE_DOWN] = [
            policy["policy_name"] for policy in policies_raw["down"]
        ]
        policies[ElastigroupProcess.AUTO_SCALE_UP] = [
            policy["policy_name"] for policy in policies_raw["up"]
        ]
        suspended_processes = (
            process_suspensions[0]["processes"] if process_suspensions else []
        )
        suspended_policies = (
            [
                suspension["policy_name"]
                for suspension in policy_suspensions[0]["scale_policy_suspensions"]
            ]
            if policy_suspensions
            else []
        )
        processes = dict()
        for process in ElastigroupProcess:
            if process in [
                ElastigroupProcess.AUTO_SCALE_DOWN,
                ElastigroupProcess.AUTO_SCALE_UP,
            ]:
                processes[process.name] = (
                    "suspended"
                    if any(
                        [policy in suspended_policies for policy in policies[process]]
                    )
                    else "active"
                )
                continue
            processes[process.name] = (
                "suspended" if process.name in suspended_processes else "active"
            )
        return processes

    @property
    def capacity(self):
        """Get Elastigroup capacity.

        Value:
            dict of str: int: Elastigroup capacity.

        """
        return dict(
            **{k: self._group["capacity"][k] for k in ["minimum", "maximum", "target"]}
        )

    def set_capacity(self, capacity):
        """Set Elastigroup capacity.

        You can provide an arbitrary combination of parameters (out of `minimum`, `maximum`,
        `target`) to the setter. When setting `minimum` or `maximum` capacity so that
        the current `target` exceeds the new range, `target` will be adjusted automatically
        to equal the boundary value.

        Args:
            capacity (dict of str: int): Elastigroup capacity.

        """
        self.spot.update_elastigroup({"capacity": capacity}, self.id)

    @property
    def name(self):
        """Get Elastigroup name.

        Value:
            str: Elastigroup name.

        """
        name = self._group["name"]
        return name

    @property
    def status(self):
        """Get Elastigroup status.

        This function aggregates Elastigroup ID, name, capacity and processes into a single dictionary.

        Value:
            dict of str: str: Elastigroup status.

        """
        status = {
            "id": self.id,
            "name": self.name,
            "capacity": self.capacity,
            "processes": self.processes,
        }
        return status

    def roll(self, batch=None, grace=None):
        """Roll the Elastigroup.

        Rolls an Elastigroup. Batch can be specified as a percentage of `target` capacity (with %) or
        as instance amount. Grace period can be specified as a number of seconds or a string using the
        following format: `1m30s`.

        Args:
            batch (str, optional): Batch size, percentage of capacity or instance amount. Default is 20%.
            grace (str, optional): Grace period. Default is 5 minutes.

        """
        if not batch:
            batch = "20%"
        if not grace:
            grace = "5m"
        batch = (
            int(batch.strip("%"))
            if "%" in str(batch)
            else int(int(batch) / self.capacity["target"] * 100)
        )
        grace = int(durations.Duration(grace).to_seconds())
        return self.spot.roll_group(
            self.id,
            spotinst_sdk.aws_elastigroup.Roll(
                batch_size_percentage=batch, grace_period=grace
            ),
        )

    def suspend(self, process):
        """Suspend a process.

        Suspends a process or an auto-scaling policy.

        Args:
            process (ElastigroupProcess): Process to suspend.

        """
        if ElastigroupProcess(process) in [
            ElastigroupProcess.AUTO_SCALE_DOWN,
            ElastigroupProcess.AUTO_SCALE_UP,
        ]:
            scaling_policy_kind = (
                ElastigroupProcess(process).value.rsplit("_", 1)[-1].lower()
            )
            scaling_policies = [
                policy["policy_name"]
                for policy in self._group["scaling"].get(scaling_policy_kind, [])
            ]
            try:
                for policy in scaling_policies:
                    self.spot.suspend_scaling_policies(self.id, policy)
            except spotinst_sdk.SpotinstClientException as e:
                if "is already suspended" not in str(e):
                    raise e
            return
        self.spot.suspend_process(self.id, [process.name], None)

    def unsuspend(self, process):
        """Unsuspend a process.

        Unsuspends a process or an auto-scaling policy.

        Args:
            process (ElastigroupProcess): Process to unsuspend.

        """
        if ElastigroupProcess(process) in [
            ElastigroupProcess.AUTO_SCALE_DOWN,
            ElastigroupProcess.AUTO_SCALE_UP,
        ]:
            scaling_policy_kind = (
                ElastigroupProcess(process).value.rsplit("_", 1)[-1].lower()
            )
            scaling_policies = [
                policy["policy_name"]
                for policy in self._group["scaling"].get(scaling_policy_kind, [])
            ]
            for policy in scaling_policies:
                self.spot.resume_suspended_scaling_policies(self.id, policy)
            return
        self.spot.remove_suspended_process(self.id, [process.name])

    def scale_up(self, amount):
        """Add instances to Elastigroup.

        Scales the Elastigroup up by `amount` instances.

        Args:
            amount (int or str): Amount of instances to add, number or percentage from target capacity.

        """
        amount = (
            int(int(amount.strip("%")) / 100 * self.capacity["target"])
            if "%" in str(amount)
            else int(amount)
        )
        if amount == 0:
            return
        self.spot.scale_elastigroup_up(self.id, amount)

    def scale_down(self, amount):
        """Remove instances from Elastigroup.

        Scales the Elastigroup down by `amount` instances.

        Args:
            amount (int or str): Amount of instances to remove, number or percentage from target capacity.

        """
        amount = (
            int(int(amount.strip("%")) / 100 * self.capacity["target"])
            if "%" in str(amount)
            else int(amount)
        )
        if amount == 0:
            return
        self.spot.scale_elastigroup_down(self.id, amount)


@enum.unique
class ElastigroupProcess(enum.Enum):
    """A set of Elastigroup processes.

    AUTO_SCALE_DOWN and AUTO_SCALE_UP represent respective scaling policies as abstract processes.

    """

    AUTO_SCALE = enum.auto()
    AUTO_HEALING = enum.auto()
    OUT_OF_STRATEGY = enum.auto()
    PREVENTIVE_REPLACEMENT = enum.auto()
    REVERT_PREFERRED = enum.auto()
    SCHEDULING = enum.auto()
    AUTO_SCALE_DOWN = enum.auto()
    AUTO_SCALE_UP = enum.auto()
