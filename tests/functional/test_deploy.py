import asyncio
import pytest
import stat
import os

# Treat all tests as coroutines
pytestmark = [
    pytest.mark.asyncio,
]

juju_repository = os.getenv('JUJU_REPOSITORY', '.').rstrip('/')
series = ['bionic',
          # cosmic packages don't exist for gitlab, so testing is pointless
          # pytest.param('cosmic', marks=pytest.mark.xfail(reason='canary')),
          ]
sources = [('local', '{}/builds/gitlab'.format(juju_repository)),
           ('jujucharms', 'cs:~pirate-charmers/gitlab'),
           ]


# Custom fixtures
@pytest.fixture(params=series)
def series(request):
    return request.param


@pytest.fixture(params=sources, ids=[s[0] for s in sources])
def source(request):
    return request.param


@pytest.fixture
async def app(model, series, source):
    app_name = 'gitlab-{}-{}'.format(series, source[0])
    return model.applications[app_name]


async def test_gitlab_deploy(model, series, source, request):
    application_name = 'gitlab-{}-{}'.format(series, source[0])
    cmd = 'juju deploy {} -m {} --series {} {}'.format(
            source[1],
            model.info.name,
            series,
            application_name)
    if request.node.get_closest_marker('xfail'):
        cmd += ' --force'
    await asyncio.create_subprocess_shell(cmd)
    
    app = await model._wait_for_new('application', application_name)
    await model.block_until(lambda: app.status == 'waiting')


async def test_gitlab_deploy_status(model, app, request):
    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == 'idle' or unit.agent_status == 'error')
    await model.block_until(lambda: app.status == 'blocked' or app.status == 'error')
    assert unit.agent_status is not 'error'
    assert app.status is not 'error'


async def test_mysql_deploy(model, series, app, request):
    if app.name.endswith('jujucharms'):
        pytest.skip("No need to test the charm deploy")

    await model.block_until(lambda: app.status == 'blocked')

    application_name = 'gitlab-mysql-{}'.format(series)
    cmd = 'juju deploy cs:mysql -m {} --series xenial {}'.format(
            model.info.name,
            application_name)
    await asyncio.create_subprocess_shell(cmd)


async def test_mysql_relate(model, series, app, request):
    if app.name.endswith('jujucharms'):
        pytest.skip("No need to test the charm deploy")

    application_name = 'gitlab-mysql-{}'.format(series)
    sql = await model._wait_for_new('application', application_name)
    await model.block_until(lambda: sql.status == 'active')
    print('Relating {} with {}'.format(app.name, 'mysql'))
    await model.add_relation(
        '{}:db'.format(app.name),
        application_name)


async def test_redis_deploy(model, series, app, request):
    if app.name.endswith('jujucharms'):
        pytest.skip("No need to test the charm deploy")

    await model.block_until(lambda: app.status == 'blocked')

    application_name = 'gitlab-redis-{}'.format(series)
    cmd = 'juju deploy cs:~omnivector/redis -m {} --series xenial {}'.format(
            model.info.name,
            application_name)
    await asyncio.create_subprocess_shell(cmd)


async def test_redis_relate(model, series, app, request):
    if app.name.endswith('jujucharms'):
        pytest.skip("No need to test the charm deploy")

    application_name = 'gitlab-redis-{}'.format(series)
    redis = await model._wait_for_new('application', application_name)
    await model.block_until(lambda: redis.status == 'active')
    print('Relating {} with {}'.format(app.name, 'redis'))
    await model.add_relation(
        '{}:redis'.format(app.name),
        application_name)


async def test_charm_upgrade(model, app, request):
    if app.name.endswith('local'):
        pytest.skip("No need to upgrade the local deploy")

    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == 'idle')
    await asyncio.create_subprocess_shell(['juju',
                                           'upgrade-charm',
                                           '--switch={}'.format(sources[0][1]),
                                           '-m', model.info.name,
                                           app.name,
                                           ])
    await model.block_until(lambda: unit.agent_status == 'executing')


# Tests
async def test_gitlab_status(model, app):
    # Verifies status for all deployed series of the charm
    await model.block_until(lambda: app.status == 'active')
    unit = app.units[0]
    await model.block_until(lambda: unit.agent_status == 'idle')


async def test_reconfigure_action(app):
    unit = app.units[0]
    action = await unit.run_action('reconfigure')
    action = await action.wait()
    assert action.status == 'completed'


async def test_run_command(app, jujutools):
    unit = app.units[0]
    cmd = 'hostname -i'
    results = await jujutools.run_command(cmd, unit)
    assert results['Code'] == '0'
    assert unit.public_address in results['Stdout']


async def test_juju_file_stat(app, jujutools):
    unit = app.units[0]
    path = '/var/lib/juju/agents/unit-{}/charm/metadata.yaml'.format(unit.entity_id.replace('/', '-'))
    fstat = await jujutools.file_stat(path, unit)
    assert stat.filemode(fstat.st_mode) == '-rw-r--r--'
    assert fstat.st_uid == 0
    assert fstat.st_gid == 0
