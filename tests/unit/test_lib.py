#!/usr/bin/python3
"""Test helper library usage."""

import mock

from charmhelpers.core import unitdata
from mock import call


def test_pytest():
    """Test pytest actually tests."""
    assert True


def test_gitlab(libgitlab):
    """See if the helper fixture works to load charm configs."""
    assert isinstance(libgitlab.charm_config, dict)


def test_gitlab_kv(libgitlab):
    """See if the unitdata kv helper is loaded."""
    assert isinstance(libgitlab.kv, unitdata.Storage)


def test_set_package_name(libgitlab):
    "Test set_package_name"
    libgitlab.set_package_name("not-ee")
    assert libgitlab.package_name == "gitlab-ce"
    libgitlab.set_package_name("gitlab-ee")
    assert libgitlab.package_name == "gitlab-ee"


def test_restart(libgitlab, mock_gitlab_host):
    "Test restart"
    libgitlab.restart()
    assert mock_gitlab_host.service_restart.called
    assert mock_gitlab_host.service_restart.call_args == call("gitlab")


def test_get_external_uri(libgitlab):
    "Test get_external_uri"
    result = libgitlab.get_external_uri()
    assert result == "http://mock.example.com"
    libgitlab.charm_config["external_url"] = "foo.bar.com"
    result = libgitlab.get_external_uri()
    assert result == "foo.bar.com"


def test_get_sshhost(libgitlab):
    "Test get_sshhost."
    result = libgitlab.get_sshhost()
    assert result == "mock.example.com"
    libgitlab.charm_config["external_url"] = "foo.bar.com"
    result = libgitlab.get_sshhost()
    assert result == "mock.example.com"


def test_get_sshport(libgitlab, mock_gitlab_get_flag_value):
    "Test get_sshport."
    result = libgitlab.get_sshport()
    assert result == "22"
    mock_gitlab_get_flag_value.return_value = True
    result = libgitlab.get_sshport()
    assert result == libgitlab.charm_config["ssh_port"]


def test_configure_proxy(libgitlab):
    "Test configure_proxy"
    # Test HTTP
    mock_proxy = mock.Mock()
    libgitlab.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == call(
        [
            {
                "mode": "http",
                "external_port": 80,
                "internal_host": "mock.example.com",
                "internal_port": 80,
                "subdomain": "mock.example.com",
            },
            {
                "mode": "tcp",
                "external_port": 222,
                "internal_host": "mock.example.com",
                "internal_port": 22,
            },
        ]
    )

    # Test HTTPS
    mock_proxy.reset_mock()
    libgitlab.charm_config["external_url"] = "https://mock.example.com"
    libgitlab.configure_proxy(mock_proxy)
    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == call(
        [
            {
                "mode": "http",
                "external_port": 443,
                "internal_host": "mock.example.com",
                "internal_port": 80,
                "subdomain": "mock.example.com",
            },
            {
                "mode": "tcp",
                "external_port": 222,
                "internal_host": "mock.example.com",
                "internal_port": 22,
            },
        ]
    )


def test_mysql_configured(libgitlab):
    "Test mysql_configured"
    assert libgitlab.mysql_configured() is False
    libgitlab.kv.set("mysql_host", "mock")
    libgitlab.kv.set("mysql_port", "mock")
    libgitlab.kv.set("mysql_db", "mock")
    libgitlab.kv.set("mysql_user", "mock")
    libgitlab.kv.set("mysql_pass", "mock")
    assert libgitlab.mysql_configured() is True


def test_legacy_db_configured(libgitlab):
    "Test legacy_db_configured."
    assert libgitlab.legacy_db_configured() is False
    libgitlab.kv.set("db_host", "mock")
    libgitlab.kv.set("db_port", "mock")
    libgitlab.kv.set("db_db", "mock")
    libgitlab.kv.set("db_user", "mock")
    libgitlab.kv.set("db_pass", "mock")
    assert libgitlab.legacy_db_configured() is True


def test_upgrade_gitlab_noop(libgitlab):
    """Test the noop path."""
    result = libgitlab.upgrade_gitlab()
    assert result is False


def test_upgrade_gitlab_minor(libgitlab, mock_gitlab_hookenv_log):
    """Test the upgrade path."""
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
    """Test the upgrade path."""
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
    """Test the upgrade path."""
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
