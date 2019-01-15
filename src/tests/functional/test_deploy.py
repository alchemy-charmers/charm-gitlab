import pytest
import os
import yaml
from juju.model import Model

# Treat tests as coroutines
pytestmark = pytest.mark.asyncio

# Load charm metadata
metadata = yaml.load(open("./metadata.yaml"))
juju_repository = os.getenv('JUJU_REPOSITORY',
                            '.').rstrip('/')
charmname = metadata['name']
series = ['bionic']


@pytest.fixture
async def model():
    model = Model()
    await model.connect_current()
    yield model
    await model.disconnect()


@pytest.mark.parametrize('series', series)
async def test_gitlab_deploy(model, series):
    # this has been modified from the template, as the template
    # deploys from the layer, rather than the built charm, which
    # needs to be fixed
    app = await model.deploy('{}/builds/{}'.format(
            juju_repository,
            charmname),
        series=series)
    await model.block_until(lambda: app.status == 'active')
    assert True


@pytest.mark.parametrize('series', series)
async def test_mysql_relate(model, series):
    sql = await model.deploy(
        'cs:mysql',
        series='xenial')
    await model.block_until(lambda: sql.status == 'active')
    await model.add_relation(
        'gitlab:db',
        'mysql')
    assert True


@pytest.mark.parametrize('series', series)
async def test_redis_relate(model, series):
    redis = await model.deploy(
        'cs:~omnivector/redis',
        series='xenial')
    await model.block_until(lambda: redis.status == 'active')
    await model.add_relation(
        'gitlab:redis',
        'redis')
    assert True


# def test_example_action(self, deploy, unit):
#     uuid = unit.run_action('example-action')
#     action_output = deploy.get_action_output(uuid, full_output=True)
#     print(action_output)
#     assert action_output['status'] == 'completed'
