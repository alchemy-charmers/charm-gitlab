"""Provides the main reactive layer for the GitLab charm."""

from charmhelpers import fetch
from charmhelpers.core import hookenv

from charms.reactive import (
    clear_flag,
    endpoint_from_flag,
    endpoint_from_name,
    set_flag,
    when,
    when_all,
    when_any,
    when_not,
)

from libgitlab import GitlabHelper

gitlab = GitlabHelper()

HEALTHY = "GitLab installed and configured"


@when_not("gitlab.installed")
def install_gitlab():
    """Installs GitLab based on configured version."""
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
    """Complains if the MySQL relation is missing, but not the Redis one."""
    hookenv.status_set("blocked", "Missing relation to MySQL")


@when("gitlab.installed")
@when("db.available")
@when_not("endpoint.redis.available")
def missing_redis_relation():
    """Complains if the Redis relation is missing, but not the MySQL one."""
    hookenv.status_set("blocked", "Missing relation to Redis")


@when("gitlab.installed")
@when_not("db.available")
@when_not("endpoint.redis.available")
def missing_all_relations():
    """Complain when neither the Redis or MySQL relations are related."""
    hookenv.status_set("blocked", "Missing relation to MySQL and Redis")


@when_all("gitlab.installed", "db.available", "endpoint.redis.available")
@when_not("db.connected")
def waiting():
    """Complain when the database relation is still completing."""
    hookenv.status_set(
        "blocked", "DB and Redis related, waiting for MySQL relation to complete"
    )


@when_all(
    "gitlab.installed", "db.available", "db.connected", "endpoint.redis.available"
)
@when_any("config.changed", "db.changed", "endpoint.redis.changed")
def configure_gitlab(reverseproxy, *args):
    """Reconfigured GitLab on configuration changes.

    Templates the GitLab Omnibus configuration file, rerunning the OmniBus
    installer to handle actual configuration.
    """
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
    """Remove the MySQL configuration when the relation has been removed."""
    hookenv.status_set("maintenance", "Cleaning up removed MySQL relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))

    gitlab.remove_mysql_conf()

    hookenv.status_set("active", HEALTHY)


@when("endpoint.redis.departed")
def remove_redis():
    """Remove the Redis configuration when the relation has been removed."""
    hookenv.status_set("maintenance", "Cleaning up removed Redis relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))

    gitlab.remove_redis_conf()

    hookenv.status_set("active", HEALTHY)


@when("reverseproxy.departed")
def remove_proxy():
    """Remove the haproxy configuration when the relation is removed."""
    hookenv.status_set("maintenance", "Removing reverse proxy relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))

    hookenv.status_set("active", HEALTHY)
    clear_flag("reverseproxy.configured")


@when("reverseproxy.ready")
@when_not("reverseproxy.configured")
def configure_proxy():
    """Configure reverse proxy settings when haproxy is related."""
    hookenv.status_set("maintenance", "Applying reverse proxy configuration")
    hookenv.log("Configuring reverse proxy via: {}".format(hookenv.remote_unit()))

    interface = endpoint_from_name("reverseproxy")
    gitlab.configure_proxy(interface)

    hookenv.status_set("active", HEALTHY)
    set_flag("reverseproxy.configured")
