# coding=utf-8
"""
TinyDB extensions. PetitDB, a TinyDB with unique fields logics.
requires: tinydb >= v3.0 (note that this is not a stable release yet.)
"""
# -------------------------------------------------------------------------------
# Author: Alexandre Manhaes Savio <alexsavio@gmail.com>
# Nuklear Medizin Department
# Klinikum rechts der Isar, Technische Universitaet Muenchen (TUM)

# 2015, Alexandre Manhaes Savio
# Use this at your own risk!
# -------------------------------------------------------------------------------
from datetime import datetime
from collections import OrderedDict

try:
    import tinydb
except:
    raise ImportError('Please install TinyDB v3.0.')

from tinydb             import TinyDB, where
from tinydb.storages    import JSONStorage
from tinydb.middlewares import CachingMiddleware

from six                import string_types
from dateutil.tz        import tzutc


class MoreThanOneItemError(Exception):
    pass


class NotUniqueItemError(Exception):
    pass


def timestamp_with_tzinfo(dt):
    """
    Serialize a date/time value into an ISO8601 text representation
    adjusted (if needed) to UTC timezone.

    For instance:
    >>> serialize_date(datetime(2012, 4, 10, 22, 38, 20, 604391))
    '2012-04-10T22:38:20.604391Z'
    """
    utc = tzutc()

    if dt.tzinfo:
        dt = dt.astimezone(utc).replace(tzinfo=None)
    return dt.isoformat() + 'Z'


def timestamp_to_date_str(dt):
    """ Serialize a date/time value into YYYY-MM-DD date string. """
    return str(dt.date())


def _to_string(data):
    """ Convert to string all values in `data`.

    Parameters
    ----------
    data: dict[str]->object

    Returns
    -------
    string_data: dict[str]->str
    """
    sdata = data.copy()
    for k, v in data.items():
        if isinstance(v, datetime):
            sdata[k] = timestamp_to_date_str(v)

        elif not isinstance(v, (string_types, float, int)):
            sdata[k] = str(v)

    return sdata


def insert_unique(table, data, unique_fields=None, *, raise_if_found=False):
    """Insert `data` into `table` ensuring that data has unique values
    in `table` for the fields listed in `unique_fields`.

    If `raise_if_found` is True, will raise an NotUniqueItemError if
    another item with the same `unique_fields` values are found
    previously in `table`.
    If False, will return the `eid` from the item found.

    Parameters
    ----------
    table: tinydb.Table

    data: dict

    unique_fields: list of str
        Name of fields (keys) from `data` which are going to be used to build
        a sample to look for exactly the same values in the database.
        If None, will use every key in `data`.

    raise_if_found: bool

    Returns
    -------
    eid: int
        Id of the object inserted or the one found with same `unique_fields`.

    Raises
    ------
    MoreThanOneItemError
        Raise even with `raise_with_found` == False if it finds more than one item
        with the same values as the sample.

    NotUniqueItemError
        If `raise_if_found` is True and an item with the same `unique_fields`
        values from `data` is found in `table`.
    """
    item = find_unique(table, data, unique_fields)
    if item is not None:
        if raise_if_found:
            raise NotUniqueItemError('Not expected to find an item with the same '
                                     'values for {}. Inserting {} got {} in eid {}.'.format(unique_fields,
                                                                                            data,
                                                                                            table.get(eid=item),
                                                                                            item))
        else:
            return item

    return table.insert(data)


def search_sample(table, sample):
    """Search for items in `table` that have the same field sub-set values as in `sample`.

    Parameters
    ----------
    table: tinydb.table

    sample: dict
        Sample data

    Returns
    -------
    search_result: list of dict
        List of the items found. The list is empty if no item is found.
    """
    query = _query_sample(sample=sample, operators='__eq__')

    return table.search(query)


def search_unique(table, sample, unique_fields=None):
    """ Search for items in `table` that have the same field sub-set values as in `sample`.
    Expecting it to be unique, otherwise will raise an exception.

    Parameters
    ----------
    table: tinydb.table
    sample: dict
        Sample data

    Returns
    -------
    search_result: tinydb.database.Element
        Unique item result of the search.

    Raises
    ------
    KeyError:
        If the search returns for more than one entry.
    """
    if unique_fields is None:
        unique_fields = list(sample.keys())

    query = _query_data(sample, field_names=unique_fields, operators='__eq__')
    items = table.search(query)

    if len(items) == 1:
        return items[0]

    if len(items) == 0:
        return None

    raise MoreThanOneItemError('Expected to find zero or one items, but found '
                                '{} items.'.format(len(items)))


def find_unique(table, sample, unique_fields=None):
    """Search in `table` an item with the value of the `unique_fields` in the `sample` sample.
    Check if the the obtained result is unique. If nothing is found will return an empty list,
    if there is more than one item found, will raise an IndexError.

    Parameters
    ----------
    table: tinydb.table

    sample: dict
        Sample data

    unique_fields: list of str
        Name of fields (keys) from `data` which are going to be used to build
        a sample to look for exactly the same values in the database.
        If None, will use every key in `data`.

    Returns
    -------
    eid: int
        Id of the object found with same `unique_fields`.
        None if none is found.

    Raises
    ------
    MoreThanOneItemError
        If more than one example is found.
    """
    res = search_unique(table, sample, unique_fields)
    if res is not None:
        return res.eid
    else:
        return res


def _query_sample(sample, operators='__eq__'):
    """Create a TinyDB query that looks for items that have each field in `sample` with a value
    compared with the correspondent operation in `operators`.

    Parameters
    ----------
    sample: dict
        The sample data

    operators: str or list of str
        A list of comparison operations for each field value in `sample`.
        If this is a str, will use the same operator for all `sample` fields.
        If you want different operators for each field, remember to use an OrderedDict for `sample`.
        Check TinyDB.Query class for possible choices.

    Returns
    -------
    query: tinydb.database.Query
    """
    if isinstance(operators, str):
        operators = [operators] * len(sample)

    if len(sample) != len(operators):
        raise ValueError('Expected `operators` to be a string or a list with the same'
                         ' length as `field_names` ({}), got {}.'.format(len(sample),
                                                                         operators))

    queries = []
    for i, fn in enumerate(sample):
        fv = sample[fn]
        op = operators[i]
        queries.append(_build_query(field_name=fn,
                                    field_value=fv,
                                    operator=op))

    return _concat_queries(queries, operators='__and__')


def _query_data(data, field_names=None, operators='__eq__'):
    """Create a tinyDB Query object that looks for items that confirms the correspondent operator
    from `operators` for each `field_names` field values from `data`.

    Parameters
    ----------
    data: dict
        The data sample

    field_names: str or list of str
        The name of the fields in `data` that will be used for the query.

    operators: str or list of str
        A list of comparison operations for each field value in `field_names`.
        If this is a str, will use the same operator for all `field_names`.
        If you want different operators for each field, remember to use an OrderedDict for `data`.
        Check TinyDB.Query class for possible choices.

    Returns
    -------
    query: tinydb.database.Query
    """
    if field_names is None:
        field_names = list(data.keys())

    if isinstance(field_names, str):
        field_names = [field_names]

    # using OrderedDict by default, in case operators has different operators for each field.
    sample = OrderedDict([(fn, data[fn]) for fn in field_names])
    return _query_sample(sample, operators=operators)


def _concat_queries(queries, operators='__and__'):
    """Create a tinyDB Query object that is the concatenation of each query in `queries`.
    The concatenation operator is taken from `operators`.

    Parameters
    ----------
    queries: list of tinydb.Query
        The list of tinydb.Query to be joined.

    operators: str or list of str
        List of binary operators to join `queries` into one query.
        Check TinyDB.Query class for possible choices.

    Returns
    -------
    query: tinydb.database.Query
    """
    # checks first
    if not queries:
        raise ValueError('Expected some `queries`, got {}.'.format(queries))

    if len(queries) == 1:
        return queries[0]

    if isinstance(operators, str):
        operators = [operators] * (len(queries) - 1)

    if len(queries) - 1 != len(operators):
        raise ValueError('Expected `operators` to be a string or a list with the same'
                         ' length as `field_names` ({}), got {}.'.format(len(queries),
                                                                         operators))

    # recursively build the query
    first, rest, end = queries[0], queries[1:-1], queries[-1:][0]
    bigop = getattr(first, operators[0])
    for i, q in enumerate(rest):
        bigop = getattr(bigop(q), operators[i])

    return bigop(end)


def _build_query(field_name, field_value, operator='__eq__'):
    """Create a tinyDB Query object with the format:
    (where(`field_name`) `operator` `field_value`)

    Parameters
    ----------
    field_name: str
        The name of the field to be queried.

    field_value:
        The value of the field

    operator: str
        The comparison operator.
        Check TinyDB.Query class for possible choices.

    Returns
    -------
    query: tinydb.database.Query
    """
    qelem = where(field_name)

    if not hasattr(qelem, operator):
        raise NotImplementedError('Operator `{}` not found in query object.'.format(operator))
    else:
        query = getattr(qelem, operator)

    return query(field_value)


class PetitDB(TinyDB):
    """A generic TinyDB subclass that defines operations for: unique values and meta-queries."""

    def __init__(self, file_path, storage=CachingMiddleware(JSONStorage)):
        self._db_fpath = file_path
        self._storage  = storage
        super(PetitDB, self).__init__(self._db_fpath) #, storage=self._storage)

    def search_by_eid(self, table_name, eid):
        """Return the element in `table_name` with Object ID `eid`.
        If None is found will raise a KeyError exception.

        Parameters
        ----------
        table_name: str
            The name of the table to look in.

        eid: int
            The Object ID of the element to look for.

        Returns
        -------
        elem: tinydb.database.Element

        Raises
        ------
        KeyError
            If the element with ID `eid` is not found.
        """
        elem = self.table(table_name).get(eid=eid)
        if elem is None:
            raise KeyError('Could not find {} with eid {}.'.format(table_name, eid))

        return elem

    def insert_unique(self, table_name, data, unique_fields=None, *, raise_if_found=False):
        """Insert `data` into `table` ensuring that data has unique values
        in `table` for the fields listed in `unique_fields`.

        If `raise_if_found` is True, will raise an NotUniqueItemError if
        another item with the same `unique_fields` values are found
        previously in `table`.
        If False, will return the `eid` from the item found.

        Parameters
        ----------
        table_name: str

        data: dict

        unique_fields: list of str
            Name of fields (keys) from `data` which are going to be used to build
            a sample to look for exactly the same values in the database.
            If None, will use every key in `data`.

        raise_if_found: bool

        Returns
        -------
        eid: int
            Id of the object inserted or the one found with same `unique_fields`.

        Raises
        ------
        MoreThanOneItemError
            Raise even with `raise_with_found` == False if it finds more than one item
            with the same values as the sample.

        NotUniqueItemError
            If `raise_if_found` is True and an item with the same `unique_fields`
            values from `data` is found in `table`.
        """
        return insert_unique(table=self.table(table_name),
                             data=_to_string(data),
                             unique_fields=unique_fields,
                             raise_if_found=raise_if_found)

    def search_unique(self, table_name, sample, unique_fields=None):
        """ Search in `table` an item with the value of the `unique_fields` in the `data` sample.
        Check if the the obtained result is unique. If nothing is found will return an empty list,
        if there is more than one item found, will raise an IndexError.

        Parameters
        ----------
        table_name: str

        sample: dict
            Sample data

        unique_fields: list of str
            Name of fields (keys) from `data` which are going to be used to build
            a sample to look for exactly the same values in the database.
            If None, will use every key in `data`.

        Returns
        -------
        eid: int
            Id of the object found with same `unique_fields`.
            None if none is found.

        Raises
        ------
        MoreThanOneItemError
            If more than one example is found.
        """
        return search_unique(table=self.table(table_name),
                             sample=sample,
                             unique_fields=unique_fields)

    def search_sample(self, table_name, sample):
        """Search for items in `table` that have the same field sub-set values as in `sample`.

        Parameters
        ----------
        table_name: str

        sample: dict
            Sample data

        Returns
        -------
        search_result: list of dict
            List of the items found. The list is empty if no item is found.
        """
        return search_sample(table=self.table(table_name),
                             sample=sample)

    def is_unique(self, table_name, sample, unique_fields=None):
        """Return True if an item with the value of `unique_fields`
        from `data` is unique in the table with `table_name`.
        False if no sample is found or more than one is found.

        See function `find_unique` for more details.

        Parameters
        ----------
        table_name: str

        sample: dict
            Sample data for query

        unique_fields: str or list of str

        Returns
        -------
        is_unique: bool
        """
        try:
            eid = find_unique(self.table(table_name),
                              sample=sample,
                              unique_fields=unique_fields)
        except:
            return False
        else:
            return eid is not None

    def update_unique(self, table_name, fields, data, cond=None, unique_fields=None,
                      *, raise_if_not_found=False):
        """Update the unique matching element to have a given set of fields.

        Parameters
        ----------
        table_name: str

        fields: dict or function[dict -> None]
            new data/values to insert into the unique element
            or a method that will update the elements.

        data: dict
            Sample data for query

        cond: tinydb.Query
            which elements to update

        unique_fields: list of str

        raise_if_not_found: bool
            Will raise an exception if the element is not found for update.

        Returns
        -------
        eid: int
            The eid of the updated element if found, None otherwise.
        """
        eid = find_unique(self.table(table_name), data, unique_fields)

        if eid is None:
            if raise_if_not_found:
                msg  = 'Could not find {} with {}'.format(table_name, data)
                if cond is not None:
                    msg += ' where {}.'.format(cond)
                raise IndexError(msg)

        else:
            self.table(table_name).update(_to_string(fields), cond=cond, eids=[eid])

        return eid

    def count(self, table_name, sample):
        """Return the number of items that match the `sample` field values
        in table `table_name`.
        Check function search_sample for more details.
        """
        return len(list(search_sample(table=self.table(table_name),
                                      sample=sample)))

