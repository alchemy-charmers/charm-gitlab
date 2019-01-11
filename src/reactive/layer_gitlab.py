from libgitlab import GitlabHelper
from charmhelpers.core import hookenv
from charms.reactive import set_flag, when_not
from charmhelpers import fetch

gitlab = GitlabHelper()


@when_not('gitlab.installed')
def install_gitlab():
    hookenv.status_set('maintenance', 'Installing GitLab')
    fetch.configure_sources(update=True,
                            sources_var='apt_repo',
                            keys_var='apt_key')
    fetch.apt_install('gitlab-ee')
    hookenv.status_set('active', 'GitLab Installed')
    set_flag('gitlab.installed')
