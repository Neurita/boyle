# -*- coding: utf-8 -*-

from boyle.utils.strings import where_is


def test_where_is():
    alist = [str(i) for i in list(range(10))]

    assert(where_is(alist, '1' ) ==  1)
    assert(where_is(alist, '0' ) ==  0)
    assert(where_is(alist, '9' ) ==  9)
    assert(where_is(alist, '20') == -1)