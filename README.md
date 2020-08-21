[![pipeline status](https://git.ec0.io/pirate-charmers/charm-gitlab/badges/master/pipeline.svg)](https://git.ec0.io/pirate-charmers/charm-gitlab/commits/master)
[![coverage report](https://git.ec0.io/pirate-charmers/charm-gitlab/badges/master/coverage.svg)](https://git.ec0.io/pirate-charmers/charm-gitlab/commits/master)

# GitLab 

This charm provides the [GitLab](https://gitlab.com) code hosting and CI/CD platform, for use with MySQL as a backend database.

Optionally, a reverse proxy can be placed in front of GitLab by relating this charm to a charm implementing the `reverseproxy` interface.

# Usage

Running the following step will install the GitLab Omnibus package,
with default configuration.
`juju deploy gitlab`

Before GitLab can be used, you will need to relate it to a
PostgreSQL cluster via the db-admin relation:
`juju add-relation gitlab:pgsql postgresql:db-admin`

Usage via HTTPS can be achieved by running GitLab behind a reverse
proxy that has been properly configured for the desired external
domain name. A good default reverse proxy is provided by the
`haproxy` charm.
`juju add-relation gitlab:reverseproxy haproxy`

# Upgrades

GitLab has a fairly strict upgrade policy due to the required
DB migrations which are run on package upgrade. Due to this,
this package will upgrade the package periodically to make sure
that no upgrade steps are missed. If you would like to control
this process manually, you can set a specific package version
you would like to stay on using the `version` configuration
item. The `upgrade` action can then be run when you do want to
upgrade. Unset the `version` option and then run the `upgrade`
action to upgrade to the latest version, or set a new desired
version in the `version` option and then run the `upgrade`
action to upgrade to a new specified version.

# Migration
This charm (and GitLab) previously supported installation to
a MySQL database. If you had deployed this charm against MySQL,
you must migrate to PostgreSQL to keep using it, as GitLab
has deprecated support for MySQL as of the 12.1 release. Deploying
with MySQL is unsupported, as GitLab no longer actually
works with MySQL as a backend DB.

*NOTE:* There is a chance the following process could nuke your
database contents. Or mess up your schema. Always back up your
MySQL database prior to running the `migratedb` action.
If you have data in your PostgreSQL database, you should back
that up too, as the migration will very likely remove it if
there is already a gitlab database there.

*ALSO NOTE:* The migration and schema manipulation in upstream
GitLab is fragile. Given the official guidance is to upgrade
before upgrading to 12.1, if you have already upgraded or have
not upgraded in a while prior to attempting the migration, you
will need to carefully control the upgrade process (per the
above process) until you reach version 12.0.9, perform the
migration, and then continue any other upgrades. Failure to do
so will get your MySQL database schema and upgrade out of date.
The charm has some safety in place, as if you are on the latest
charm, and have MySQL related, it will cease upgrades and
reconfigurations. You can run both manually as you upgrade using
the `upgrade` and `reconfigure` actions which relate directly to
the apt package upgrades and `gitlab-ctl reconfigure` calls in
the [upstream migration
documentation](https://docs.gitlab.com/ce/update/mysql_to_postgresql.html).

In order to migrate, deploy a new `cs:postgresql` unit or cluster, and
relate the `db-admin` relation from the PostgreSQL charm to this
charm's `pgsql` relation. Do not remove the MySQL relation yet, as 
the MySQL credentials will be stored in the charm's key/value
store and used to migrate data from the old database. Once the
relation to PostgreSQL is healthy, you can use the `migratedb`
action to migrate your data using `pgloader`. Once this is complete,
remove the MySQL relation, and GitLab will be reconfigured to use
the new PostgreSQL database. Migrations will run automatically.
If there is any issue with the migration process, the charm will
enter error state - the charm `debug-log` will be helpful in
determining the problem, and manual intervention will likely be
required. If all goes well, no further action will be required
to continue using PostgreSQL.

# PostgreSQL Upgrade

Starting with version 13 of GitLab, PostgreSQL lower than version 11
is deprecated, and will actively break in later 13.x versions due
to migrations requiring newer schema primitives.

The tested migration path with the charms is as such:

*NOTE*: Until GitLab fixes [5391](https://gitlab.com/gitlab-org/omnibus-gitlab/-/issues/5391) properly:

Your app and DB servers (gitlab unit and postgresql unit) should both be upgraded to Ubuntu 20.04

You need to work around the `pg_dump` version used by GitLab

On the application server, after following the below instructions, before the final upgrade, upgrade your application unit to focal using `juju upgrade-series <machine ID> prepare` and then doing a do-release upgrade to foacl, followed by `juju upgrade-series <machine ID> complete`
 
 You will then need to install `postgresql-client-12` and run `sudo ln -s /usr/lib/postgresql/12/bin/pg_dump /opt/gitlab/bin/pg_dump`

Process:

Take a full GitLab backup:
 * Access your gitlab unit via SSH: `juju ssh gitlab/0`
 * Run the backup: `gitlab-backup`
 * From your machine, SCP the resulting tar and keep safe: `juju scp gitlab/0:*.tar .`

Dump the curent database (note, this will migrate ALL databases)
 * Access your PostgreSQL server: `juju ssh postgresql/0`
 * Access the postgres user: `sudo -u postgres -i`
 * Back up all databases: `pg_dumpall > /tmp/gitlab.dump`
 * From your machine, SCP the file: `juju scp postgresql/0:/tmp/gitlab.dump .`

Deploy a new PostgreSQL application
 * Deploy a new PostgreSQL 12 on Focal: `juju deploy cs:postgresql --series focal --config version=12 postgresql12`

Migrate the database to the new PostgreSQL
 * SCP the dump file to the new application: `juju scp gitlab.dump postgresql12/0:/tmp`
 * Access the new postgresql server: `juju ssh postgresql12/0`
 * Switch to the postgres user: `sudo -u postgres -i `
 * Restore the DB: `psql < /tmp/gitlab.dump`

Re-relate GitLab
 * Remove old relation: `juju remove-relation gitlab postgresql:db-admin`
 * Add new relation: `juju add-relation gitlab postgresql12:db-admin`
 * If your units are not both on Ubuntu focal, and you are using PostgreSQL 12, make sure you follow the
   steps in the note above to work around [5391](https://gitlab.com/gitlab-org/omnibus-gitlab/-/issues/5391) 
 * Run an upgrade of GitLab: `juju run-action --wait gitlab/0 upgrade`

# Contact Information

This charm is written by James Hebden of the Pirate Charmers group.

  - https://piratecharmers.com
  - https://launchpad.net/~pirate-charmers/layer-gitlab

# Planned features

  - configuration of SMTP settings
  - administrative password management via juju config
  - specify option to pass hostname over reverseproxy relation
  - specify option to override address used for reverseproxy
  - interface for relating GitLab CI runners (WIP)
