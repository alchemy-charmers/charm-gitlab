#!/usr/bin/python3
"""Test helper library usage."""

import mock
import pytest
from charmhelpers.core import unitdata
from mock import call


def test_pytest():
    """Test pytest actually tests."""
    assert True


def test_gitlab(libgitlab):
    """See if the helper fixture works to load charm configs."""
    assert isinstance(libgitlab.charm_config, dict)


def test_gitlab_kv(libgitlab):
    """See if the unitdata kv helper is loaded."""
    assert isinstance(libgitlab.kv, unitdata.Storage)


def test_set_package_name(libgitlab):
    """Test set_package_name."""
    libgitlab.set_package_name("not-ee")
    assert libgitlab.package_name == "gitlab-ce"
    libgitlab.set_package_name("gitlab-ee")
    assert libgitlab.package_name == "gitlab-ee"


def test_restart(libgitlab, mock_gitlab_host):
    """Test restart."""
    libgitlab.restart()
    assert mock_gitlab_host.service_restart.called
    assert mock_gitlab_host.service_restart.call_args == call("gitlab")


def test_get_external_uri(libgitlab):
    """Test get_external_uri."""
    result = libgitlab.get_external_uri()
    assert result == "http://mock.example.com"
    libgitlab.charm_config["external_url"] = "foo.bar.com"
    result = libgitlab.get_external_uri()
    assert result == "foo.bar.com"


def test_get_sshhost(libgitlab):
    """Test get_sshhost."""
    result = libgitlab.get_sshhost()
    assert result == "mock.example.com"
    libgitlab.charm_config["external_url"] = "foo.bar.com"
    result = libgitlab.get_sshhost()
    assert result == "mock.example.com"


def test_get_sshport(libgitlab, mock_gitlab_get_flag_value):
    """Test get_sshport."""
    result = libgitlab.get_sshport()
    assert result == 22
    libgitlab.charm_config["ssh_port"] = 922
    result = libgitlab.get_sshport()
    assert result == libgitlab.charm_config["ssh_port"]
    mock_gitlab_get_flag_value.return_value = True
    result = libgitlab.get_sshport()
    assert result == libgitlab.charm_config["proxy_ssh_port"]


def test_get_smtp_enabled(libgitlab, mock_gitlab_get_flag_value):
    """Test get_smtp_enabled."""
    result = libgitlab.get_smtp_enabled()
    assert result is False
    libgitlab.charm_config["smtp_server"] = "mocked.smtp.server"
    result = libgitlab.get_smtp_enabled()
    assert result is True


def test_ports(libgitlab, mock_open_port, mock_close_port, mock_opened_ports):
    """Test ports are opened correctly."""
    libgitlab.open_ports()
    assert mock_opened_ports.call_count == 1
    assert mock_open_port.call_count == 1
    assert mock_close_port.call_count == 2
    mock_open_port.assert_has_calls([call("22")])
    mock_opened_ports.reset_mock()
    mock_close_port.reset_mock()
    libgitlab.close_ports()
    assert mock_opened_ports.call_count == 1
    assert mock_close_port.call_count == 3
    mock_close_port.assert_has_calls([call("2222"), call("80"), call("443")])


@pytest.mark.parametrize("external_url", ("https://mock.example.com", ""))
@pytest.mark.parametrize("proxy_ssh_port", (222, 2222))
@pytest.mark.parametrize("ssh_port", (22, 922))
def test_configure_proxy(libgitlab, external_url, proxy_ssh_port, ssh_port):
    """Test configure_proxy."""
    mock_proxy = mock.Mock()
    libgitlab.charm_config["external_url"] = external_url
    libgitlab.charm_config["proxy_ssh_port"] = proxy_ssh_port
    libgitlab.charm_config["ssh_port"] = ssh_port
    libgitlab.configure_proxy(mock_proxy)

    expected_external_http_port = 80
    if external_url.startswith("https"):
        expected_external_http_port = 443

    assert mock_proxy.configure.called
    assert mock_proxy.configure.call_args == call(
        [
            {
                "mode": "http",
                "external_port": expected_external_http_port,
                "internal_host": "mock.example.com",
                "internal_port": 80,
                "subdomain": "mock.example.com",
            },
            {
                "mode": "tcp",
                "external_port": proxy_ssh_port,
                "internal_host": "mock.example.com",
                "internal_port": ssh_port,
            },
        ]
    )


def test_mysql_configured(libgitlab):
    """Test mysql_configured."""
    assert libgitlab.mysql_configured() is False
    libgitlab.kv.set("mysql_host", "mysql_host")
    libgitlab.kv.set("mysql_port", "mysql_port")
    libgitlab.kv.set("mysql_db", "mysql_db")
    libgitlab.kv.set("mysql_user", "mysql_user")
    libgitlab.kv.set("mysql_pass", "mysql_pass")
    assert libgitlab.mysql_configured() is True


def test_legacy_db_configured(libgitlab):
    """Test legacy_db_configured."""
    assert libgitlab.legacy_db_configured() is False
    libgitlab.kv.set("db_host", "db_host")
    libgitlab.kv.set("db_port", "db_port")
    libgitlab.kv.set("db_db", "db_db")
    libgitlab.kv.set("db_user", "db_user")
    libgitlab.kv.set("db_pass", "db_pass")
    assert libgitlab.legacy_db_configured() is True


def test_install_pgloader(libgitlab, mock_apt_install):
    """Test install_pgloader."""
    libgitlab.install_pgloader()
    assert mock_apt_install.called
    assert mock_apt_install.call_args == call("pgloader", fatal=True)


def test_configure_pgloader(libgitlab):
    """Test configure_pgloader."""
    libgitlab.kv.set("mysql_host", "mysql_host")
    libgitlab.kv.set("mysql_port", "mysql_port")
    libgitlab.kv.set("mysql_db", "mysql_db")
    libgitlab.kv.set("mysql_user", "mysql_user")
    libgitlab.kv.set("mysql_pass", "mysql_pass")

    libgitlab.kv.set("pgsql_host", "pgsql_host")
    libgitlab.kv.set("pgsql_port", "pgsql_port")
    libgitlab.kv.set("pgsql_db", "pgsql_db")
    libgitlab.kv.set("pgsql_user", "pgsql_user")
    libgitlab.kv.set("pgsql_pass", "pgsql_pass")

    libgitlab.configure_pgloader()
    with open(libgitlab.gitlab_commands_file, "rb") as commands_file:
        content = commands_file.readlines()
    assert (
        b"     FROM mysql://mysql_user:mysql_pass@mysql_host:mysql_port/mysql_db\n"
        in content
    )
    assert (
        b"     INTO postgresql://pgsql_user:pgsql_pass@pgsql_host:pgsql_port/pgsql_db\n"
        in content
    )
    assert b"ALTER SCHEMA 'mysql_db' RENAME TO 'public'\n" in content


def test_mysql_migrated(libgitlab):
    """Test mysql_migrated."""
    assert libgitlab.mysql_migrated() is False
    libgitlab.kv.set("mysql_migration_run", True)
    assert libgitlab.mysql_migrated() is True


def test_migrate_db(libgitlab):
    """Test migrate_db."""
    # No migration
    libgitlab.install_pgloader = mock.Mock()
    libgitlab.configure_pgloader = mock.Mock()
    libgitlab.run_pgloader = mock.Mock()
    libgitlab.migrate_db()
    assert libgitlab.install_pgloader.call_count == 0
    assert libgitlab.configure_pgloader.call_count == 0
    assert libgitlab.run_pgloader.call_count == 0
    assert not libgitlab.kv.get("mysql_migratin_run")

    # Migration
    libgitlab.kv.set("mysql_host", "mysql_host")
    libgitlab.kv.set("mysql_port", "mysql_port")
    libgitlab.kv.set("mysql_db", "mysql_db")
    libgitlab.kv.set("mysql_user", "mysql_user")
    libgitlab.kv.set("mysql_pass", "mysql_pass")

    libgitlab.kv.set("pgsql_host", "pgsql_host")
    libgitlab.kv.set("pgsql_port", "pgsql_port")
    libgitlab.kv.set("pgsql_db", "pgsql_db")
    libgitlab.kv.set("pgsql_user", "pgsql_user")
    libgitlab.kv.set("pgsql_pass", "pgsql_pass")
    libgitlab.migrate_db()
    assert libgitlab.install_pgloader.call_count == 1
    assert libgitlab.configure_pgloader.call_count == 1
    assert libgitlab.run_pgloader.call_count == 1
    assert libgitlab.kv.get("mysql_migration_run")


def test_migrate_mysql_config(libgitlab):
    """Test migrate_mysql_config."""
    assert not libgitlab.kv.get("db_host", None)
    libgitlab.kv.set("mysql_host", "mysql_host")
    libgitlab.kv.set("mysql_port", "mysql_port")
    libgitlab.kv.set("mysql_db", "mysql_db")
    libgitlab.kv.set("mysql_user", "mysql_user")
    libgitlab.kv.set("mysql_pass", "mysql_pass")
    libgitlab.migrate_mysql_config()
    assert libgitlab.kv.get("db_host") == "mysql_host"


def test_redis_configured(libgitlab):
    """Test redis_configured."""
    assert not libgitlab.redis_configured()
    libgitlab.kv.set("redis_host", "redis_host")
    libgitlab.kv.set("redis_port", "redis_port")
    assert libgitlab.redis_configured()


def test_remove_mysql_conf(libgitlab):
    """Test remove_mysql_conf."""
    libgitlab.kv.set("mysql_host", "mysql_host")
    libgitlab.kv.set("mysql_port", "mysql_port")
    libgitlab.kv.set("mysql_db", "mysql_db")
    libgitlab.kv.set("mysql_user", "mysql_user")
    libgitlab.kv.set("mysql_pass", "mysql_pass")
    libgitlab.remove_mysql_conf()
    assert not libgitlab.kv.get("mysql_host", None)
    assert not libgitlab.kv.get("mysql_port", None)
    assert not libgitlab.kv.get("mysql_db", None)
    assert not libgitlab.kv.get("mysql_user", None)


def test_remove_pgsql_conf(libgitlab):
    """Test remove pgsql_conf."""
    libgitlab.kv.set("db_host", "db_host")
    libgitlab.kv.set("db_port", "db_port")
    libgitlab.kv.set("db_db", "db_db")
    libgitlab.kv.set("db_user", "db_user")
    libgitlab.kv.set("db_pass", "db_pass")
    libgitlab.remove_pgsql_conf()
    assert not libgitlab.kv.get("db_host", None)
    assert not libgitlab.kv.get("db_port", None)
    assert not libgitlab.kv.get("db_db", None)
    assert not libgitlab.kv.get("db_user", None)


def test_save_pgsql_conf(libgitlab):
    """Test save_pgsql_conf."""
    db = mock.Mock()
    master = mock.Mock()
    master.host = "host"
    master.port = "port"
    master.dbname = "dbname"
    master.user = "user"
    master.password = "password"
    db.master = master
    libgitlab.save_pgsql_conf(db)
    assert libgitlab.kv.get("pgsql_host") == "host"
    assert libgitlab.kv.get("pgsql_port") == "port"
    assert libgitlab.kv.get("pgsql_db") == "dbname"
    assert libgitlab.kv.get("pgsql_user") == "user"
    assert libgitlab.kv.get("pgsql_pass") == "password"


def test_save_mysql_conf(libgitlab):
    """Test save_mysql_conf."""
    db = mock.Mock()
    db.host.return_value = "host"
    db.port.return_value = "port"
    db.database.return_value = "dbname"
    db.user.return_value = "user"
    db.password.return_value = "password"
    libgitlab.save_mysql_conf(db)
    assert libgitlab.kv.get("mysql_host") == "host"
    assert libgitlab.kv.get("mysql_port") == "port"
    assert libgitlab.kv.get("mysql_db") == "dbname"
    assert libgitlab.kv.get("mysql_user") == "user"
    assert libgitlab.kv.get("mysql_pass") == "password"


def test_save_redis_conf(libgitlab):
    """Test save_redis_conf."""
    endpoint = mock.Mock()
    mock_redis = mock.Mock()
    mock_redis.get.return_value = "mock value"

    # Test relation before data is available
    endpoint.relation_data.return_value = []
    libgitlab.save_redis_conf(endpoint)
    assert libgitlab.kv.get("redis_host") is None

    # Test relation after before data is available
    endpoint.relation_data.return_value = [mock_redis]
    libgitlab.save_redis_conf(endpoint)
    assert libgitlab.kv.get("redis_host") == "mock value"
    assert libgitlab.kv.get("redis_port") == "mock value"
    assert libgitlab.kv.get("redis_pass") == "mock value"
    mock_redis.get.return_value = None
    libgitlab.save_redis_conf(endpoint)
    assert not libgitlab.kv.get("redis_pass")


def test_remove_redis_conf(libgitlab):
    """Test remove_redis_conf."""
    libgitlab.kv.set("redis_host", "mock")
    libgitlab.kv.set("redis_port", "mock")
    libgitlab.kv.set("redis_pass", "mock")
    libgitlab.remove_redis_conf()
    assert not libgitlab.kv.get("redis_host")
    assert not libgitlab.kv.get("redis_port")
    assert not libgitlab.kv.get("redis_pass")


def test_upgrade_gitlab_noop(libgitlab):
    """Test the noop path."""
    result = libgitlab.upgrade_gitlab()
    assert result is False


def test_upgrade_gitlab_minor(libgitlab, mock_gitlab_hookenv_log):
    """Test the upgrade path."""
    # Upgrade to new minor version
    libgitlab.get_installed_version.return_value = "1.1.0"
    result = libgitlab.upgrade_gitlab()
    print(mock_gitlab_hookenv_log.call_args_list)
    calls = [
        call("Processing pending package upgrades for GitLab"),
        call("Found major version 1 for GitLab version 1.1.1"),
        call("Found major version 1 for GitLab version 1.1.0"),
        call("Upgrading GitLab version 1.1.0 to latest in major release 1"),
    ]
    mock_gitlab_hookenv_log.assert_has_calls(calls)
    assert libgitlab.get_installed_version() == "1.1.1"
    assert result is True

    # Don't upgrade if charm_config matches intalled
    mock_gitlab_hookenv_log.reset_mock()
    libgitlab.charm_config["version"] = "1.1.0"
    libgitlab.get_installed_version.return_value = "1.1.0"
    result = libgitlab.upgrade_gitlab()
    assert libgitlab.get_installed_version() == "1.1.0"
    assert result is False


def test_upgrade_gitlab_major(libgitlab, mock_gitlab_hookenv_log):
    """Test the upgrade path."""
    libgitlab.get_installed_version.return_value = "0.0.0"
    result = libgitlab.upgrade_gitlab()
    print(mock_gitlab_hookenv_log.call_args_list)
    calls = [
        call("Processing pending package upgrades for GitLab"),
        call("Found major version 1 for GitLab version 1.1.1"),
        call("Found major version 0 for GitLab version 0.0.0"),
        call("Upgrading GitLab version 0.0.0 to latest in current major release 0"),
        call("Upgrading GitLab version 0.0.0 to latest in next major release 1"),
        call("Found major version 1 for GitLab version 1.1.1"),
        call("Found major version 1 for GitLab version 1.1.1"),
        call("GitLab is already at configured version 1.1.1"),
    ]
    mock_gitlab_hookenv_log.assert_has_calls(calls)
    assert libgitlab.get_installed_version() == "1.1.1"
    assert result is True


def test_upgrade_gitlab_install(libgitlab, mock_gitlab_hookenv_log):
    """Test the upgrade path."""
    libgitlab.get_installed_version.return_value = ""
    result = libgitlab.upgrade_gitlab()
    print(mock_gitlab_hookenv_log.call_args_list)
    calls = [
        call("Processing pending package upgrades for GitLab"),
        call("GitLab is not installed, installing..."),
    ]
    mock_gitlab_hookenv_log.assert_has_calls(calls)
    assert libgitlab.get_installed_version() == "1.1.1"
    assert result is True


def test_backup(libgitlab, mock_gitlab_subprocess, mock_layers):
    """Test backup."""
    libgitlab.backup()
    assert mock_gitlab_subprocess.check_output.call_count == 1
    assert mock_layers["layer_backup"].call_count == 1


def test_render_config_fails_without_db(libgitlab, mock_gitlab_hookenv_log):
    """Test render of configuration fails when DB is not configured."""
    assert libgitlab.render_config() is False
    mock_gitlab_hookenv_log.assert_has_calls(
        [call("Skipping configuration due to missing DB config")]
    )


def test_render_pgsql_config(libgitlab, mock_gitlab_hookenv_log):
    """Test render of configuration includes PostgreSQL configuration when present in KV store."""
    _rendered_config("pgsql", libgitlab)
    mock_gitlab_hookenv_log.assert_has_calls(
        [call("PostgreSQL is related and configured in the charm KV store", "DEBUG")]
    )


def test_render_mysql_config(libgitlab):
    """Test render of configuration includes MySQL configuration when present in KV store."""
    _rendered_config("mysql", libgitlab)


def test_render_legacy_database_config(libgitlab):
    """Test render of configuration includes legacy MySQL configuration when present in KV store."""
    _rendered_config("legacy", libgitlab)


@pytest.mark.parametrize("database_type", ("pgsql", "mysql", "legacy"))
def test_render_smtp_settings_not_enabled(database_type, libgitlab):
    """Test render of configuration prior to SMTP being configured."""
    config_lines = _rendered_config(database_type, libgitlab)
    assert not any((line.startswith("gitlab_rails['smtp") for line in config_lines))


@pytest.mark.parametrize("database_type", ("pgsql", "mysql", "legacy"))
def test_render_smtp_settings_without_login(database_type, libgitlab):
    """Test render of configuration when SMTP is configured without login setting."""
    libgitlab.charm_config["smtp_server"] = "mocked.smtp.server"
    libgitlab.charm_config["smtp_port"] = 123
    libgitlab.charm_config["smtp_domain"] = "domain.smtp.server"
    libgitlab.charm_config["smtp_authentication"] = "plain"
    libgitlab.charm_config["smtp_tls"] = True

    config_lines = _rendered_config(database_type, libgitlab)

    # Assert that smtp was properly configured in gitlab config
    assert "gitlab_rails['smtp_enable'] = true" in config_lines
    assert "gitlab_rails['smtp_address'] = \"mocked.smtp.server\"" in config_lines
    assert "gitlab_rails['smtp_port'] = \"123\"" in config_lines
    assert "gitlab_rails['smtp_domain'] = \"domain.smtp.server\"" in config_lines
    assert "gitlab_rails['smtp_authentication'] = \"plain\"" in config_lines
    assert "gitlab_rails['smtp_enable_starttls_auto'] = true" in config_lines
    assert "gitlab_rails['smtp_tls'] = true" in config_lines

    assert not any(
        (line.startswith("gitlab_rails['smtp_user_name']") for line in config_lines)
    )
    assert not any(
        (line.startswith("gitlab_rails['smtp_password']") for line in config_lines)
    )


@pytest.mark.parametrize("database_type", ("pgsql", "mysql", "legacy"))
def test_render_smtp_settings_with_login(database_type, libgitlab):
    """Test render of configuration when SMTP is configured with login setting."""
    libgitlab.charm_config["smtp_server"] = "mocked.smtp.server"
    libgitlab.charm_config["smtp_port"] = 123
    libgitlab.charm_config["smtp_user"] = "user"
    libgitlab.charm_config["smtp_password"] = "password"
    libgitlab.charm_config["smtp_domain"] = "domain.smtp.server"
    libgitlab.charm_config["smtp_authentication"] = "plain"
    libgitlab.charm_config["smtp_tls"] = True

    config_lines = _rendered_config(database_type, libgitlab)

    # Assert that smtp was properly configured in gitlab config
    assert "gitlab_rails['smtp_enable'] = true" in config_lines
    assert "gitlab_rails['smtp_address'] = \"mocked.smtp.server\"" in config_lines
    assert "gitlab_rails['smtp_port'] = \"123\"" in config_lines
    assert "gitlab_rails['smtp_user_name'] = \"user\"" in config_lines
    assert "gitlab_rails['smtp_password'] = \"password\"" in config_lines
    assert "gitlab_rails['smtp_domain'] = \"domain.smtp.server\"" in config_lines
    assert "gitlab_rails['smtp_authentication'] = \"plain\"" in config_lines
    assert "gitlab_rails['smtp_enable_starttls_auto'] = true" in config_lines
    assert "gitlab_rails['smtp_tls'] = true" in config_lines


@pytest.mark.parametrize("database_type", ("pgsql", "mysql", "legacy"))
@pytest.mark.parametrize("email_from", ("test@example.com", ""))
@pytest.mark.parametrize("email_display_name", ("name", ""))
@pytest.mark.parametrize("email_reply_to", ("noreply@example.com", ""))
def test_render_email_settings(
    database_type, email_from, email_display_name, email_reply_to, libgitlab
):
    """Test render of configuration when email settings are configured."""
    libgitlab.charm_config["email_from"] = email_from
    libgitlab.charm_config["email_display_name"] = email_display_name
    libgitlab.charm_config["email_reply_to"] = email_reply_to

    config_lines = _rendered_config(database_type, libgitlab)

    # Assert that email options were properly configured in gitlab config
    if email_from:
        assert (
            "gitlab_rails['gitlab_email_from'] = '{}'".format(email_from)
            in config_lines
        )
    else:
        assert not any(
            (line.startswith("gitlab_rails['gitlab_email_from']") for line in config_lines)
        )

    if email_display_name:
        assert (
            "gitlab_rails['gitlab_email_display_name'] = '{}'".format(
                email_display_name
            )
            in config_lines
        )
    else:
        assert not any(
            (
                line.startswith("gitlab_rails['gitlab_email_display_name']")
                for line in config_lines
            )
        )

    if email_reply_to:
        assert (
            "gitlab_rails['gitlab_email_reply_to'] = '{}'".format(email_reply_to)
            in config_lines
        )
    else:
        assert not any(
            (
                line.startswith("gitlab_rails['gitlab_email_reply_to']")
                for line in config_lines
            )
        )


def _rendered_config(database_type, libgitlab):
    _configure_database(database_type, libgitlab)

    assert libgitlab.render_config() is True
    with open(libgitlab.gitlab_config, "r") as f:
        config_lines = f.read().splitlines()

    _assert_database_rendered(database_type, config_lines)
    return config_lines


def _configure_database(database_type, libgitlab):
    if database_type == "pgsql":
        # Configure postgresql
        libgitlab.kv.set("pgsql_host", "host")
        libgitlab.kv.set("pgsql_port", "port")
        libgitlab.kv.set("pgsql_db", "db")
        libgitlab.kv.set("pgsql_user", "user")
        libgitlab.kv.set("pgsql_pass", "pass")
    elif database_type == "mysql":
        # Configure mysql
        libgitlab.kv.set("mysql_host", "host")
        libgitlab.kv.set("mysql_port", "port")
        libgitlab.kv.set("mysql_db", "db")
        libgitlab.kv.set("mysql_user", "user")
        libgitlab.kv.set("mysql_pass", "pass")
    elif database_type == "legacy":
        # Configure legacy database
        libgitlab.kv.set("db_host", "host")
        libgitlab.kv.set("db_port", "port")
        libgitlab.kv.set("db_db", "db")
        libgitlab.kv.set("db_user", "user")
        libgitlab.kv.set("db_pass", "pass")
    else:
        pytest.fail("Unsupported database type: {}".format(database_type))


def _assert_database_rendered(database_type, config_lines):
    if database_type == "pgsql":
        # Assert that postgresql was properly configured in gitlab config
        assert "gitlab_rails['db_adapter'] = \"postgresql\"" in config_lines
        assert "gitlab_rails['db_host'] = \"host\"" in config_lines
        assert "gitlab_rails['db_port'] = \"port\"" in config_lines
        assert "gitlab_rails['db_database'] = \"db\"" in config_lines
        assert "gitlab_rails['db_username'] = \"user\"" in config_lines
        assert "gitlab_rails['db_password'] = \"pass\"" in config_lines
    elif database_type in ("mysql", "legacy"):
        # Assert that mysql (or legacy database) was properly configured in gitlab config
        assert "gitlab_rails['db_adapter'] = \"mysql2\"" in config_lines
        assert "gitlab_rails['db_host'] = \"host\"" in config_lines
        assert "gitlab_rails['db_port'] = \"port\"" in config_lines
        assert "gitlab_rails['db_database'] = \"db\"" in config_lines
        assert "gitlab_rails['db_username'] = \"user\"" in config_lines
        assert "gitlab_rails['db_password'] = \"pass\"" in config_lines
    else:
        pytest.fail("Unsupported database type: {}".format(database_type))
