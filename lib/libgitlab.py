# for python 2 & 3 compat
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse

from charmhelpers.core import hookenv, host, templating, unitdata
from charms.reactive.helpers import any_file_changed
import subprocess
import socket


class GitlabHelper:
    def __init__(self):
        self.charm_config = hookenv.config()
        self.kv = unitdata.kv()

    def action_function(self):
        return True

    def restart(self):
        host.service_restart("gitlab")
        return True

    def get_external_uri(self):

        configured_value = self.charm_config["external_url"]
        if configured_value:
            return configured_value
        else:
            fqdn = "http://{}".format(socket.getfqdn())
            return fqdn

    def get_sshhost(self):

        url = urlparse(self.get_external_uri())

        if url.hostname:
            return url.hostname
        else:
            return socket.getfqdn

    def configure_proxy(self, proxy):

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

    def save_mysql_conf(self, mysql):
        self.kv.set("mysql_host", mysql.host())
        self.kv.set("mysql_port", mysql.port())
        self.kv.set("mysql_db", mysql.database())
        self.kv.set("mysql_user", mysql.user())
        self.kv.set("mysql_pass", mysql.password())

    def remove_mysql_conf(self):
        self.kv.unset("mysql_host")
        self.kv.unset("mysql_port")
        self.kv.unset("mysql_db")
        self.kv.unset("mysql_user")
        self.kv.unset("mysql_pass")

    def save_redis_conf(self, endpoint):
        redis = endpoint.relation_data()[0]
        self.kv.set("redis_host", redis["host"])
        self.kv.set("redis_port", redis["port"])
        if redis.get("password"):
            self.kv.set("redis_pass", redis["password"])
        else:
            self.kv.unset("redis_pass")

    def remove_redis_conf(self):
        self.kv.unset("redis_host")
        self.kv.unset("redis_port")
        self.kv.unset("redis_pass")

    def configure(self):
        hookenv.log(self.kv, hookenv.DEBUG)
        templating.render(
            "gitlab.rb.j2",
            "/etc/gitlab/gitlab.rb",
            {
                "mysql_host": self.kv.get("mysql_host"),
                "mysql_port": self.kv.get("mysql_port"),
                "mysql_database": self.kv.get("mysql_db"),
                "mysql_user": self.kv.get("mysql_user"),
                "mysql_password": self.kv.get("mysql_pass"),
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
