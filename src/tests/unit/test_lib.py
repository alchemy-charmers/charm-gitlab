#!/usr/bin/python3


class TestLib():
    def test_pytest(self):
        assert True

    def test_gitlab(self, libgitlab):
        ''' See if the helper fixture works to load charm configs '''
        assert isinstance(libgitlab.charm_config, dict)

    # Include tests for functions in libgitlab
