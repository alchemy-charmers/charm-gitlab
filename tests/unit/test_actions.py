import imp
import mock


class TestActions:
    def test_reconfigure_action(self, libgitlab, monkeypatch):
        mock_function = mock.Mock()
        monkeypatch.setattr(libgitlab, "configure", mock_function)
        assert mock_function.call_count == 0
        imp.load_source("configure", "./actions/reconfigure")
        assert mock_function.call_count == 1
