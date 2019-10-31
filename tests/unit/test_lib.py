#!/usr/bin/python3

from mock import call

"""Test helper library usage."""
from charmhelpers.core import unitdata


def test_pytest():
    """Test pytest actually tests."""
    assert True


def test_gitlab(libgitlab):
    """See if the helper fixture works to load charm configs."""
    assert isinstance(libgitlab.charm_config, dict)


def test_gitlab_kv(libgitlab):
    """See if the unitdata kv helper is loaded."""
    assert isinstance(libgitlab.kv, unitdata.Storage)


def test_upgrade_gitlab_noop(libgitlab):
    """ Test the noop path """
    result = libgitlab.upgrade_gitlab()
    assert result is False


def test_upgrade_gitlab_minor(libgitlab, mock_gitlab_hookenv_log):
    """ Test the upgrade path """
    # Upgrade to new minor version
    libgitlab.get_installed_version.return_value = "1.1.0"
    result = libgitlab.upgrade_gitlab()
    print(mock_gitlab_hookenv_log.call_args_list)
    calls = [
        call("Processing pending package upgrades for GitLab"),
        call("Found major version 1 for GitLab version 1.1.1"),
        call("Found major version 1 for GitLab version 1.1.0"),
        call("Upgrading GitLab version 1.1.0 to latest in major release 1"),
    ]
    mock_gitlab_hookenv_log.assert_has_calls(calls)
    assert libgitlab.get_installed_version() == "1.1.1"
    assert result is True

    # Don't upgrade if charm_config matches intalled
    mock_gitlab_hookenv_log.reset_mock()
    libgitlab.charm_config["version"] = "1.1.0"
    libgitlab.get_installed_version.return_value = "1.1.0"
    result = libgitlab.upgrade_gitlab()
    assert libgitlab.get_installed_version() == "1.1.0"
    assert result is False


def test_upgrade_gitlab_major(libgitlab, mock_gitlab_hookenv_log):
    """ Test the upgrade path """
    libgitlab.get_installed_version.return_value = "0.0.0"
    result = libgitlab.upgrade_gitlab()
    print(mock_gitlab_hookenv_log.call_args_list)
    calls = [
        call("Processing pending package upgrades for GitLab"),
        call("Found major version 1 for GitLab version 1.1.1"),
        call("Found major version 0 for GitLab version 0.0.0"),
        call("Upgrading GitLab version 0.0.0 to latest in current major release 0"),
        call("Upgrading GitLab version 0.0.0 to latest in next major release 1"),
        call("Found major version 1 for GitLab version 1.1.1"),
        call("Found major version 1 for GitLab version 1.1.1"),
        call("GitLab is already at configured version 1.1.1"),
    ]
    mock_gitlab_hookenv_log.assert_has_calls(calls)
    assert libgitlab.get_installed_version() == "1.1.1"
    assert result is True


def test_upgrade_gitlab_install(libgitlab, mock_gitlab_hookenv_log):
    """ Test the upgrade path """
    libgitlab.get_installed_version.return_value = ""
    result = libgitlab.upgrade_gitlab()
    print(mock_gitlab_hookenv_log.call_args_list)
    calls = [
        call("Processing pending package upgrades for GitLab"),
        call("GitLab is not installed, installing..."),
    ]
    mock_gitlab_hookenv_log.assert_has_calls(calls)
    assert libgitlab.get_installed_version() == "1.1.1"
    assert result is True


# Include tests for functions in libgitlab
