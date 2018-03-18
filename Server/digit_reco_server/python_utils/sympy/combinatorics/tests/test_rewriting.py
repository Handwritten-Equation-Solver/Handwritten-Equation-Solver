from sympy.combinatorics.fp_groups import FpGroup
from sympy.combinatorics.free_groups import free_group

def test_rewriting():
    F, a, b = free_group("a, b")
    G = FpGroup(F, [a*b*a**-1*b**-1])
    a, b = G.generators
    R = G._rewriting_system
    assert R.is_confluent

    assert G.reduce(b**-1*a) == a*b**-1
    assert G.reduce(b**3*a**4*b**-2*a) == a**5*b
    assert G.equals(b**2*a**-1*b, b**4*a**-1*b**-1)

    G = FpGroup(F, [a**3, b**3, (a*b)**2])
    R = G._rewriting_system
    R.make_confluent()
    # R._is_confluent should be set to True after
    # a successful run of make_confluent
    assert R.is_confluent
    # but also the system should actually be confluent
    assert R._check_confluence()
    assert G.reduce(b*a**-1*b**-1*a**3*b**4*a**-1*b**-15) == a**-1*b**-1
