#!/usr/bin/python3
"""Configure testing session for unit testing charm."""
import mock

import pytest

from charmhelpers.core import unitdata

# If layer options are used, add this to libgitlab
# and import layer in libgitlab
@pytest.fixture
def mock_layers(monkeypatch):
    """Mock charm layer inclusion."""
    import sys

    sys.modules["charms.layer"] = mock.Mock()
    sys.modules["reactive"] = mock.Mock()
    # Mock any functions in layers that need to be mocked here

    def options(layer):
        # mock options for layers here
        if layer == "example-layer":
            options = {"port": 9999}
            return options
        else:
            return None

    monkeypatch.setattr("libgitlab.layer.options", options)


@pytest.fixture
def mock_hookenv_config(monkeypatch):
    """Mock charm hook environment items like charm configuration."""
    import yaml

    def mock_config():
        cfg = {}
        yml = yaml.safe_load(open("./config.yaml"))

        # Load all defaults
        for key, value in yml["options"].items():
            cfg[key] = value["default"]

        # Manually add cfg from other layers
        # cfg['my-other-layer'] = 'mock'
        return cfg

    monkeypatch.setattr("libgitlab.hookenv.config", mock_config)


@pytest.fixture
def mock_remote_unit(monkeypatch):
    """Mock the remote unit name for charm in test."""
    monkeypatch.setattr("libgitlab.hookenv.remote_unit", lambda: "unit-mock/0")


@pytest.fixture
def mock_charm_dir(monkeypatch):
    """Mock the charm directory for charm in test."""
    monkeypatch.setattr("libgitlab.hookenv.charm_dir", lambda: ".")


@pytest.fixture
def mock_get_installed_version(monkeypatch):
    """Mock the installed version."""
    installed_version = mock.Mock()
    installed_version.return_value = "1.1.1"
    monkeypatch.setattr(
        "libgitlab.GitlabHelper.get_installed_version", installed_version
    )


@pytest.fixture
def mock_get_latest_version(monkeypatch):
    """Mock get_latest_version."""
    latest_version = mock.Mock()
    latest_version.return_value = "1.1.1"
    monkeypatch.setattr("libgitlab.GitlabHelper.get_latest_version", latest_version)


@pytest.fixture
def mock_upgrade_package(
    mock_get_installed_version, mock_get_latest_version, monkeypatch
):
    """Mock the upgrade_package function and set the installed versions.

    When a wildcard is provided the minor and patch are set to 1
    """

    def mock_upgrade(self, version=None):
        if version:
            sane_version = version.replace("*", "1.1")
            self.get_installed_version.return_value = sane_version
        else:
            self.get_installed_version.return_value = self.get_latest_version()

    monkeypatch.setattr("libgitlab.GitlabHelper.upgrade_package", mock_upgrade)


@pytest.fixture
def mock_gitlab_hookenv_log(monkeypatch):
    """Mock hookenv.log."""
    mock_log = mock.Mock()
    monkeypatch.setattr("libgitlab.hookenv.log", mock_log)
    return mock_log


@pytest.fixture
def mock_gitlab_host(monkeypatch):
    """Mock host import on libgitlab."""
    mock_host = mock.Mock()
    monkeypatch.setattr("libgitlab.host", mock_host)
    return mock_host


@pytest.fixture
def mock_gitlab_get_flag_value(monkeypatch):
    """Mock _get_flag_value on libgitlab."""
    mock_flag_value = mock.Mock()
    mock_flag_value.return_value = None
    monkeypatch.setattr("libgitlab._get_flag_value", mock_flag_value)
    return mock_flag_value


@pytest.fixture
def mock_gitlab_socket(monkeypatch):
    """Mock socket import on libgitlab."""
    mock_socket = mock.Mock()
    mock_socket.getfqdn = mock.Mock()
    mock_socket.getfqdn.return_value = "mock.example.com"
    monkeypatch.setattr("libgitlab.socket", mock_socket)
    return mock_socket


@pytest.fixture
def mock_gitlab_fetch(monkeypatch):
    """Mock fetch import on libgitlab."""
    mock_fetch = mock.Mock()
    monkeypatch.setattr("libgitlab.fetch", mock_fetch)
    return mock_fetch


@pytest.fixture
def mock_gitlab_subprocess(monkeypatch):
    """Mock subprocess import on libgitlab."""
    mock_subprocess = mock.Mock()
    monkeypatch.setattr("libgitlab.subprocess", mock_subprocess)
    return mock_subprocess


@pytest.fixture
def mock_template(monkeypatch):
    monkeypatch.setattr("libgitlab.templating.host.os.fchown", mock.Mock())
    monkeypatch.setattr("libgitlab.templating.host.os.chown", mock.Mock())
    monkeypatch.setattr("libgitlab.templating.host.os.fchmod", mock.Mock())


@pytest.fixture
def mock_unit_db(monkeypatch):
    mock_kv = mock.Mock()
    mock_kv.return_value = unitdata.Storage(path=":memory:")
    monkeypatch.setattr("libgitlab.unitdata.kv", mock_kv)


@pytest.fixture
def libgitlab(
    tmpdir,
    mock_hookenv_config,
    mock_charm_dir,
    mock_upgrade_package,
    mock_gitlab_socket,
    mock_gitlab_fetch,
    mock_template,
    mock_gitlab_subprocess,
    mock_unit_db,
    monkeypatch,
):
    """Mock important aspects of the charm helper library for operation during unit testing."""
    from libgitlab import GitlabHelper

    gitlab = GitlabHelper()

    # Example config file patching
    cfg_file = tmpdir.join("example.cfg")
    with open("./tests/unit/example.cfg", "r") as src_file:
        cfg_file.write(src_file.read())
    gitlab.example_config_file = cfg_file.strpath

    commands_file = tmpdir.join("commands.load")
    gitlab.gitlab_commands_file = commands_file.strpath
    config_file = tmpdir.join("gitlab.rb")
    gitlab.gitlab_config = config_file.strpath

    # Mock host functions not appropriate for unit testing
    gitlab.fetch_gitlab_apt_package = mock.Mock()
    gitlab.gitlab_reconfigure_run = mock.Mock()

    # Any other functions that load the helper will get this version
    monkeypatch.setattr("libgitlab.GitlabHelper", lambda: gitlab)

    return gitlab
