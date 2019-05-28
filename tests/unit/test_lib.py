#!/usr/bin/python3

from charmhelpers.core import unitdata


class TestLib:
    def test_pytest(self):
        assert True

    def test_gitlab(self, libgitlab):
        """ See if the helper fixture works to load charm configs """
        assert isinstance(libgitlab.charm_config, dict)

    def test_gitlab_kv(self, libgitlab):
        """ See if the unitdata kv helper is loaded """
        assert isinstance(libgitlab.kv, unitdata.Storage)

    # Include tests for functions in libgitlab
