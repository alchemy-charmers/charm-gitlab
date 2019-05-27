#!/usr/bin/python3
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


# Include tests for functions in libgitlab
