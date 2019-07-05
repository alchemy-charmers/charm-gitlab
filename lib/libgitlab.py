"""The helper library for the GitLab charm.

Provides the majority of the logic in the charm, specifically all logic which
can be meaningfully unit tested.
"""
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

import socket
import subprocess

from charmhelpers.core import hookenv, host, templating, unitdata

from charms.reactive.helpers import any_file_changed


class GitlabHelper:
    """The GitLab helper class.

    Provides helper functions and implements the actual logic of the GitLab
    charm. Used and called from the Reactive charm layer and unit tests.
    """

    def __init__(self):
        """Load hookenv key/value store and charm configuration."""
        self.charm_config = hookenv.config()
        self.kv = unitdata.kv()

    def action_function(self):
        """Stub function for the example action."""
        return True

    def restart(self):
        """Restart the GitLab service."""
        host.service_restart("gitlab")
        return True

    def get_external_uri(self):
        """Return the configured external URL from Charm configuration."""
        configured_value = self.charm_config["external_url"]
        if configured_value:
            return configured_value
        else:
            fqdn = "http://{}".format(socket.getfqdn())
            return fqdn

    def get_sshhost(self):
        """Return the host used when configuring SSH access to GitLab."""
        url = urlparse(self.get_external_uri())

        if url.hostname:
            return url.hostname
        else:
            return socket.getfqdn

    def configure_proxy(self, proxy):
        """Configure GitLab for operation behind a reverse proxy."""
        url = urlparse(self.get_external_uri())

        if url.scheme == "https":
            port = 443
        else:
            port = 80

        proxy_config = [
            {
                "mode": "http",
                "external_port": port,
                "internal_host": socket.getfqdn(),
                "internal_port": self.charm_config["http_port"],
                "subdomain": url.hostname,
            },
            {
                "mode": "tcp",
                "external_port": self.charm_config["ssh_port"],
                "internal_host": socket.getfqdn(),
                "internal_port": 22,
            },
        ]
        proxy.configure(proxy_config)

    def mysql_configured(self):
        """Determine if we have legacy MySQL DB configuration present."""
        if (
            self.kv.get("mysql_host")
            and self.kv.get("mysql_port")
            and self.kv.get("mysql_db")
            and self.kv.get("mysql_user")
            and self.kv.get("mysql_pass")
        ):
            return True
        return False

    def migrate_db_config(self):
        """Migrate legacy MySQL configuration to new DB configuration in KV store."""
        if self.mysql_configured():
            self.kv.set("db_host", self.kv.get("mysql_host"))
            self.kv.set("db_port", self.kv.get("mysql_port"))
            self.kv.set("db_db", self.kv.get("mysql_db"))
            self.kv.set("db_user", self.kv.get("mysql_user"))
            self.kv.set("db_pass", self.kv.get("mysql_pass"))
            self.kv.set("db_adapter", "mysql2")
            self.remove_mysql_conf()

    def db_configured(self):
        """Determine if we have all requried DB configuration present."""
        if (
            self.kv.get("db_host")
            and self.kv.get("db_port")
            and self.kv.get("db_db")
            and self.kv.get("db_user")
            and self.kv.get("db_pass")
            and self.kv.get("db_adapter")
        ):
            hookenv.log("The DB is related and configured in the charm KV store", hookenv.DEBUG)
            return True
        return False

    def redis_configured(self):
        """Determine if Redis is related and the KV has been updated with configuration"""
        if (
            self.kv.get("redis_host")
            and self.kv.get("redis_port")
        ):
            hookenv.log("Redis is related and configured in the charm KV store", hookenv.DEBUG)
            return True
        return False

    def remove_mysql_conf(self):
        """Remove legacy MySQL configuraion from the unit KV store."""
        # legacy kv to clean up
        self.kv.unset("mysql_host")
        self.kv.unset("mysql_port")
        self.kv.unset("mysql_db")
        self.kv.unset("mysql_user")
        self.kv.unset("mysql_pass")

    def remove_db_conf(self):
        """Remove the MySQL configuration from the unit KV store."""
        self.kv.unset("db_host")
        self.kv.unset("db_port")
        self.kv.unset("db_db")
        self.kv.unset("db_user")
        self.kv.unset("db_pass")
        self.kv.unset("db_adapter")
        if self.mysql_configured():
            self.remove_mysql_conf()

    def save_db_conf(self, db):
        """Configure GitLab with knowledge of a related PostgreSQL endpoint."""
        hookenv.log(db, hookenv.DEBUG)
        if db:
            if hasattr(db, 'relation_name') and db.relation_name == "db":
                hookenv.log("Detected related MySQL database: {}".format(db), hookenv.DEBUG)
                self.kv.set("db_adapter", "mysql2")
                self.kv.set("db_host", db.host())
                self.kv.set("db_port", db.port())
                self.kv.set("db_db", db.database())
                self.kv.set("db_user", db.user())
                self.kv.set("db_pass", db.password())
            elif hasattr(db, 'master') and db.master:
                hookenv.log("Detected related PostgreSQL database: {}".format(db.master), hookenv.DEBUG)
                self.kv.set("db_adapter", "postgresql")
                self.kv.set("db_host", db.master.host)
                self.kv.set("db_port", db.master.port)
                self.kv.set("db_db", db.master.dbname)
                self.kv.set("db_user", db.master.user)
                self.kv.set("db_pass", db.master.password)

    def save_redis_conf(self, endpoint):
        """Configure GitLab with knowledge of a related Redis instance."""
        redis = endpoint.relation_data()[0]
        self.kv.set("redis_host", redis["host"])
        self.kv.set("redis_port", redis["port"])
        if redis.get("password"):
            self.kv.set("redis_pass", redis["password"])
        else:
            self.kv.unset("redis_pass")

    def remove_redis_conf(self):
        """Remove Redis configuation from the unit KV store."""
        self.kv.unset("redis_host")
        self.kv.unset("redis_port")
        self.kv.unset("redis_pass")

    def configure(self):
        """Configure GitLab.

        Templates the configuration of the GitLab omnibus installer and
        runs the configuration routine to configure and start related services
        based on charm configuration and relation data.
        """
        self.migrate_db_config()

        hookenv.log(self.kv, hookenv.DEBUG)
        templating.render(
            "gitlab.rb.j2",
            "/etc/gitlab/gitlab.rb",
            {
                "db_adapter": self.kv.get("db_adapter"),
                "db_host": self.kv.get("db_host"),
                "db_port": self.kv.get("db_port"),
                "db_database": self.kv.get("db_db"),
                "db_user": self.kv.get("db_user"),
                "db_password": self.kv.get("db_pass"),
                "redis_host": self.kv.get("redis_host"),
                "redis_port": self.kv.get("redis_port"),
                "http_port": self.charm_config["http_port"],
                "ssh_host": self.get_sshhost(),
                "url": self.get_external_uri(),
            },
        )

        if any_file_changed(["/etc/gitlab/gitlab.rb"]):
            subprocess.check_call("/usr/bin/gitlab-ctl reconfigure", shell=True)

        # TODO: ensure service is enabled
        # TODO: start service
        # TODO: check service is running
        return True
