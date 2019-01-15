# GitLab 

This charm provides the [GitLab](https://gitlab.com) code hosting and CI/CD platform, for use with MySQL as a backend database.

Optionally, a reverse proxy can be placed in front of GitLab by relating this charm to a charm implementing the `reverseproxy` interface.

# Usage

Running the following step will install the GitLab Omnibus package,
with default configuration.
`juju deploy gitlab`

Before GitLab can be used, you will need to relate it to a MySQL
database relation, such as those provided by the MySQL charm, or
the Percona charms.
`juju add-relation gitlab:db mysql`

Usage via HTTPS can be achieved by running GitLab behind a reverse
proxy that has been properly configured for the desired external
domain name. A good default reverse proxy is provided by the
`haproxy` charm.
`juju add-relation gitlab:reverseproxy haproxy`

# Contact Information

This charm is written by James Hebden of the Pirate Charmers group.

  - https://piratecharmers.com
  - https://launchpad.net/~pirate-charmers/layer-gitlab

# Planned features

  - configuration of SMTP settings
  - postgresql support (currenly MySQL only)
  - redis relation for external redis
  - administrative password management via juju config
