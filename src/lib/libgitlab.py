from charmhelpers.core import hookenv


class GitlabHelper():
    def __init__(self):
        self.charm_config = hookenv.config()

    def action_function(self):
        return True
