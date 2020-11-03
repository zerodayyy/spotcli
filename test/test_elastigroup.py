import unittest.mock

import pytest
import spotinst_sdk

from spotcli.elastigroup import Elastigroup, ElastigroupProcess


@pytest.fixture(scope="function")
def arrange_elastigroup():
    mock_elastigroup = {
        "id": "sig-12345678",
        "name": "test-elastigroup",
        "capacity": {"minimum": 0, "maximum": 200, "target": 100},
        "scaling": {
            "down": [
                {"policy_name": "SCALING_POLICY_DOWN_1"},
                {"policy_name": "SCALING_POLICY_DOWN_2"},
            ],
            "up": [{"policy_name": "SCALING_POLICY_UP_1"}],
        },
    }
    mock_suspended_processes = [{"processes": ["AUTO_HEALING"]}]
    mock_suspended_scaling_policies = [
        {
            "scale_policy_suspensions": [
                {"policy_name": "SCALING_POLICY_DOWN_1"},
                {"policy_name": "SCALING_POLICY_DOWN_2"},
            ]
        }
    ]
    spotinst_client = spotinst_sdk.SpotinstClient(
        account_id="act-12345678", auth_token="deadbeefdeadbeef"
    )
    spotinst_client.get_elastigroup = unittest.mock.MagicMock(
        return_value=mock_elastigroup
    )
    spotinst_client.update_elastigroup = unittest.mock.MagicMock()
    spotinst_client.roll_group = unittest.mock.MagicMock()
    spotinst_client.suspend_process = unittest.mock.MagicMock()
    spotinst_client.remove_suspended_process = unittest.mock.MagicMock()
    spotinst_client.suspend_scaling_policies = unittest.mock.MagicMock()
    spotinst_client.resume_suspended_scaling_policies = unittest.mock.MagicMock()
    spotinst_client.scale_elastigroup_up = unittest.mock.MagicMock()
    spotinst_client.scale_elastigroup_down = unittest.mock.MagicMock()
    spotinst_client.list_suspended_process = unittest.mock.MagicMock(
        return_value=mock_suspended_processes
    )
    spotinst_client.list_suspended_scaling_policies = unittest.mock.MagicMock(
        return_value=mock_suspended_scaling_policies
    )
    elastigroup = Elastigroup(spotinst_client, "sig-12345678")
    return spotinst_client, elastigroup


@pytest.mark.unit
@pytest.mark.elastigroup
class ElastigroupTests:
    @pytest.mark.parametrize(
        "query",
        [
            ("(is|rv|ow|banner)-bidder(?!.*haproxy)", ["sig-00000001", "sig-00000003"]),
            ("prod_us-is-ds-online.sonic-us.us-east-1", ["sig-00000005"]),
            ("is", ["sig-00000001", "sig-00000002", "sig-00000005"]),
        ],
    )
    @unittest.mock.patch("spotcli.elastigroup.Elastigroup", autospec=True)
    def test_finds_elastigroups(_, ElastigroupMock, query):
        mock_elastigroup_list = [
            {
                "id": "sig-00000001",
                "name": "prod_us-is-bidder.sonic-us.us-east-1",
            },
            {
                "id": "sig-00000002",
                "name": "prod_us-is-bidder-haproxy.sonic-us.us-east-1",
            },
            {
                "id": "sig-00000003",
                "name": "prod_us-rv-bidder.sonic-us.us-east-1",
            },
            {
                "id": "sig-00000004",
                "name": "prod_us-rv-bidder-haproxy.sonic-us.us-east-1",
            },
            {
                "id": "sig-00000005",
                "name": "prod_us-is-ds-online.sonic-us.us-east-1",
            },
            {
                "id": "sig-00000006",
                "name": "production-platform-api.production.eu-west-1",
            },
        ]
        spotinst_client = spotinst_sdk.SpotinstClient(
            account_id="act-12345678", auth_token="deadbeefdeadbeef"
        )
        spotinst_client.get_elastigroups = unittest.mock.MagicMock(
            return_value=mock_elastigroup_list
        )
        groups = Elastigroup.find(spotinst_client, query[0])
        for id in query[1]:
            ElastigroupMock.assert_any_call(spotinst_client, id)
        assert groups == [ElastigroupMock(spotinst_client, id) for id in query[1]]
        ElastigroupMock.reset_mock(return_value=True)

    @pytest.mark.parametrize("batch_size", [20, "20", "20%"])
    @unittest.mock.patch("spotinst_sdk.aws_elastigroup.Roll", autospec=True)
    def test_elastigroup_roll(_, MockRoll, batch_size, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        elastigroup.roll(batch_size, "1m45s")
        MockRoll.assert_called_with(batch_size_percentage=20, grace_period=105)
        spotinst_client.roll_group.assert_called_with("sig-12345678", MockRoll())

    def test_elastigroup_suspend_process(_, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        elastigroup.suspend(ElastigroupProcess.AUTO_HEALING)
        spotinst_client.suspend_process.assert_called_with(
            "sig-12345678", ["AUTO_HEALING"], None
        )

    def test_elastigroup_suspend_scaling_policy(_, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        elastigroup.suspend(ElastigroupProcess.AUTO_SCALE_DOWN)
        spotinst_client.suspend_scaling_policies.assert_called_with(
            "sig-12345678", ["SCALING_POLICY_DOWN_1", "SCALING_POLICY_DOWN_2"]
        )

    def test_elastigroup_unsuspend_process(_, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        elastigroup.unsuspend(ElastigroupProcess.AUTO_HEALING)
        spotinst_client.remove_suspended_process.assert_called_with(
            "sig-12345678", ["AUTO_HEALING"]
        )

    def test_elastigroup_unsuspend_scaling_policy(_, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        elastigroup.unsuspend(ElastigroupProcess.AUTO_SCALE_DOWN)
        spotinst_client.resume_suspended_scaling_policies.assert_called_with(
            "sig-12345678", ["SCALING_POLICY_DOWN_1", "SCALING_POLICY_DOWN_2"]
        )

    @pytest.mark.parametrize("amount", [10, "10%"])
    def test_elastigroup_scale_up(_, amount, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        elastigroup.scale_up(amount)
        spotinst_client.scale_elastigroup_up.assert_called_with("sig-12345678", 10)

    @pytest.mark.parametrize("amount", [10, "10%"])
    def test_elastigroup_scale_down(_, amount, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        elastigroup.scale_down(amount)
        spotinst_client.scale_elastigroup_down.assert_called_with("sig-12345678", 10)

    @pytest.mark.parametrize(
        "capacity",
        [
            {"minimum": 0},
            {"maximum": 100},
            {"target": 50},
            {"minimum": 0, "maximum": 100, "target": 50},
        ],
    )
    def test_elastigroup_set_capacity(_, capacity, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        elastigroup.set_capacity(capacity)
        spotinst_client.update_elastigroup.assert_called_with(
            {"capacity": capacity}, "sig-12345678"
        )

    def test_elastigroup_get_status(_, arrange_elastigroup):
        spotinst_client, elastigroup = arrange_elastigroup
        status_expected = {
            "id": "sig-12345678",
            "name": "test-elastigroup",
            "capacity": {"minimum": 0, "maximum": 200, "target": 100},
            "processes": {
                "AUTO_SCALE": "active",
                "AUTO_HEALING": "suspended",
                "OUT_OF_STRATEGY": "active",
                "PREVENTIVE_REPLACEMENT": "active",
                "REVERT_PREFERRED": "active",
                "SCHEDULING": "active",
                "AUTO_SCALE_DOWN": "suspended",
                "AUTO_SCALE_UP": "active",
            },
        }
        status_received = elastigroup.status
        spotinst_client.get_elastigroup.assert_called_with("sig-12345678")
        spotinst_client.list_suspended_process.assert_called_with("sig-12345678")
        spotinst_client.list_suspended_scaling_policies.assert_called_with(
            "sig-12345678"
        )
        assert status_received == status_expected
