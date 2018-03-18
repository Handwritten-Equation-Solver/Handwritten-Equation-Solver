from __future__ import division

from sympy import Dummy, Rational, S, Symbol, symbols, pi, sqrt, oo
from sympy.core.compatibility import range
from sympy.geometry import (Circle, Ellipse, GeometryError, Line, Point, Polygon, Ray, RegularPolygon, Segment,
                            Triangle, intersection)
from sympy.integrals.integrals import Integral
from sympy.utilities.pytest import raises, slow
from sympy import integrate
from sympy.functions.special.elliptic_integrals import elliptic_e


def test_ellipse_geom():
    x = Symbol('x', real=True)
    y = Symbol('y', real=True)
    t = Symbol('t', real=True)
    y1 = Symbol('y1', real=True)
    half = Rational(1, 2)
    p1 = Point(0, 0)
    p2 = Point(1, 1)
    p4 = Point(0, 1)

    e1 = Ellipse(p1, 1, 1)
    e2 = Ellipse(p2, half, 1)
    e3 = Ellipse(p1, y1, y1)
    c1 = Circle(p1, 1)
    c2 = Circle(p2, 1)
    c3 = Circle(Point(sqrt(2), sqrt(2)), 1)
    l1 = Line(p1, p2)

    # Test creation with three points
    cen, rad = Point(3*half, 2), 5*half
    assert Circle(Point(0, 0), Point(3, 0), Point(0, 4)) == Circle(cen, rad)
    raises(
        GeometryError, lambda: Circle(Point(0, 0), Point(1, 1), Point(2, 2)))

    raises(ValueError, lambda: Ellipse(None, None, None, 1))
    raises(GeometryError, lambda: Circle(Point(0, 0)))

    # Basic Stuff
    assert Ellipse(None, 1, 1).center == Point(0, 0)
    assert e1 == c1
    assert e1 != e2
    assert e1 != l1
    assert p4 in e1
    assert p2 not in e2
    assert e1.area == pi
    assert e2.area == pi/2
    assert e3.area == pi*y1*abs(y1)
    assert c1.area == e1.area
    assert c1.circumference == e1.circumference
    assert e3.circumference == 2*pi*y1
    assert e1.plot_interval() == e2.plot_interval() == [t, -pi, pi]
    assert e1.plot_interval(x) == e2.plot_interval(x) == [x, -pi, pi]

    assert c1.minor == 1
    assert c1.major == 1
    assert c1.hradius == 1
    assert c1.vradius == 1

    # Private Functions
    assert hash(c1) == hash(Circle(Point(1, 0), Point(0, 1), Point(0, -1)))
    assert c1 in e1
    assert (Line(p1, p2) in e1) is False
    assert e1.__cmp__(e1) == 0
    assert e1.__cmp__(Point(0, 0)) > 0

    # Encloses
    assert e1.encloses(Segment(Point(-0.5, -0.5), Point(0.5, 0.5))) is True
    assert e1.encloses(Line(p1, p2)) is False
    assert e1.encloses(Ray(p1, p2)) is False
    assert e1.encloses(e1) is False
    assert e1.encloses(
        Polygon(Point(-0.5, -0.5), Point(-0.5, 0.5), Point(0.5, 0.5))) is True
    assert e1.encloses(RegularPolygon(p1, 0.5, 3)) is True
    assert e1.encloses(RegularPolygon(p1, 5, 3)) is False
    assert e1.encloses(RegularPolygon(p2, 5, 3)) is False

    assert e2.arbitrary_point() in e2

    # Foci
    f1, f2 = Point(sqrt(12), 0), Point(-sqrt(12), 0)
    ef = Ellipse(Point(0, 0), 4, 2)
    assert ef.foci in [(f1, f2), (f2, f1)]

    # Tangents
    v = sqrt(2) / 2
    p1_1 = Point(v, v)
    p1_2 = p2 + Point(half, 0)
    p1_3 = p2 + Point(0, 1)
    assert e1.tangent_lines(p4) == c1.tangent_lines(p4)
    assert e2.tangent_lines(p1_2) == [Line(Point(3/2, 1), Point(3/2, 1/2))]
    assert e2.tangent_lines(p1_3) == [Line(Point(1, 2), Point(5/4, 2))]
    assert c1.tangent_lines(p1_1) != [Line(p1_1, Point(0, sqrt(2)))]
    assert c1.tangent_lines(p1) == []
    assert e2.is_tangent(Line(p1_2, p2 + Point(half, 1)))
    assert e2.is_tangent(Line(p1_3, p2 + Point(half, 1)))
    assert c1.is_tangent(Line(p1_1, Point(0, sqrt(2))))
    assert e1.is_tangent(Line(Point(0, 0), Point(1, 1))) is False
    assert c1.is_tangent(e1) is True
    assert c1.is_tangent(Ellipse(Point(2, 0), 1, 1)) is True
    assert c1.is_tangent(
        Polygon(Point(1, 1), Point(1, -1), Point(2, 0))) is True
    assert c1.is_tangent(
        Polygon(Point(1, 1), Point(1, 0), Point(2, 0))) is False
    assert Circle(Point(5, 5), 3).is_tangent(Circle(Point(0, 5), 1)) is False

    assert Ellipse(Point(5, 5), 2, 1).tangent_lines(Point(0, 0)) == \
        [Line(Point(0, 0), Point(77/25, 132/25)),
     Line(Point(0, 0), Point(33/5, 22/5))]
    assert Ellipse(Point(5, 5), 2, 1).tangent_lines(Point(3, 4)) == \
        [Line(Point(3, 4), Point(4, 4)), Line(Point(3, 4), Point(3, 5))]
    assert Circle(Point(5, 5), 2).tangent_lines(Point(3, 3)) == \
        [Line(Point(3, 3), Point(4, 3)), Line(Point(3, 3), Point(3, 4))]
    assert Circle(Point(5, 5), 2).tangent_lines(Point(5 - 2*sqrt(2), 5)) == \
        [Line(Point(5 - 2*sqrt(2), 5), Point(5 - sqrt(2), 5 - sqrt(2))),
     Line(Point(5 - 2*sqrt(2), 5), Point(5 - sqrt(2), 5 + sqrt(2))), ]

    # for numerical calculations, we shouldn't demand exact equality,
    # so only test up to the desired precision
    def lines_close(l1, l2, prec):
        """ tests whether l1 and 12 are within 10**(-prec)
        of each other """
        return abs(l1.p1 - l2.p1) < 10**(-prec) and abs(l1.p2 - l2.p2) < 10**(-prec)
    def line_list_close(ll1, ll2, prec):
        return all(lines_close(l1, l2, prec) for l1, l2 in zip(ll1, ll2))

    e = Ellipse(Point(0, 0), 2, 1)
    assert e.normal_lines(Point(0, 0)) == \
        [Line(Point(0, 0), Point(0, 1)), Line(Point(0, 0), Point(1, 0))]
    assert e.normal_lines(Point(1, 0)) == \
        [Line(Point(0, 0), Point(1, 0))]
    assert e.normal_lines((0, 1)) == \
        [Line(Point(0, 0), Point(0, 1))]
    assert line_list_close(e.normal_lines(Point(1, 1), 2), [
        Line(Point(-51/26, -1/5), Point(-25/26, 17/83)),
        Line(Point(28/29, -7/8), Point(57/29, -9/2))], 2)
    # test the failure of Poly.intervals and checks a point on the boundary
    p = Point(sqrt(3), S.Half)
    assert p in e
    assert line_list_close(e.normal_lines(p, 2), [
        Line(Point(-341/171, -1/13), Point(-170/171, 5/64)),
        Line(Point(26/15, -1/2), Point(41/15, -43/26))], 2)
    # be sure to use the slope that isn't undefined on boundary
    e = Ellipse((0, 0), 2, 2*sqrt(3)/3)
    assert line_list_close(e.normal_lines((1, 1), 2), [
        Line(Point(-64/33, -20/71), Point(-31/33, 2/13)),
        Line(Point(1, -1), Point(2, -4))], 2)
    # general ellipse fails except under certain conditions
    e = Ellipse((0, 0), x, 1)
    assert e.normal_lines((x + 1, 0)) == [Line(Point(0, 0), Point(1, 0))]
    raises(NotImplementedError, lambda: e.normal_lines((x + 1, 1)))
    # Properties
    major = 3
    minor = 1
    e4 = Ellipse(p2, minor, major)
    assert e4.focus_distance == sqrt(major**2 - minor**2)
    ecc = e4.focus_distance / major
    assert e4.eccentricity == ecc
    assert e4.periapsis == major*(1 - ecc)
    assert e4.apoapsis == major*(1 + ecc)
    assert e4.semilatus_rectum == major*(1 - ecc ** 2)
    # independent of orientation
    e4 = Ellipse(p2, major, minor)
    assert e4.focus_distance == sqrt(major**2 - minor**2)
    ecc = e4.focus_distance / major
    assert e4.eccentricity == ecc
    assert e4.periapsis == major*(1 - ecc)
    assert e4.apoapsis == major*(1 + ecc)

    # Intersection
    l1 = Line(Point(1, -5), Point(1, 5))
    l2 = Line(Point(-5, -1), Point(5, -1))
    l3 = Line(Point(-1, -1), Point(1, 1))
    l4 = Line(Point(-10, 0), Point(0, 10))
    pts_c1_l3 = [Point(sqrt(2)/2, sqrt(2)/2), Point(-sqrt(2)/2, -sqrt(2)/2)]

    assert intersection(e2, l4) == []
    assert intersection(c1, Point(1, 0)) == [Point(1, 0)]
    assert intersection(c1, l1) == [Point(1, 0)]
    assert intersection(c1, l2) == [Point(0, -1)]
    assert intersection(c1, l3) in [pts_c1_l3, [pts_c1_l3[1], pts_c1_l3[0]]]
    assert intersection(c1, c2) == [Point(0, 1), Point(1, 0)]
    assert intersection(c1, c3) == [Point(sqrt(2)/2, sqrt(2)/2)]
    assert e1.intersection(l1) == [Point(1, 0)]
    assert e2.intersection(l4) == []
    assert e1.intersection(Circle(Point(0, 2), 1)) == [Point(0, 1)]
    assert e1.intersection(Circle(Point(5, 0), 1)) == []
    assert e1.intersection(Ellipse(Point(2, 0), 1, 1)) == [Point(1, 0)]
    assert e1.intersection(Ellipse(Point(5, 0), 1, 1)) == []
    assert e1.intersection(Point(2, 0)) == []
    assert e1.intersection(e1) == e1
    assert intersection(Ellipse(Point(0, 0), 2, 1), Ellipse(Point(3, 0), 1, 2)) == [Point(2, 0)]
    assert intersection(Circle(Point(0, 0), 2), Circle(Point(3, 0), 1)) == [Point(2, 0)]
    assert intersection(Circle(Point(0, 0), 2), Circle(Point(7, 0), 1)) == []
    assert intersection(Ellipse(Point(0, 0), 5, 17), Ellipse(Point(4, 0), 1, 0.2)) == [Point(5, 0)]
    assert intersection(Ellipse(Point(0, 0), 5, 17), Ellipse(Point(4, 0), 0.999, 0.2)) == []
    assert Circle((0, 0), 1/2).intersection(
        Triangle((-1, 0), (1, 0), (0, 1))) == [
        Point(-1/2, 0), Point(1/2, 0)]
    raises(TypeError, lambda: intersection(e2, Line((0, 0, 0), (0, 0, 1))))
    raises(TypeError, lambda: intersection(e2, Rational(12)))
    # some special case intersections
    csmall = Circle(p1, 3)
    cbig = Circle(p1, 5)
    cout = Circle(Point(5, 5), 1)
    # one circle inside of another
    assert csmall.intersection(cbig) == []
    # separate circles
    assert csmall.intersection(cout) == []
    # coincident circles
    assert csmall.intersection(csmall) == csmall

    v = sqrt(2)
    t1 = Triangle(Point(0, v), Point(0, -v), Point(v, 0))
    points = intersection(t1, c1)
    assert len(points) == 4
    assert Point(0, 1) in points
    assert Point(0, -1) in points
    assert Point(v/2, v/2) in points
    assert Point(v/2, -v/2) in points

    circ = Circle(Point(0, 0), 5)
    elip = Ellipse(Point(0, 0), 5, 20)
    assert intersection(circ, elip) in \
        [[Point(5, 0), Point(-5, 0)], [Point(-5, 0), Point(5, 0)]]
    assert elip.tangent_lines(Point(0, 0)) == []
    elip = Ellipse(Point(0, 0), 3, 2)
    assert elip.tangent_lines(Point(3, 0)) == \
        [Line(Point(3, 0), Point(3, -12))]

    e1 = Ellipse(Point(0, 0), 5, 10)
    e2 = Ellipse(Point(2, 1), 4, 8)
    a = 53/17
    c = 2*sqrt(3991)/17
    ans = [Point(a - c/8, a/2 + c), Point(a + c/8, a/2 - c)]
    assert e1.intersection(e2) == ans
    e2 = Ellipse(Point(x, y), 4, 8)
    c = sqrt(3991)
    ans = [Point(-c/68 + a, 2*c/17 + a/2), Point(c/68 + a, -2*c/17 + a/2)]
    assert [p.subs({x: 2, y:1}) for p in e1.intersection(e2)] == ans

    # Combinations of above
    assert e3.is_tangent(e3.tangent_lines(p1 + Point(y1, 0))[0])

    e = Ellipse((1, 2), 3, 2)
    assert e.tangent_lines(Point(10, 0)) == \
        [Line(Point(10, 0), Point(1, 0)),
        Line(Point(10, 0), Point(14/5, 18/5))]

    # encloses_point
    e = Ellipse((0, 0), 1, 2)
    assert e.encloses_point(e.center)
    assert e.encloses_point(e.center + Point(0, e.vradius - Rational(1, 10)))
    assert e.encloses_point(e.center + Point(e.hradius - Rational(1, 10), 0))
    assert e.encloses_point(e.center + Point(e.hradius, 0)) is False
    assert e.encloses_point(
        e.center + Point(e.hradius + Rational(1, 10), 0)) is False
    e = Ellipse((0, 0), 2, 1)
    assert e.encloses_point(e.center)
    assert e.encloses_point(e.center + Point(0, e.vradius - Rational(1, 10)))
    assert e.encloses_point(e.center + Point(e.hradius - Rational(1, 10), 0))
    assert e.encloses_point(e.center + Point(e.hradius, 0)) is False
    assert e.encloses_point(
        e.center + Point(e.hradius + Rational(1, 10), 0)) is False
    assert c1.encloses_point(Point(1, 0)) is False
    assert c1.encloses_point(Point(0.3, 0.4)) is True

    assert e.scale(2, 3) == Ellipse((0, 0), 4, 3)
    assert e.scale(3, 6) == Ellipse((0, 0), 6, 6)
    assert e.rotate(pi) == e
    assert e.rotate(pi, (1, 2)) == Ellipse(Point(2, 4), 2, 1)
    raises(NotImplementedError, lambda: e.rotate(pi/3))

    # Circle rotation tests (Issue #11743)
    # Link - https://github.com/sympy/sympy/issues/11743
    cir = Circle(Point(1, 0), 1)
    assert cir.rotate(pi/2) == Circle(Point(0, 1), 1)
    assert cir.rotate(pi/3) == Circle(Point(1/2, sqrt(3)/2), 1)
    assert cir.rotate(pi/3, Point(1, 0)) == Circle(Point(1, 0), 1)
    assert cir.rotate(pi/3, Point(0, 1)) == Circle(Point(1/2 + sqrt(3)/2, 1/2 + sqrt(3)/2), 1)


def test_construction():
    e1 = Ellipse(hradius=2, vradius=1, eccentricity=None)
    assert e1.eccentricity == sqrt(3)/2

    e2 = Ellipse(hradius=2, vradius=None, eccentricity=sqrt(3)/2)
    assert e2.vradius == 1

    e3 = Ellipse(hradius=None, vradius=1, eccentricity=sqrt(3)/2)
    assert e3.hradius == 2

    # filter(None, iterator) filters out anything falsey, including 0
    # eccentricity would be filtered out in this case and the constructor would throw an error
    e4 = Ellipse(Point(0, 0), hradius=1, eccentricity=0)
    assert e4.vradius == 1


def test_ellipse_random_point():
    y1 = Symbol('y1', real=True)
    e3 = Ellipse(Point(0, 0), y1, y1)
    rx, ry = Symbol('rx'), Symbol('ry')
    for ind in range(0, 5):
        r = e3.random_point()
        # substitution should give zero*y1**2
        assert e3.equation(rx, ry).subs(zip((rx, ry), r.args)).equals(0)


def test_repr():
    assert repr(Circle((0, 1), 2)) == 'Circle(Point2D(0, 1), 2)'


def test_transform():
    c = Circle((1, 1), 2)
    assert c.scale(-1) == Circle((-1, 1), 2)
    assert c.scale(y=-1) == Circle((1, -1), 2)
    assert c.scale(2) == Ellipse((2, 1), 4, 2)

    assert Ellipse((0, 0), 2, 3).scale(2, 3, (4, 5)) == \
        Ellipse(Point(-4, -10), 4, 9)
    assert Circle((0, 0), 2).scale(2, 3, (4, 5)) == \
        Ellipse(Point(-4, -10), 4, 6)
    assert Ellipse((0, 0), 2, 3).scale(3, 3, (4, 5)) == \
        Ellipse(Point(-8, -10), 6, 9)
    assert Circle((0, 0), 2).scale(3, 3, (4, 5)) == \
        Circle(Point(-8, -10), 6)
    assert Circle(Point(-8, -10), 6).scale(1/3, 1/3, (4, 5)) == \
        Circle((0, 0), 2)
    assert Circle((0, 0), 2).translate(4, 5) == \
        Circle((4, 5), 2)
    assert Circle((0, 0), 2).scale(3, 3) == \
        Circle((0, 0), 6)


def test_bounds():
    e1 = Ellipse(Point(0, 0), 3, 5)
    e2 = Ellipse(Point(2, -2), 7, 7)
    c1 = Circle(Point(2, -2), 7)
    c2 = Circle(Point(-2, 0), Point(0, 2), Point(2, 0))
    assert e1.bounds == (-3, -5, 3, 5)
    assert e2.bounds == (-5, -9, 9, 5)
    assert c1.bounds == (-5, -9, 9, 5)
    assert c2.bounds == (-2, -2, 2, 2)


def test_reflect():
    b = Symbol('b')
    m = Symbol('m')
    l = Line((0, b), slope=m)
    t1 = Triangle((0, 0), (1, 0), (2, 3))
    assert t1.area == -t1.reflect(l).area
    e = Ellipse((1, 0), 1, 2)
    assert e.area == -e.reflect(Line((1, 0), slope=0)).area
    assert e.area == -e.reflect(Line((1, 0), slope=oo)).area
    raises(NotImplementedError, lambda: e.reflect(Line((1, 0), slope=m)))


def test_is_tangent():
    e1 = Ellipse(Point(0, 0), 3, 5)
    c1 = Circle(Point(2, -2), 7)
    assert e1.is_tangent(Point(0, 0)) is False
    assert e1.is_tangent(Point(3, 0)) is False
    assert e1.is_tangent(e1) is True
    assert e1.is_tangent(Ellipse((0, 0), 1, 2)) is False
    assert e1.is_tangent(Ellipse((0, 0), 3, 2)) is True
    assert c1.is_tangent(Ellipse((2, -2), 7, 1)) is True
    assert c1.is_tangent(Circle((11, -2), 2)) is True
    assert c1.is_tangent(Circle((7, -2), 2)) is True
    assert c1.is_tangent(Ray((-5, -2), (-15, -20))) is False
    assert c1.is_tangent(Ray((-3, -2), (-15, -20))) is False
    assert c1.is_tangent(Ray((-3, -22), (15, 20))) is False
    assert c1.is_tangent(Ray((9, 20), (9, -20))) is True
    assert e1.is_tangent(Segment((2, 2), (-7, 7))) is False
    assert e1.is_tangent(Segment((0, 0), (1, 2))) is False
    assert c1.is_tangent(Segment((0, 0), (-5, -2))) is False
    assert e1.is_tangent(Segment((3, 0), (12, 12))) is False
    assert e1.is_tangent(Segment((12, 12), (3, 0))) is False
    assert e1.is_tangent(Segment((-3, 0), (3, 0))) is False
    assert e1.is_tangent(Segment((-3, 5), (3, 5))) is True
    assert e1.is_tangent(Line((0, 0), (1, 1))) is False
    assert e1.is_tangent(Line((-3, 0), (-2.99, -0.001))) is False
    assert e1.is_tangent(Line((-3, 0), (-3, 1))) is True
    assert e1.is_tangent(Polygon((0, 0), (5, 5), (5, -5))) is False
    assert e1.is_tangent(Polygon((-100, -50), (-40, -334), (-70, -52))) is False
    assert e1.is_tangent(Polygon((-3, 0), (3, 0), (0, 1))) is False
    assert e1.is_tangent(Polygon((-3, 0), (3, 0), (0, 5))) is False
    assert e1.is_tangent(Polygon((-3, 0), (0, -5), (3, 0), (0, 5))) is False
    assert e1.is_tangent(Polygon((-3, -5), (-3, 5), (3, 5), (3, -5))) is True
    assert c1.is_tangent(Polygon((-3, -5), (-3, 5), (3, 5), (3, -5))) is False
    assert e1.is_tangent(Polygon((0, 0), (3, 0), (7, 7), (0, 5))) is False
    assert e1.is_tangent(Polygon((3, 12), (3, -12), (6, 5))) is True
    assert e1.is_tangent(Polygon((3, 12), (3, -12), (0, -5), (0, 5))) is False
    assert e1.is_tangent(Polygon((3, 0), (5, 7), (6, -5))) is False
    raises(TypeError, lambda: e1.is_tangent(Point(0, 0, 0)))
    raises(TypeError, lambda: e1.is_tangent(Rational(5)))


def test_parameter_value():
    t = Symbol('t')
    e = Ellipse(Point(0, 0), 3, 5)
    assert e.parameter_value((3, 0), t) == {t: 0}
    raises(ValueError, lambda: e.parameter_value((4, 0), t))

def test_second_moment_of_area():
    x, y = symbols('x, y')
    e = Ellipse(Point(0, 0), 5, 4)
    I_yy = 2*4*integrate(sqrt(25 - x**2)*x**2, (x, -5, 5))/5
    I_xx = 2*5*integrate(sqrt(16 - y**2)*y**2, (y, -4, 4))/4
    Y = 3*sqrt(1 - x**2/5**2)
    I_xy = integrate(integrate(y, (y, -Y, Y))*x, (x, -5, 5))
    assert I_yy == e.second_moment_of_area()[1]
    assert I_xx == e.second_moment_of_area()[0]
    assert I_xy == e.second_moment_of_area()[2]

def test_circumference():
    M = Symbol('M')
    m = Symbol('m')
    assert Ellipse(Point(0, 0), M, m).circumference == 4 * M * elliptic_e((M ** 2 - m ** 2) / M**2)

    assert Ellipse(Point(0, 0), 5, 4).circumference == 20 * elliptic_e(S(9) / 25)

    # degenerate ellipse
    assert Ellipse(None, 1, None, 1).circumference == 4

    # circle
    assert Ellipse(None, 1, None, 0).circumference == 2*pi

    # test numerically
    assert abs(Ellipse(None, hradius=5, vradius=3).circumference.evalf(16) - 25.52699886339813) < 1e-10
