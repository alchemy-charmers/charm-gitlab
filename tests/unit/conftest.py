#!/usr/bin/python3
"""Configure testing session for unit testing charm."""
import mock

import pytest


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
        yml = yaml.load(open("./config.yaml"))

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
    monkeypatch.setattr("libgitlab.hookenv.charm_dir", lambda: "/mock/charm/dir")


@pytest.fixture
def libgitlab(tmpdir, mock_hookenv_config, mock_charm_dir, monkeypatch):
    """Mock important aspects of the charm helper library for operation during unit testing."""
    from libgitlab import GitlabHelper

    gitlab = GitlabHelper()

    # Example config file patching
    cfg_file = tmpdir.join("example.cfg")
    with open("./tests/unit/example.cfg", "r") as src_file:
        cfg_file.write(src_file.read())
    gitlab.example_config_file = cfg_file.strpath

    # Any other functions that load the helper will get this version
    monkeypatch.setattr("libgitlab.GitlabHelper", lambda: gitlab)

    return gitlab
