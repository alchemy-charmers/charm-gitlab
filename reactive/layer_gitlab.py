"""Provides the main reactive layer for the GitLab charm."""

import socket
import subprocess

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


@when_any("pgsql.departed")
def remove_pgsql():
    """Remove the PostgreSQL DB configuration when the relation has been removed."""
    hookenv.status_set("maintenance", "Cleaning up removed pgsql relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))
    gitlab.remove_pgsql_conf()


@when_any("db.departed")
def remove_mysql():
    """Remove the Legacy MySQL DB configuration when the relation has been removed."""
    hookenv.status_set("maintenance", "Cleaning up legacy MySQL relation")
    hookenv.log("Removing config for: {}".format(hookenv.remote_unit()))
    gitlab.remove_mysql_conf()


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
    hookenv.status_set("maintenance", "Installing GitLab")
    gitlab.upgrade_gitlab()
    hookenv.status_set("active", "GitLab Installed")
    set_flag("gitlab.installed")


@when("pgsql.database.connected")
@when_not("pgsql.database.available")
def wait_pgsql():
    """Update charm status while waiting for PostgreSQL to be ready."""
    hookenv.status_set("blocked", "Waiting for PostgreSQL database")


@when("gitlab.installed")
@when_not("pgsql.database.available")
@when("endpoint.redis.available")
def missing_db_relation():
    """Complains if either database relation is missing, but not the Redis one."""
    hookenv.status_set("blocked", "Missing relation to PostgreSQL")


@when("gitlab.installed")
@when_any("db.connected", "pgsql.database.available")
@when_not("endpoint.redis.available")
def missing_redis_relation():
    """Complains if the Redis relation is missing, but not the DB ones."""
    hookenv.status_set("blocked", "Missing relation to Redis")


@when("gitlab.installed")
@when_none("pgsql.database.available", "endpoint.redis.available")
def missing_all_relations():
    """Complain when neither the Redis or DB relations are related."""
    hookenv.status_set("blocked", "Missing relation to Redis and PostgreSQL")


@when_all("gitlab.installed", "endpoint.redis.available")
@when_any("db.available", "pgsql.database.available")
@when_any(
    "config.changed", "db.changed", "pgsql.database.changed", "endpoint.redis.changed"
)
def configure_gitlab(reverseproxy, *args):
    """Upgrade and reconfigure GitLab on configuration changes.

    Templates the GitLab Omnibus configuration file, rerunning the OmniBus
    installer to handle actual configuration.
    """
    # These interfaces don't clear their changed status
    clear_flag("db.changed")
    clear_flag("pgsql.database.changed")
    clear_flag("endpoint.redis.changed")

    hookenv.status_set("maintenance", "Configuring GitLab")
    hookenv.log(
        ("Configuring GitLab, then running gitlab-ctl " "reconfigure on changes")
    )

    redis = endpoint_from_flag("endpoint.redis.available")
    if redis:
        gitlab.save_redis_conf(redis)

    if (
        is_flag_set("pgsql.database.available")
        and is_flag_set("db.available")
        and gitlab.mysql_migrated()
    ):
        hookenv.log(
            "Both PostgreSQL and MySQL related, and migration complet. Please remove MySQL relation to continue."
        )
        hookenv.status_set(
            "blocked",
            "Both PostgreSQL and MySQL related, and migration complet. Please remove MySQL relation to continue.",
        )
        return
    elif (
        is_flag_set("pgsql.database.available")
        and is_flag_set("db.available")
        and not gitlab.mysql_migrated()
    ):
        mysql = endpoint_from_flag("db.available")
        pgsql = endpoint_from_flag("pgsql.database.available")
        hookenv.log(
            "Both PostgreSQL and MySQL related, run migrate-db action and then remve MySQL relation to finish setup."
        )
        hookenv.status_set(
            "blocked",
            "Both PgSQL and MySQL related. Please refer to the charm README on how to finish migration.",
        )
        gitlab.save_mysql_conf(mysql)
        gitlab.save_pgsql_conf(pgsql)
        return
    elif is_flag_set("pgsql.database.available") and not is_flag_set("db.available"):
        pgsql = endpoint_from_flag("pgsql.database.available")
        hookenv.log("Detected PostgreSQL database during configure")
        gitlab.save_pgsql_conf(pgsql)
    elif is_flag_set("db.available") and not is_flag_set("pgsql.database.available"):
        mysql = endpoint_from_flag("db.available")
        hookenv.log(
            "MySQL unsupported. Please relate this service to a healthy PostgreSQL cluster using the db-admin relation."
        )
        gitlab.save_mysql_conf(mysql)
        hookenv.status_set(
            "blocked", "MySQL unsupported. Please migrate to PostgreSQL."
        )
        return

    if gitlab.pgsql_configured() and gitlab.redis_configured():
        hookenv.log("Running GitLab configuration/install")
        if gitlab.configure():
            hookenv.status_set("active", HEALTHY)
            set_flag("gitlab.configured")
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


def get_runner_token():
    """Get the runner token for registering a runner."""
    cmd = [
        "/usr/bin/gitlab-rails",
        "runner",
        "-e",
        "production",
        "STDOUT.write Gitlab::CurrentSettings.current_application_settings.runners_registration_token"
    ]
    token = subprocess.check_output(cmd)
    return token.decode("utf-8")


@when_all("endpoint.runner.joined", "gitlab.configured")
@when_not("runner.published")
def publish_runner_config():
    """Publish the configuration for a runner to register."""
    endpoint = endpoint_from_flag("endpoint.runner.joined")
    if gitlab.charm_config["runners_bypass_proxy"]:
        server_uri = "http://{}".format(socket.getfqdn())
    else:
        server_uri = gitlab.get_external_uri()
    server_token = get_runner_token()
    hookenv.log(
        "Publishing runner config uri/token: {}/{}".format(server_uri, server_token),
        "DEBUG",
    )
    endpoint.publish(server_uri, server_token)
    set_flag("runner.published")


@when("endpoint.runner.departed")
def handle_runner_departed():
    """Handle relations departed."""
    clear_flag("runner.published")
