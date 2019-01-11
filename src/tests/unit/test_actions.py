import imp

import mock


class TestActions():
    def test_example_action(self, libgitlab, monkeypatch):
        mock_function = mock.Mock()
        monkeypatch.setattr(libgitlab, 'action_function', mock_function)
        assert mock_function.call_count == 0
        imp.load_source('action_function', './actions/example-action')
        assert mock_function.call_count == 1
