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

# Migration
This charm previously supported installation to a MySQL database.
If you had deployed this charm against MySQL, you must migrate
to PostgreSQL to keep using it, as GitLab has deprecated support
for MySQL. Deploying with MySQL is unsupported, as GitLab no longer
actually works with MySQL as a backend DB.

*NOTE:* There is a chance the following process could nuke your
database contents. Always back you your MySQL database prior to
running the `migratedb` action. If you have data in your PostgreSQL
database, you should back that up too, as the migration will very
likely remove it.

In order to migrate, deploy a new cs:postgresql unit or cluster, and
relate the db-admin relation from the PostgreSQL charm to this
charm's pgsql relation. Do not remove the MySQL relation. Once the
relation to PostgreSQL is healthy, you can use the `migratedb`
action to migrate your data using pgloader. Once this is complete,
remove the MySQL relation, and GitLab will be reconfigured to use
the new PostgreSQL database.

# Contact Information

This charm is written by James Hebden of the Pirate Charmers group.

  - https://piratecharmers.com
  - https://launchpad.net/~pirate-charmers/layer-gitlab

# Planned features

  - configuration of SMTP settings
  - administrative password management via juju config
  - specify option to pass hostname over reverseproxy relation
  - specify option to override address used for reverseproxy
