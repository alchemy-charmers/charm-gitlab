"""Test charm actions."""
import imp

import mock


def test_reconfigure_action(libgitlab, monkeypatch):
    """Test reconfiguration of GitLab."""
    mock_function = mock.Mock()
    monkeypatch.setattr(libgitlab, "configure", mock_function)
    assert mock_function.call_count == 0
    imp.load_source("configure", "./actions/reconfigure")
    assert mock_function.call_count == 1


def test_upgrade_action(libgitlab, monkeypatch):
    """Test reconfiguration of GitLab."""
    mock_function = mock.Mock()
    monkeypatch.setattr(libgitlab, "upgrade_gitlab", mock_function)
    assert mock_function.call_count == 0
    imp.load_source("upgrade_gitlab", "./actions/upgrade")
    assert mock_function.call_count == 1


def test_migrate_db_action(libgitlab, monkeypatch):
    """Test migration of GitLab data."""
    mock_function = mock.Mock()
    monkeypatch.setattr(libgitlab, "migrate_db", mock_function)
    assert mock_function.call_count == 0
    imp.load_source("migratedb", "./actions/migratedb")
    assert mock_function.call_count == 1
