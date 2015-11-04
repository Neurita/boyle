# -*- coding: utf-8 -*-

import pytest

import os
from boyle.petitdb import (PetitDB,
                           find_unique,
                           insert_unique,
                           search_sample,
                           MoreThanOneItemError,
                           NotUniqueItemError)


@pytest.fixture
def testdb():
    try:
        os.remove('test.json')
    except:
        pass

    pdb = PetitDB('test.json')

    uniqs = pdb.table('uniques')
    uniqs.insert_multiple([{'x': x, 'y': y} for x, y in zip(range(0, 10), range(10, 20))])

    dbls = pdb.table('doubles')
    dbls.insert_multiple([{'x': x, 'y': y} for x, y in zip(range(0, 10), range(10, 20))])
    dbls.insert_multiple([{'x': x, 'y': y} for x, y in zip(range(0, 10), range(10, 20))])

    return pdb


def test_find_unique_in_uniques(testdb):

    uniqs = testdb.table('uniques')

    eid = find_unique(uniqs, {'x': 1}, 'x')
    item = uniqs.get(eid=eid)
    assert(item)
    assert(isinstance(item, dict))
    assert(item['x'] == 1)

    eid = find_unique(uniqs, {'x': 1})
    item = uniqs.get(eid=eid)
    assert(item)
    assert(isinstance(item, dict))
    assert(item['x'] == 1)

    eid = find_unique(uniqs, {'x': 1, 'y': 11}, ['x', 'y'])
    item = uniqs.get(eid=eid)
    assert(item)
    assert(isinstance(item, dict))
    assert(item['x'] == 1)
    assert(item['y'] == 11)

    eid = find_unique(uniqs, {'x': 1, 'y': 11})
    item = uniqs.get(eid=eid)
    assert(item)
    assert(isinstance(item, dict))
    assert(item['x'] == 1)
    assert(item['y'] == 11)

    assert(find_unique(uniqs, {'x': -1, 'y': 11}) is None)


def test_find_unique_in_doubles(testdb):

    dbls = testdb.table('doubles')

    pytest.raises(MoreThanOneItemError,
                  find_unique,
                  table=dbls,
                  data={'x': 1, 'y': 11},
                  unique_fields=['x', 'y'],)


def test_insert_unique(testdb):

    dbls  = testdb.table('doubles')
    uniqs = testdb.table('uniques')

    pytest.raises(MoreThanOneItemError,
                  insert_unique,
                  table=dbls,
                  data={'x': 1, 'y': 11},
                  raise_if_found=True)

    pytest.raises(NotUniqueItemError,
                  insert_unique,
                  table=uniqs,
                  data={'x': 1, 'y': 11},
                  raise_if_found=True)

    item = insert_unique(dbls, {'x': 1, 'y': 21})
    assert(isinstance(item, int))

    item = insert_unique(uniqs, {'x': 1, 'y': 11}, raise_if_found=False)
    assert(isinstance(item, int))


def test_find_sample(testdb):

    dbls  = testdb.table('doubles')
    uniqs = testdb.table('uniques')

    items = search_sample(dbls, {'x': 1, 'y': 11})
    assert(len(items) == 2)
    assert(items[0] == items[1])

    items = search_sample(uniqs, {'x': 1, 'y': 11})
    assert(len(items) == 1)


def test_petitdb_count(testdb):
    sample = {'x': 1, 'y': 11}
    assert(testdb.count('doubles', sample) == 2)

    assert(testdb.count('uniques', sample) == 1)


def test_petitdb_isunique(testdb):
    sample = {'x': 1, 'y': 11}
    assert(not testdb.is_unique('doubles', sample))

    assert(testdb.is_unique('uniques', sample))


def test_petitdb_update_unique(testdb):
    sample = {'x': 1, 'y': 11}
    nufields = {'z': 100}

    eid = find_unique(testdb.table('uniques'), sample)

    nueid = testdb.update_unique('uniques', fields=nufields, data=sample)
    assert(eid == nueid)

    nuitem = testdb.table('uniques').get(eid=nueid)
    assert('z' in nuitem)

    pytest.raises(MoreThanOneItemError,
                  testdb.update_unique,
                  table_name='doubles',
                  data=sample,
                  fields=nufields)


def test_petitdb_search_by_eid(testdb):

    elem = testdb.search_by_eid('uniques', eid=1)
    assert(elem.eid == 1)
    assert(isinstance(elem, dict))

    pytest.raises(KeyError,
                  testdb.search_by_eid,
                  table_name='uniques',
                  eid=10000,)
