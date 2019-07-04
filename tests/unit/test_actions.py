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
