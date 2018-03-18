"""This tests sympy/core/basic.py with (ideally) no reference to subclasses
of Basic or Atom."""

import collections
import sys

from sympy.core.basic import Basic, Atom, preorder_traversal, as_Basic
from sympy.core.singleton import S, Singleton
from sympy.core.symbol import symbols
from sympy.core.compatibility import default_sort_key, with_metaclass

from sympy import sin, Lambda, Q, cos, gamma, Tuple
from sympy.functions.elementary.exponential import exp
from sympy.utilities.pytest import raises
from sympy.core import I, pi

b1 = Basic()
b2 = Basic(b1)
b3 = Basic(b2)
b21 = Basic(b2, b1)


def test_structure():
    assert b21.args == (b2, b1)
    assert b21.func(*b21.args) == b21
    assert bool(b1)


def test_equality():
    instances = [b1, b2, b3, b21, Basic(b1, b1, b1), Basic]
    for i, b_i in enumerate(instances):
        for j, b_j in enumerate(instances):
            assert (b_i == b_j) == (i == j)
            assert (b_i != b_j) == (i != j)

    assert Basic() != []
    assert not(Basic() == [])
    assert Basic() != 0
    assert not(Basic() == 0)

    class Foo(object):
        """
        Class that is unaware of Basic, and relies on both classes returning
        the NotImplemented singleton for equivalence to evaluate to False.

        """

    b = Basic()
    foo = Foo()

    assert b != foo
    assert foo != b
    assert not b == foo
    assert not foo == b

    class Bar(object):
        """
        Class that considers itself equal to any instance of Basic, and relies
        on Basic returning the NotImplemented singleton in order to achieve
        a symmetric equivalence relation.

        """
        def __eq__(self, other):
            if isinstance(other, Basic):
                return True
            return NotImplemented

        def __ne__(self, other):
            return not self == other

    bar = Bar()

    assert b == bar
    assert bar == b
    assert not b != bar
    assert not bar != b


def test_matches_basic():
    instances = [Basic(b1, b1, b2), Basic(b1, b2, b1), Basic(b2, b1, b1),
                 Basic(b1, b2), Basic(b2, b1), b2, b1]
    for i, b_i in enumerate(instances):
        for j, b_j in enumerate(instances):
            if i == j:
                assert b_i.matches(b_j) == {}
            else:
                assert b_i.matches(b_j) is None
    assert b1.match(b1) == {}


def test_has():
    assert b21.has(b1)
    assert b21.has(b3, b1)
    assert b21.has(Basic)
    assert not b1.has(b21, b3)
    assert not b21.has()


def test_subs():
    assert b21.subs(b2, b1) == Basic(b1, b1)
    assert b21.subs(b2, b21) == Basic(b21, b1)
    assert b3.subs(b2, b1) == b2

    assert b21.subs([(b2, b1), (b1, b2)]) == Basic(b2, b2)

    assert b21.subs({b1: b2, b2: b1}) == Basic(b2, b2)
    if sys.version_info >= (3, 4):
        assert b21.subs(collections.ChainMap({b1: b2}, {b2: b1})) == Basic(b2, b2)
    assert b21.subs(collections.OrderedDict([(b2, b1), (b1, b2)])) == Basic(b2, b2)

    raises(ValueError, lambda: b21.subs('bad arg'))
    raises(ValueError, lambda: b21.subs(b1, b2, b3))


def test_atoms():
    assert b21.atoms() == set()


def test_free_symbols_empty():
    assert b21.free_symbols == set()


def test_doit():
    assert b21.doit() == b21
    assert b21.doit(deep=False) == b21


def test_S():
    assert repr(S) == 'S'


def test_xreplace():
    assert b21.xreplace({b2: b1}) == Basic(b1, b1)
    assert b21.xreplace({b2: b21}) == Basic(b21, b1)
    assert b3.xreplace({b2: b1}) == b2
    assert Basic(b1, b2).xreplace({b1: b2, b2: b1}) == Basic(b2, b1)
    assert Atom(b1).xreplace({b1: b2}) == Atom(b1)
    assert Atom(b1).xreplace({Atom(b1): b2}) == b2
    raises(TypeError, lambda: b1.xreplace())
    raises(TypeError, lambda: b1.xreplace([b1, b2]))


def test_Singleton():
    global instantiated
    instantiated = 0

    class MySingleton(with_metaclass(Singleton, Basic)):
        def __new__(cls):
            global instantiated
            instantiated += 1
            return Basic.__new__(cls)

    assert instantiated == 0
    MySingleton() # force instantiation
    assert instantiated == 1
    assert MySingleton() is not Basic()
    assert MySingleton() is MySingleton()
    assert S.MySingleton is MySingleton()
    assert instantiated == 1

    class MySingleton_sub(MySingleton):
        pass
    assert instantiated == 1
    MySingleton_sub()
    assert instantiated == 2
    assert MySingleton_sub() is not MySingleton()
    assert MySingleton_sub() is MySingleton_sub()


def test_preorder_traversal():
    expr = Basic(b21, b3)
    assert list(
        preorder_traversal(expr)) == [expr, b21, b2, b1, b1, b3, b2, b1]
    assert list(preorder_traversal(('abc', ('d', 'ef')))) == [
        ('abc', ('d', 'ef')), 'abc', ('d', 'ef'), 'd', 'ef']

    result = []
    pt = preorder_traversal(expr)
    for i in pt:
        result.append(i)
        if i == b2:
            pt.skip()
    assert result == [expr, b21, b2, b1, b3, b2]

    w, x, y, z = symbols('w:z')
    expr = z + w*(x + y)
    assert list(preorder_traversal([expr], keys=default_sort_key)) == \
        [[w*(x + y) + z], w*(x + y) + z, z, w*(x + y), w, x + y, x, y]
    assert list(preorder_traversal((x + y)*z, keys=True)) == \
        [z*(x + y), z, x + y, x, y]


def test_sorted_args():
    x = symbols('x')
    assert b21._sorted_args == b21.args
    raises(AttributeError, lambda: x._sorted_args)

def test_call():
    x, y = symbols('x y')
    # See the long history of this in issues 5026 and 5105.

    raises(TypeError, lambda: sin(x)({ x : 1, sin(x) : 2}))
    raises(TypeError, lambda: sin(x)(1))

    # No effect as there are no callables
    assert sin(x).rcall(1) == sin(x)
    assert (1 + sin(x)).rcall(1) == 1 + sin(x)

    # Effect in the pressence of callables
    l = Lambda(x, 2*x)
    assert (l + x).rcall(y) == 2*y + x
    assert (x**l).rcall(2) == x**4
    # TODO UndefinedFunction does not subclass Expr
    #f = Function('f')
    #assert (2*f)(x) == 2*f(x)

    assert (Q.real & Q.positive).rcall(x) == Q.real(x) & Q.positive(x)


def test_rewrite():
    x, y, z = symbols('x y z')
    a, b = symbols('a b')
    f1 = sin(x) + cos(x)
    assert f1.rewrite(cos,exp) == exp(I*x)/2 + sin(x) + exp(-I*x)/2
    assert f1.rewrite([cos],sin) == sin(x) + sin(x + pi/2, evaluate=False)
    f2 = sin(x) + cos(y)/gamma(z)
    assert f2.rewrite(sin,exp) == -I*(exp(I*x) - exp(-I*x))/2 + cos(y)/gamma(z)


def test_literal_evalf_is_number_is_zero_is_comparable():
    from sympy.integrals.integrals import Integral
    from sympy.core.symbol import symbols
    from sympy.core.function import Function
    from sympy.functions.elementary.trigonometric import cos, sin
    x = symbols('x')
    f = Function('f')

    # issue 5033
    assert f.is_number is False
    # issue 6646
    assert f(1).is_number is False
    i = Integral(0, (x, x, x))
    # expressions that are symbolically 0 can be difficult to prove
    # so in case there is some easy way to know if something is 0
    # it should appear in the is_zero property for that object;
    # if is_zero is true evalf should always be able to compute that
    # zero
    assert i.n() == 0
    assert i.is_zero
    assert i.is_number is False
    assert i.evalf(2, strict=False) == 0

    # issue 10268
    n = sin(1)**2 + cos(1)**2 - 1
    assert n.is_comparable is False
    assert n.n(2).is_comparable is False
    assert n.n(2).n(2).is_comparable


def test_as_Basic():
    assert as_Basic(1) is S.One
    assert as_Basic(()) == Tuple()
    raises(TypeError, lambda: as_Basic([]))
