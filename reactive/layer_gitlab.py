from charmhelpers.core import hookenv
from charms.reactive import (
    when_not,
    when_all,
    when_any,
    when,
    clear_flag,
    set_flag,
    endpoint_from_flag,
    endpoint_from_name,
)
from charmhelpers import fetch
from libgitlab import GitlabHelper

gitlab = GitlabHelper()

HEALTHY = "GitLab installed and configured"


@when_not("gitlab.installed")
def install_gitlab():
    version = hookenv.config("version")

    hookenv.status_set("maintenance", "Installing GitLab")
    fetch.configure_sources(update=True, sources_var="apt_repo", keys_var="apt_key")
    if version:
        fetch.apt_install("gitlab-ee=".format(version), fatal=True)
    else:
        fetch.apt_install("gitlab-ee", fatal=True)

    hookenv.status_set("active", "GitLab Installed")
    set_flag("gitlab.installed")


@when("gitlab.installed")
@when_not("db.available")
@when("endpoint.redis.available")
def missing_mysql_relation():
    hookenv.status_set("blocked", "Missing relation to MySQL")


@when("gitlab.installed")
@when("db.available")
@when_not("endpoint.redis.available")
def missing_redis_relation():
    hookenv.status_set("blocked", "Missing relation to Redis")


@when("gitlab.installed")
@when_not("db.available")
@when_not("endpoint.redis.available")
def missing_all_relations():
    hookenv.status_set("blocked", "Missing relation to MySQL and Redis")


@when_all("gitlab.installed", "db.available", "endpoint.redis.available")
@when_not("db.connected")
def waiting():
    hookenv.status_set(
        "blocked", "DB and Redis related, waiting for MySQL relation to complete"
    )


@when_all(
    "gitlab.installed", "db.available", "db.connected", "endpoint.redis.available"
)
@when_any("config.changed", "db.changed", "endpoint.redis.changed")
def configure_gitlab(reverseproxy, *args):
    hookenv.status_set("maintenance", "Configuring GitLab")
    hookenv.log(
        ("Configuring GitLab, then running gitlab-ctl " "reconfigure on changes")
    )

    mysql = endpoint_from_flag("db.available")
    gitlab.save_mysql_conf(mysql)

    redis = endpoint_from_flag("endpoint.redis.available")
    gitlab.save_redis_conf(redis)

    gitlab.configure()

    hookenv.status_set("active", HEALTHY)


@when("db.departed")
def remove_mysql():
    hookenv.status_set("maintenance", "Cleaning up removed MySQL relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))

    gitlab.remove_mysql_conf()

    hookenv.status_set("active", HEALTHY)


@when("endpoint.redis.departed")
def remove_redis():
    hookenv.status_set("maintenance", "Cleaning up removed Redis relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))

    gitlab.remove_redis_conf()

    hookenv.status_set("active", HEALTHY)


@when("reverseproxy.departed")
def remove_proxy():
    hookenv.status_set("maintenance", "Removing reverse proxy relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))

    hookenv.status_set("active", HEALTHY)
    clear_flag("reverseproxy.configured")


@when("reverseproxy.ready")
@when_not("reverseproxy.configured")
def configure_proxy():
    hookenv.status_set("maintenance", "Applying reverse proxy configuration")
    hookenv.log("Configuring reverse proxy via: {}".format(hookenv.remote_unit()))

    interface = endpoint_from_name("reverseproxy")
    gitlab.configure_proxy(interface)

    hookenv.status_set("active", HEALTHY)
    set_flag("reverseproxy.configured")
