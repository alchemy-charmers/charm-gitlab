"""Provides the main reactive layer for the GitLab charm."""

from charmhelpers import fetch
from charmhelpers.core import hookenv

from charms.reactive import (
    clear_flag,
    endpoint_from_flag,
    endpoint_from_name,
    is_flag_set,
    set_flag,
    when,
    when_all,
    when_any,
    when_none,
    when_not,
)

from libgitlab import GitlabHelper

gitlab = GitlabHelper()

HEALTHY = "GitLab installed and configured"


@when("pgsql.database.connected")
def set_pgsql_db():
    """Set PostgreSQL database name, so the related charm will create the DB for us."""
    hookenv.log("Requesting gitlab DB from {}".format(hookenv.remote_unit()))
    pgsql = endpoint_from_flag("postgresql.database.connected")
    pgsql.set_database("gitlab")


@when_any("db.departed", "pgsql.departed")
def remove_db():
    """Remove the DB configuration when the relation has been removed."""
    hookenv.status_set("maintenance", "Cleaning up removed database relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))
    if is_flag_set("pgsql.database.available") or is_flag_set("db.connected"):
        hookenv.log(
            "Ignoring request to remove config for {}, there is still another DB related".format(
                hookenv.remote_unit()
            )
        )
    else:
        gitlab.remove_db_conf()


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


@when("pgsql.database.connected")
@when_not("pgsql.database.available")
def wait_pgsql():
    """Update charm status while waiting for PostgreSQL to be ready."""
    hookenv.status_set("blocked", "Waiting for PostgreSQL database")


@when("gitlab.installed")
@when_none("db.connected", "pgsql.database.available")
@when("endpoint.redis.available")
def missing_db_relation():
    """Complains if either database relation is missing, but not the Redis one."""
    hookenv.status_set("blocked", "Missing relation to either PostgreSQL or MySQL")


@when("gitlab.installed")
@when_any("db.connected", "pgsql.database.available")
@when_not("endpoint.redis.available")
def missing_redis_relation():
    """Complains if the Redis relation is missing, but not the DB ones."""
    hookenv.status_set("blocked", "Missing relation to Redis")


@when("gitlab.installed")
@when_none("db.available", "pgsql.database.available", "endpoint.redis.available")
def missing_all_relations():
    """Complain when neither the Redis or DB relations are related."""
    hookenv.status_set(
        "blocked", "Missing relation to Redis and either PostgreSQL or MySQL"
    )


@when_all("gitlab.installed", "endpoint.redis.available")
@when_any("db.available", "pgsql.database.available")
@when_any(
    "config.changed", "db.changed", "pgsql.database.changed", "endpoint.redis.changed"
)
def configure_gitlab(reverseproxy, *args):
    """Reconfigured GitLab on configuration changes.

    Templates the GitLab Omnibus configuration file, rerunning the OmniBus
    installer to handle actual configuration.
    """
    hookenv.status_set("maintenance", "Configuring GitLab")
    hookenv.log(
        ("Configuring GitLab, then running gitlab-ctl " "reconfigure on changes")
    )

    redis = endpoint_from_flag("endpoint.redis.available")
    if redis:
        gitlab.save_redis_conf(redis)

    if is_flag_set("pgsql.database.available"):
        db = endpoint_from_flag("pgsql.database.available")
        hookenv.log("Detected PostgreSQL database during configure")
    else:
        db = endpoint_from_flag("db.available")
        hookenv.log("Detected MySQL database during configure")

    if db:
        hookenv.log("Found DB configuration provided from endpoint: {}".format(db))
        gitlab.save_db_conf(db)

    if gitlab.db_configured() and gitlab.redis_configured():
        hookenv.log("Running GitLab configuration/install")
        if gitlab.configure():
            hookenv.status_set("active", HEALTHY)
    else:
        hookenv.log("DB and/or Redis unconfigured, skipping install.")


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
