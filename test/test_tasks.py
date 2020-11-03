from spotcli.providers import SpotProvider
import unittest.mock
import pytest

import spotinst_sdk

from spotcli.tasks import (
    Alias,
    TargetList,
    Task,
    RollTask,
    UpscaleTask,
    DownscaleTask,
    SuspendTask,
    UnsuspendTask,
)
from spotcli.elastigroup import Elastigroup, ElastigroupProcess


@pytest.mark.unit
@pytest.mark.tasks
class TasksTests:
    def test_alias_is_list(self):
        assert Alias("test", []) == list()

    @unittest.mock.patch.object(Elastigroup, "find", new=lambda _, x: x)
    @pytest.mark.parametrize(
        "targets",
        [
            (["a", ["b", ["c"]], "d"], ["a", "b", "c", "d"]),
            (["a", "b", "c"], ["a", "b", "c"]),
            ([[[[["a"], "b"], "c"], "d"], "e"], ["a", "b", "c", "d", "e"]),
        ],
    )
    def test_target_list_flattens_itself(self, targets):
        spot = unittest.mock.MagicMock()
        assert TargetList(spot, dict(), targets[0]).data == targets[1]

    @unittest.mock.patch.object(Elastigroup, "find")
    def test_target_list_finds_elastigroups(self, fake_find):
        spot = SpotProvider(name="spot", kind="spot", account="act-12345678", token="deadbeefdeadbeef")
        targets = ["a", "b", "c", "d", "e"]
        TargetList(spot, dict(), targets).data
        calls = [unittest.mock.call(spot, i) for i in targets]
        fake_find.assert_has_calls(calls)

    @unittest.mock.patch.object(Elastigroup, "find")
    def test_target_list_resolves_aliases(self, fake_find):
        spot = SpotProvider(name="spot", kind="spot", account="act-12345678", token="deadbeefdeadbeef")
        aliases = {
            "testA": Alias("test", ["a", "b", "c"]),
            "testB": Alias("testB", ["testA", "d", "e"]),
        }
        TargetList(spot, aliases, ["testB"]).data
        calls = [unittest.mock.call(spot, i) for i in ["a", "b", "c", "d", "e"]]
        fake_find.assert_has_calls(calls)

    def test_task_factory_instantiates_correct_classes(self):
        assert isinstance(Task(kind="roll", targets=[]), RollTask)
        assert isinstance(Task(kind="upscale", targets=[], amount=1), UpscaleTask)
        assert isinstance(Task(kind="downscale", targets=[], amount=1), DownscaleTask)
        assert isinstance(
            Task(kind="suspend", targets=[], processes=[ElastigroupProcess.AUTO_HEALING]),
            SuspendTask,
        )
        assert isinstance(
            Task(kind="unsuspend", targets=[], processes=[ElastigroupProcess.AUTO_HEALING]),
            UnsuspendTask,
        )

    def test_tasks_call_correct_methods(self):
        mock_elastigroup = unittest.mock.MagicMock()

        Task(kind="roll", targets=[mock_elastigroup]).run()
        Task(kind="upscale", targets=[mock_elastigroup], amount=1).run()
        Task(kind="downscale", targets=[mock_elastigroup], amount=1).run()
        Task(
            kind="suspend",
            targets=[mock_elastigroup],
            processes=[ElastigroupProcess.AUTO_HEALING],
        ).run()
        Task(
            kind="unsuspend",
            targets=[mock_elastigroup],
            processes=[ElastigroupProcess.AUTO_HEALING],
        ).run()

        mock_elastigroup.roll.assert_called_with(None, None)
        mock_elastigroup.scale_up.assert_called_with(1)
        mock_elastigroup.scale_down.assert_called_with(1)
        mock_elastigroup.suspend.assert_called_with(ElastigroupProcess.AUTO_HEALING)
        mock_elastigroup.unsuspend.assert_called_with(ElastigroupProcess.AUTO_HEALING)
