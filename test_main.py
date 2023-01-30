import functools
import json
import os
import codecs
from datetime import datetime

from bson import json_util
import mongomock
import pytest
import pymongo
import yaml

from app import app


_cache = {}
_engine = 'mongomock'


def pytest_addoption(parser):
    parser.addini(
        name='mongodb_fixtures',
        help='Load these fixtures for tests',
        type='linelist')

    parser.addini(
        name='mongodb_fixture_dir',
        help='Try loading fixtures from this directory',
        default=os.getcwd())

    parser.addini(
        name='mongodb_engine',
        help='The database engine to use [mongomock]',
        default='mongomock')

    parser.addini(
        name='mongodb_host',
        help='The host where the mongodb-server runs',
        default='localhost')

    parser.addini(
        name='mongodb_dbname',
        help='The name of the database where fixtures are created [pytest]',
        default='pytest')

    parser.addoption(
        '--mongodb-fixture-dir',
        help='Try loading fixtures from this directory')

    parser.addoption(
        '--mongodb-engine',
        help='The database engine to use [mongomock]')

    parser.addoption(
        '--mongodb-host',
        help='The host where the mongodb-server runs')

    parser.addoption(
        '--mongodb-dbname',
        help='The name of the database where fixtures are created [pytest]')


def pytest_configure(config):
    global _engine
    _engine = config.getoption('mongodb_engine') or config.getini('mongodb_engine')


@pytest.fixture(scope='function')
def mongodb(pytestconfig):
    dbname = pytestconfig.getoption('mongodb_dbname') or pytestconfig.getini('mongodb_dbname')
    client = make_mongo_client(pytestconfig)
    db = client[dbname]
    # clean_database(db)
    load_fixtures(db, pytestconfig)
    return db


def make_mongo_client(config):
    engine = config.getoption('mongodb_engine') or config.getini('mongodb_engine')
    host = config.getoption('mongodb_host') or config.getini('mongodb_host')
    if engine == 'pymongo':
        client = pymongo.MongoClient(host)
    else:
        client = mongomock.MongoClient(host)
    return client


# def clean_database(db):
#     for name in list_collection_names(db):
#         db.drop_collection(name)


def list_collection_names(db):
    if hasattr(db, 'list_collection_names'):
        return db.list_collection_names()
    return db.collection_names(include_system_collections=False)


def load_fixtures(db, config):
    basedir = config.getoption('mongodb_fixture_dir') or config.getini('mongodb_fixture_dir')
    if not os.path.isabs(basedir):
        basedir = config.rootdir.join(basedir).strpath
    fixtures = config.getini('mongodb_fixtures')

    for file_name in os.listdir(basedir):
        collection, ext = os.path.splitext(os.path.basename(file_name))
        file_format = ext.strip('.')
        supported = file_format in ('json', 'yaml')
        selected = collection in fixtures if fixtures else True
        if selected and supported:
            path = os.path.join(basedir, file_name)
            load_fixture(db, collection, path, file_format)


def load_fixture(db, collection, path, file_format):
    if file_format == 'json':
        loader = functools.partial(json.load, object_hook=json_util.object_hook)
    elif file_format == 'yaml':
        loader = functools.partial(yaml.load, Loader=yaml.FullLoader)
    else:
        return
    try:
        docs = _cache[path]
    except KeyError:
        with codecs.open(path, encoding='utf-8') as fp:
            _cache[path] = docs = loader(fp)
    insert_many(db[collection], docs)


def insert_many(collection, docs):
    if hasattr(collection, 'insert_many'):
        return collection.insert_many(docs)
    return collection.insert(docs)


def mongo_engine():
    return _engine

def test_load(mongodb):
    collection_name = mongodb.name
    assert 'parts-inventory' in collection_name
    check_parts(mongodb.parts)

def check_parts(parts):
    assert parts.count_documents({}) == 3
    check_keys_in_docs(parts, ['partName', 'partNumber', 'inStock', 'onOrder', 'weight(kg)', 'dimensions(mm)', 'cost($)', 'expiration', 'systemType'])
    screw = parts.find_one({'partName': 'Screw'})
    assert screw['partNumber'] == 100001
    assert screw['inStock'] == 20
    nail = parts.find_one({'partName': 'Nail'})
    assert nail['partNumber'] == 100002
    assert str(nail['cost($)']) == '0.50'
    bolt = parts.find_one({'partName': 'Bolt'})
    assert bolt['partNumber'] == 100003
    assert bolt['systemType'] == ['Filter', 'TempControl', 'Electronics']
    assert bolt['expiration'] == datetime(2030, 1, 1, 0, 0)

def check_keys_in_docs(collection, keys):
    for doc in collection.find():
        for key in keys:
            assert key in doc

# @pytest.mark.skip
def test_insert(mongodb):
    mongodb.parts.insert_one({
        'partName': 'Bulb',
        'partNumber': 100004,
        'inStock': 2,
        'onOrder': 8,
        'weight(kg)': 1.5,
        'dimensions(mm)': '200x400',
         'cost($)': 4.5,
         'expiration': datetime(2030, 1, 1, 0, 0),
         'systemType': ['Optics', 'Lasers']
    })
    assert mongodb.parts.count_documents({}) == 4
    assert mongodb.parts.find_one({'partName': 'Bulb'})

def test_mongo_engine(pytestconfig):
    assert mongo_engine() == 'mongomock'


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_pymongo(client):
    response = client.get('/test')
    my_json = response.data.decode("UTF-8")
    data = json.loads(my_json)
    json_obj = json.dumps(data)
    assert 'partName' in json_obj
    assert 'partNumber' in json_obj
    assert 'inStock' in json_obj
    assert 'onOrder' in json_obj
    assert response.status_code == 200

def test_pymongo_post(client):
    response = client.post('/test/part')
    my_json = response.data.decode("UTF-8")
    data = json.loads(my_json)
    json_obj = json.dumps(data)
    assert '_id' in json_obj
    assert response.status_code == 200

def test_pymongo_delete(client):
    response = client.delete('/test/part/63d80df53cec861f655cdf13')
    my_json = response.data.decode("UTF-8")
    data = json.loads(my_json)
    json_obj = json.dumps(data)
    assert 'deleted' in json_obj
    assert response.status_code == 200