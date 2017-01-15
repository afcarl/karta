""" Basic unit tests for geometry classes """

from __future__ import division
import unittest
import math
import numpy as np

from karta.vector.geometry import (Point, Line, Polygon,
                                   Multipoint, Multiline, Multipolygon)
from karta.vector.geometry import affine_matrix, _flatten
from karta.crs import (Cartesian, SphericalEarth,
                       LonLatWGS84, NSIDCNorth, ProjectedCRS)
from karta.errors import CRSError

class TestGeometry(unittest.TestCase):
    """ Tests for manipulating Geometry objects (indexing, iteration, equality,
    etc.)
    """

    def setUp(self):
        self.vertices = [(2.0, 9.0, 9.0), (4.0, 1.0, 9.0), (4.0, 1.0, 5.0),
                         (2.0, 8.0, 0.0), (9.0, 8.0, 4.0), (1.0, 4.0, 6.0),
                         (7.0, 3.0, 4.0), (2.0, 5.0, 3.0), (1.0, 6.0, 6.0),
                         (8.0, 1.0, 0.0), (5.0, 5.0, 1.0), (4.0, 5.0, 7.0),
                         (3.0, 3.0, 5.0), (9.0, 0.0, 9.0), (6.0, 3.0, 8.0),
                         (4.0, 5.0, 7.0), (9.0, 9.0, 4.0), (1.0, 4.0, 7.0),
                         (1.0, 7.0, 8.0), (9.0, 1.0, 6.0)]

        self.data = {"a": [99.0, 2.0, 60.0, 75.0, 71.0, 34.0, 1.0, 49.0, 4.0,
            36.0, 47.0, 58.0, 65.0, 72.0, 4.0, 27.0, 52.0, 37.0, 95.0, 17.0]}
        return

    def test_point_equality(self):
        pt1 = Point((3.0, 4.0))
        pt2 = Point((3.0, 4.0, 5.0))
        pt3 = Point((3.0, 4.0, 5.0), properties={"species":"T. officianale", "density":"high"})
        self.assertFalse(pt1 == pt2)
        self.assertFalse(pt1 == pt3)
        self.assertFalse(pt2 == pt3)
        return

    def test_point_vertex(self):
        point = Point((1.0, 2.0, 3.0), properties={"type": "apple", "color": (43,67,10)})
        self.assertEqual(point.get_vertex(), (1.0, 2.0, 3.0))
        return

    def test_point_add(self):
        ptA = Point((1, 2), crs=SphericalEarth)
        ptB = Point((3, 4), crs=LonLatWGS84)
        res = ptA + ptB
        self.assertTrue(isinstance(res, Multipoint))
        self.assertEqual(len(res), 2)
        self.assertEqual(res.crs, SphericalEarth)
        return

    def test_line_add(self):
        lineA = Line([(1, 2), (2, 3)], crs=SphericalEarth)
        lineB = Line([(3, 4), (4, 5)], crs=LonLatWGS84)
        res = lineA + lineB
        self.assertTrue(isinstance(res, Multiline))
        self.assertEqual(len(res), 2)
        self.assertEqual(res.crs, SphericalEarth)
        return

    def test_polygon_add(self):
        polyA = Polygon([(1, 2), (2, 3), (5, 4)], crs=SphericalEarth)
        polyB = Polygon([(3, 4), (4, 5), (6, 5)], crs=LonLatWGS84)
        res = polyA + polyB
        self.assertTrue(isinstance(res, Multipolygon))
        self.assertEqual(len(res), 2)
        self.assertEqual(res.crs, SphericalEarth)
        return

    def test_multipoint_subset(self):
        mp = Multipoint(self.vertices, data=self.data)
        line = Line(self.vertices)
        ss1 = mp._subset(range(2,7))
        ss2 = line._subset(range(2,7))
        self.assertTrue(isinstance(ss1, Multipoint))
        self.assertTrue(isinstance(ss2, Line))
        return

    def test_multipoint_get(self):
        mp = Multipoint(self.vertices, data=self.data)
        point = Point(self.vertices[0], properties={"a": 99.0})
        self.assertEqual(mp[0], point)
        return

    def test_multipoint_set(self):
        mp1 = Multipoint([(3.0, 3.0), (5.0, 1.0), (3.0, 1.0),
                         (4.0, 4.0), (0.0, 1.0)],
                         data={"name": ["rankin", "corbet", "arviat",
                                        "severn", "churchill"]})
        mp2 = Multipoint([(3.0, 3.0), (5.0, 1.0), (4.0, 5.0),
                         (4.0, 4.0), (0.0, 1.0)],
                         data={"name": ["rankin", "corbet", "umiujaq",
                                        "severn", "churchill"]})
        mp1[2] = (4.0, 5.0)
        self.assertNotEqual(mp1, mp2)
        mp1[2] = Point((4.0, 5.0), properties={"name": "umiujaq"})
        self.assertEqual(mp1, mp2)
        return

    def test_multipoint_iterator(self):
        mp = Multipoint([(3.0, 3.0), (5.0, 1.0), (3.0, 1.0),
                         (4.0, 4.0), (0.0, 1.0)],
                         data={"name": ["rankin", "corbet", "arviat",
                                        "severn", "churchill"]})
        for i, pt in enumerate(mp):
            self.assertEqual(mp[i], pt)
        return

    def test_multipoint_get_data_fields(self):
        mp = Multipoint([(3.0, 3.0), (5.0, 1.0), (3.0, 1.0),
                         (4.0, 4.0), (0.0, 1.0)],
                         data={"location": ["rankin", "corbet", "arviat",
                                            "severn", "churchill"]})
        pt = mp[3]
        self.assertEqual(pt.properties, {"location":"severn"})
        return

    def test_multipoint_slicing1(self):
        mp = Multipoint(self.vertices, data=self.data)
        submp = Multipoint(self.vertices[5:10], data={"a": self.data["a"][5:10]})
        self.assertEqual(mp[5:10], submp)

    def test_multipoint_slicing2(self):
        mp = Multipoint(self.vertices, data=self.data)
        submp = Multipoint(self.vertices[5:], data={"a": self.data["a"][5:]})
        self.assertEqual(mp[5:], submp)
        return

    def test_multipoint_slicing3(self):
        mp = Multipoint(np.arange(214).reshape([107, 2]))
        self.assertEqual(len(mp[::10]), 11)
        return

    def test_multipoint_negative_index(self):
        mp = Multipoint(self.vertices, data=self.data)
        self.assertEqual(mp[len(mp)-1], mp[-1])
        return

    def test_line_extend(self):
        ln0a = Line([(3.0, 3.0, 2.0), (5.0, 1.0, 0.0), (3.0, 1.0, 5.0)])
        ln0b = Line([(4.0, 4.0, 6.0), (0.0, 1.0, 3.0)])
        ln1 = Line([(3.0, 3.0, 2.0), (5.0, 1.0, 0.0), (3.0, 1.0, 5.0),
                    (4.0, 4.0, 6.0), (0.0, 1.0, 3.0)])
        ln0a.extend(ln0b)
        self.assertEqual(ln0a, ln1)

    def test_poly_getitem(self):
        poly = Polygon([(0.0, 8.0), (0.0, 5.0), (6.0, 1.0), (7.0, 2.0),
                        (5.0, 4.0)])
        sub = poly[:3]
        self.assertEqual(sub, Line([(0.0, 8.0), (0.0, 5.0), (6.0, 1.0)]))
        return

    def test_poly_getitem2(self):
        poly = Polygon([(0.0, 8.0), (0.0, 5.0), (6.0, 1.0), (7.0, 2.0),
                        (5.0, 4.0)])
        sub = poly[:4:2]
        self.assertEqual(sub, Line([(0.0, 8.0), (6.0, 1.0)]))
        return

    def test_poly_getitem3(self):
        poly = Polygon([(0.0, 8.0), (0.0, 5.0), (6.0, 1.0), (7.0, 2.0),
                        (5.0, 4.0)])
        sub = poly[:]
        self.assertEqual(sub, poly)
        return

    def test_segments(self):
        line = Line(self.vertices)
        for i, seg in enumerate(line.segments):
            self.assertTrue(np.all(np.equal(seg.vertices[0], self.vertices[i])))
            self.assertTrue(np.all(np.equal(seg.vertices[1], self.vertices[i+1])))
        return

class TestGeometryAnalysis(unittest.TestCase):
    """ Tests for analysis methods of geometrical objects """

    def setUp(self):
        self.vertices = [(2.0, 9.0, 9.0), (4.0, 1.0, 9.0), (4.0, 1.0, 5.0),
                         (2.0, 8.0, 0.0), (9.0, 8.0, 4.0), (1.0, 4.0, 6.0),
                         (7.0, 3.0, 4.0), (2.0, 5.0, 3.0), (1.0, 6.0, 6.0),
                         (8.0, 1.0, 0.0), (5.0, 5.0, 1.0), (4.0, 5.0, 7.0),
                         (3.0, 3.0, 5.0), (9.0, 0.0, 9.0), (6.0, 3.0, 8.0),
                         (4.0, 5.0, 7.0), (9.0, 9.0, 4.0), (1.0, 4.0, 7.0),
                         (1.0, 7.0, 8.0), (9.0, 1.0, 6.0)]

        self.data = {"a" :[99.0, 2.0, 60.0, 75.0, 71.0, 34.0, 1.0, 49.0, 4.0,
            36.0, 47.0, 58.0, 65.0, 72.0, 4.0, 27.0, 52.0, 37.0, 95.0, 17.0]}
        return

    def test_point_azimuth(self):
        point = Point((1.0, 2.0))

        other = Point((2.0, 3.0))
        self.assertEqual(point.azimuth(other), 0.25*180)

        other = Point((0.0, 3.0))
        self.assertEqual(point.azimuth(other), -0.25*180)

        other = Point((0.0, 1.0))
        self.assertEqual(point.azimuth(other), -0.75*180)

        other = Point((2.0, 1.0))
        self.assertEqual(point.azimuth(other), 0.75*180)

        other = Point((1.0, 3.0))
        self.assertEqual(point.azimuth(other), 0.0)

        other = Point((1.0, 1.0))
        self.assertEqual(point.azimuth(other), -180.0)
        return

    def test_point_azimuth2(self):
        point = Point((5.0, 2.0))
        other = Point((5.0, 2.0))
        self.assertTrue(np.isnan(point.azimuth(other)))
        return

    def test_point_azimuth3(self):
        """ Verify with:

        printf "0 -1000000\n100000 -900000" | proj +proj=stere +lat_0=90 +lat_ts=70 +lon_0=-45 +k=1 +x_0=0 +y_0=0 +units=m +datum=WGS84 +no_defs -I -s | tr '\n' ' ' | invgeod +ellps=WGS84 -f "%.6f"
        """
        point = Point((0.0, -10e5), crs=NSIDCNorth)
        other = Point((1e5, -9e5), crs=NSIDCNorth)
        self.assertAlmostEqual(point.azimuth(other, projected=False), 45.036973, places=6)
        return

    def test_nearest_to(self):
        point = Point((1.0, 2.0, 3.0), properties={"type": "apple", "color": (43,67,10)})
        mp = Multipoint(self.vertices, data=self.data)
        self.assertEqual(mp.nearest_vertex_to(point), 12)
        return

    def test_point_shift(self):
        point = Point((1.0, 2.0, 3.0), properties={"type": "apple", "color": (43,67,10)})
        point2 = Point((-3.0, 5.0, 3.0), properties={"type": "apple", "color":(43,67,10)})
        point_shifted = point2.shift((4.0, -3.0))
        self.assertEqual(point, point_shifted)
        return

    def test_line_shift(self):
        line0 = Line(self.vertices)
        vertices = [(a-1, b+2, c) for (a,b,c) in self.vertices]
        line = Line(vertices).shift((1, -2))
        self.assertEqual(line, line0)
        return

    def test_multipoint_shift(self):
        mp0 = Multipoint(self.vertices, data=self.data)
        vertices = [(a-1, b+2, c) for (a,b,c) in self.vertices]
        mp = Multipoint(vertices, data=self.data).shift((1, -2))
        self.assertEqual(mp, mp0)
        return

    def test_multipoint_bbox(self):
        mp = Multipoint(self.vertices, data=self.data)
        bbox = (1.0, 0.0, 9.0, 9.0)
        self.assertEqual(mp.bbox, bbox)
        return

    def test_empty_multipoint_bbox(self):
        mp = Multipoint([], crs=Cartesian)
        bb = mp.bbox
        for item in bb:
            self.assertTrue(np.isnan(item))

        mp = Multipoint([], crs=LonLatWGS84)
        bb = mp.bbox
        for item in bb:
            self.assertTrue(np.isnan(item))
        return

    def test_multiline_bbox(self):
        geom = Multiline([[(1,2), (3,4), (3,2)],
                          [(6,8),(2,6),(3,0)],
                          [(-3,-4), (7, -1), (3, 2), (2, -3)]],
                         crs=LonLatWGS84)
        self.assertEqual(geom.bbox, (-3, -4, 7, 8))
        return

    def test_multipolygon_bbox(self):
        geom = Multipolygon([[[(1,2), (3,4), (3,2)]],
                             [[(6,8),(2,6),(3,0)]],
                             [[(-3,-4), (7, -1), (3, 2), (2, -3)]]],
                            crs=LonLatWGS84)
        self.assertEqual(geom.bbox, (-3, -4, 7, 8))
        return

    def test_multiline_get_coordinate_lists(self):
        g = Multiline([[(0, 1), (1, 2), (2, 3), (3, 4)],
                       [(5, 3), (4, 2), (3, 1), (2, 0)]])
        lists = g.get_coordinate_lists()
        self.assertTrue(np.all(lists[0] == np.array([[0, 1, 2, 3], [1, 2, 3, 4]])))
        self.assertTrue(np.all(lists[1] == np.array([[5, 4, 3, 2], [3, 2, 1, 0]])))
        return

    def test_multipolygon(self):
        g = Multipolygon([[[(0, 1), (1, 2), (2, 3), (3, 4)]],
                          [[(5, 3), (4, 2), (3, 1), (2, 0)]]])
        lists = g.get_coordinate_lists()
        self.assertTrue(np.all(lists[0] == np.array([[[0, 1, 2, 3], [1, 2, 3, 4]]])))
        self.assertTrue(np.all(lists[1] == np.array([[[5, 4, 3, 2], [3, 2, 1, 0]]])))
        return

    def test_multipoint_bbox_overlap(self):
        poly = Polygon([(0.0, 8.0), (0.0, 5.0), (6.0, 1.0)])
        mp = Multipoint(self.vertices, data=self.data)
        self.assertTrue(mp._bbox_overlap(poly))
        return

    def test_multipoint_within_radius(self):
        vertices = [(float(x),float(y)) for x in range(-10,11)
                                        for y in range(-10,11)]
        ans = [v for v in vertices if math.sqrt(v[0]**2 + v[1]**2) < 5.0]
        mp = Multipoint(vertices)
        sub = mp.within_radius(Point((0,0)), 5.0)
        self.assertEqual(sub, Multipoint(ans))
        return

    def test_multipoint_convex_hull(self):
        vertices = [(953, 198), (986, 271), (937, 305), (934, 464), (967, 595),
                (965, 704), (800, 407), (782, 322), (863, 979), (637, 689),
                (254, 944), (330, 745), (363, 646), (27, 990), (127, 696),
                (286, 352), (436, 205), (88, 254), (187, 85)]
        mp = Multipoint(vertices)
        ch = mp.convex_hull()
        hull_vertices = [(27, 990), (88, 254), (187, 85), (953, 198),
                         (986, 271), (965, 704), (863, 979)]
        self.assertTrue(np.all(np.equal(ch.vertices, hull_vertices)))
        return

    def test_multipoint_convex_hull2(self):
        vertices = [(-158, 175), (-179, 230), (-404, -390), (259, -79), (32,
            144), (-59, 355), (402, 301), (239, 159), (-421, 172), (-482, 26),
            (2, -499), (134, -72), (-412, -12), (476, 235), (-412, 40), (-198,
                -256), (314, 331), (431, -492), (325, -415), (-400, -491)]
        mp = Multipoint(vertices)
        ch = mp.convex_hull()
        hull_vertices = [(-482, 26), (-400, -491), (2, -499), (431, -492),
                         (476, 235), (402, 301), (314, 331), (-59, 355),
                         (-421, 172)]
        self.assertTrue(np.all(np.equal(ch.vertices, hull_vertices)))
        return

    def test_multipoint_convex_hull_sph(self):
        # include a point which is in the planar convex hull but not the spherical one
        vertices = [(-50, 70), (0, 71), (50, 70), (0, 50)]
        mp = Multipoint(vertices, crs=SphericalEarth)
        ch = mp.convex_hull()
        self.assertTrue(np.all(np.equal(ch.vertices, [(-50, 70), (0, 50), (50, 70)])))
        return

    def test_connected_multipoint_shortest_distance_to(self):
        line = Line([(0.0, 0.0), (2.0, 2.0), (5.0, 4.0)])
        dist = line.shortest_distance_to(Point((0.0, 2.0)))
        self.assertTrue(abs(dist - math.sqrt(2)) < 1e-10)
        return

    def test_connected_multipoint_shortest_distance_to2(self):
        line = Line([(127.0, -35.0), (132.0, -28.0), (142.0, -29.0)], crs=LonLatWGS84)
        dist = line.shortest_distance_to(Point((98.0, -7.0), crs=LonLatWGS84))
        self.assertAlmostEqual(dist, 4257313.5324397, places=6)
        return

    def test_connected_multipoint_nearest_on_boundary(self):
        line = Line([(0.0, 0.0), (2.0, 2.0), (5.0, 4.0)])
        npt = line.nearest_on_boundary(Point((0.0, 2.0)))
        self.assertEqual(npt, Point((1.0, 1.0)))
        return

    def assertPointAlmostEqual(self, a, b):
        for (a_, b_) in zip(a.vertex, b.vertex):
            self.assertAlmostEqual(a_, b_, places=5)
        self.assertEqual(a.properties, b.properties)
        self.assertEqual(a.crs, b.crs)
        return

    def test_connected_multipoint_nearest_on_boundary2(self):
        line = Line([(-40, 0.0), (35, 0.0)], crs=LonLatWGS84)
        npt = line.nearest_on_boundary(Point((30.0, 80.0), crs=LonLatWGS84))
        self.assertPointAlmostEqual(npt, Point((30.0, 0.0), crs=LonLatWGS84))
        return

    def test_connected_multipoint_nearest_on_boundary3(self):
        # This is the test that tends to break naive root finding schemes
        line = Line([(-40, 0.0), (35, 0.0)], crs=LonLatWGS84)
        npt = line.nearest_on_boundary(Point((30.0, 1e-8), crs=LonLatWGS84))
        self.assertPointAlmostEqual(npt, Point((30.0, 0.0), crs=LonLatWGS84))
        return

    def test_connected_multipoint_nearest_on_boundary4(self):
        line = Line([(-20.0, 32.0), (-26.0, 43.0), (-38.0, 39.0)], crs=LonLatWGS84)
        npt = line.nearest_on_boundary(Point((-34.0, 52.0), crs=LonLatWGS84))
        self.assertPointAlmostEqual(npt, Point((-27.98347, 42.456316), crs=LonLatWGS84))
        return

    def test_poly_extent(self):
        poly = Polygon([(0.0, 8.0), (0.0, 5.0), (6.0, 1.0)])
        poly3 = Polygon([(0.0, 8.0, 0.5), (0.0, 5.0, 0.8), (6.0, 1.0, 0.6)])
        self.assertEqual(poly.get_extent(), (0.0, 6.0, 1.0, 8.0))
        self.assertEqual(poly3.get_extent(), (0.0, 6.0, 1.0, 8.0))
        return

    def test_poly_extent_foreign_crs(self):
        poly = Polygon([(0.0, 8.0), (0.0, 5.0), (6.0, 1.0)], crs=LonLatWGS84)
        poly3 = Polygon([(0.0, 8.0, 0.5), (0.0, 5.0, 0.8), (6.0, 1.0, 0.6)],
                        crs=LonLatWGS84)
        x, y = zip(*poly.get_vertices(crs=NSIDCNorth))
        self.assertEqual(poly.get_extent(NSIDCNorth),
                         (min(x), max(x), min(y), max(y)))
        self.assertEqual(poly3.get_extent(NSIDCNorth),
                         (min(x), max(x), min(y), max(y)))
        return

    def test_poly_length(self):
        poly = Polygon([(0.0, 8.0), (0.0, 5.0), (6.0, 1.0)])
        self.assertEqual(poly.perimeter, 19.430647008220866)
        return

    def test_poly_centroid(self):
        poly = Polygon([(0,0), (1,0), (1,1), (0,1)], properties={"name": "features1"})
        c = poly.centroid
        self.assertEqual(c.x, 0.5)
        self.assertEqual(c.y, 0.5)
        self.assertEqual(c.properties, poly.properties)
        return

    def test_poly_centroid2(self):
        poly = Polygon([(0,0), (1,0), (2,0.5), (1,1), (0,1)], properties={"name": "features1"})
        c = poly.centroid
        self.assertAlmostEqual(c.x, 7/9)
        self.assertEqual(c.y, 0.5)
        self.assertEqual(c.properties, poly.properties)
        return

    def test_poly_rotate(self):
        poly = Polygon([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
        rot45 = poly.rotate(45, (0.5, 0.5))
        self.assertTrue(np.allclose(rot45.coordinates,
                                    np.array([[ 0.5,  1.20710678, 0.5, -0.20710678],
                                              [-0.20710678, 0.5,  1.20710678, 0.5 ]])))
        rot90 = poly.rotate(90, (0.0, 0.0))
        self.assertTrue(np.allclose(rot90.coordinates,
                                    np.array([[0.0, 0.0, -1.0, -1.0],
                                              [0.0, 1.0, 1.0, 0.0]])))
        return

    def test_ringedpoly_perimeter(self):
        ring = Polygon([(2.0, 2.0), (4.0, 2.0), (3.0, 6.0)])
        ringed_poly = Polygon([(0.0, 0.0), (10, 0.0), (10.0, 10.0), (0.0, 10.0)],
                              subs=[ring])
        self.assertEqual(round(ringed_poly.perimeter, 3), 50.246)
        return

    def test_ringedpoly_area(self):
        ring = Polygon([(2.0, 2.0), (4.0, 2.0), (3.0, 6.0)])
        ringed_poly = Polygon([(0.0, 0.0), (10, 0.0), (10.0, 10.0), (0.0, 10.0)],
                              subs=[ring])
        self.assertEqual(ringed_poly.area, 100 - ring.area)
        return

    def test_area_compute_pi(self):
        r = np.linspace(0, 2*np.pi, 10000)
        x = np.cos(r)
        y = np.sin(r)
        kp = Polygon(zip(x,y))
        self.assertAlmostEqual(kp.area, np.pi, places=6)
        return

    def test_to_points_cartesian(self):
        line = Line([(0.0, 0.0), (4.0, 3.0), (1.0, 7.0)])
        points = line.to_points(1.0)
        ans = [(0., 0.), (0.8, 0.6), (1.6, 1.2), (2.4, 1.8), (3.2, 2.4),
               (4., 3.), (3.4, 3.8), (2.8, 4.6), (2.2, 5.4), (1.6, 6.2),
               (1., 7.)]
        self.assertEqual(len(points), len(ans))
        for pt, vert in zip(points, ans):
            self.assertAlmostEqual(pt.x, vert[0])
            self.assertAlmostEqual(pt.y, vert[1])
        return

    def test_to_points_lonlat(self):
        line = Line([(0.0, 38.0), (-10.5, 33.0), (-6.0, 35.0)], crs=LonLatWGS84)
        points = line.to_points(100000.0)
        ans = [(  0.        , 38.        ), ( -1.00809817, 37.58554833),
               ( -2.01066416, 37.17113146), ( -3.00781084, 36.7567488 ),
               ( -3.99964867, 36.34239982), ( -4.98628577, 35.92808398),
               ( -5.96782797, 35.51380078), ( -6.94437893, 35.09954973),
               ( -7.91604017, 34.68533037), ( -8.88291117, 34.27114226),
               ( -9.84508939, 33.85698498), (-10.80267038, 33.44285814),
               (-10.09466286, 33.19083929), ( -9.15505703, 33.62895663),
               ( -8.21064326, 34.0669835 ), ( -7.26131724, 34.5049191 ),
               ( -6.30697252, 34.94276264)]
        self.assertEqual(len(points), len(ans))
        for pt, vert in zip(points, ans):
            self.assertAlmostEqual(pt.x, vert[0])
            self.assertAlmostEqual(pt.y, vert[1])
        return

    def test_to_npoints_cartesian(self):
        line = Line([(0.0, 0.0), (1.0, 2.0), (3.0, -2.0), (4.0, -1.0),
                     (4.0, 3.0), (3.0, 2.0)])
        points = line.to_npoints(20)
        ans = [Point(v) for v in [(0.0, 0.0),
                                  (0.318619234003536, 0.637238468007072),
                                  (0.637238468007072, 1.274476936014144),
                                  (0.9558577020106079, 1.9117154040212159),
                                  (1.274476936014144, 1.4510461279717122),
                                  (1.59309617001768, 0.8138076599646402),
                                  (1.911715404021216, 0.17656919195756826),
                                  (2.230334638024752, -0.4606692760495037),
                                  (2.5489538720282883, -1.0979077440565757),
                                  (2.867573106031824, -1.7351462120636478),
                                  (3.294395938694146, -1.7056040613058538),
                                  (3.7981771815888177, -1.2018228184111823),
                                  (4.0, -0.5729663008226373),
                                  (4.0, 0.13948796534818164),
                                  (4.0, 0.8519422315190006),
                                  (4.0, 1.5643964976898195),
                                  (4.0, 2.2768507638606383),
                                  (4.0, 2.989305030031457),
                                  (3.5037812428946715, 2.503781242894671),
                                  (3.0, 2.0)]]
        for a,b in zip(points, ans):
            self.assertPointAlmostEqual(a, b)
        return

    def test_to_npoints_lonlat(self):
        line = Line([(0, 40), (120, 40)], crs=LonLatWGS84)
        points = line.to_npoints(20)
        ans = [Point(v, crs=LonLatWGS84) for v in [(0, 40),
                                  (4.006549675732082, 43.200316625343305),
                                  (8.44359845345209, 46.2434129228378),
                                  (13.382442375999254, 49.09308515921458),
                                  (18.894149336762318, 51.705248417290484),
                                  (25.03918819127435, 54.027440893063556),
                                  (31.85052685770255, 55.99968253476488),
                                  (39.31083346558522, 57.55771841446013),
                                  (47.329401349484314, 58.6395037346357),
                                  (55.7308352362257, 59.194673757153645),
                                  (64.26916476377436, 59.19467375715364),
                                  (72.67059865051574, 58.639503734635674),
                                  (80.68916653441482, 57.557718414460105),
                                  (88.14947314229748, 55.999682534764844),
                                  (94.96081180872568, 54.02744089306352),
                                  (101.10585066323772, 51.705248417290456),
                                  (106.61755762400078, 49.09308515921457),
                                  (111.55640154654793, 46.24341292283779),
                                  (115.99345032426793, 43.2003166253433),
                                  (120, 40)]]
        for a,b in zip(points, ans):
            self.assertPointAlmostEqual(a, b)
        return

    def test_to_npoints_lonlat_precision(self):

        line = Line([(-20.247017, 79.683933), (-20.0993, 79.887917),
            (-19.13705, 80.048567), (-18.680467, 80.089333), (-17.451917,
                80.14405), (-16.913233, 80.02715), (-16.631367, 80.022933),
            (-16.194067, 80.0168), (-15.915983, 80.020267), (-15.7763,
                80.021283)], crs=LonLatWGS84)

        for n in range(2, 30):
            self.assertEqual(len(line.to_npoints(n)), n)
        return

class TestMiscellaneous(unittest.TestCase):
    """ Misc testing that doesn't fit well into other test cases """

    def test_hashing(self):
        np.random.seed(49)
        vertices = [(np.random.random(), np.random.random()) for i in range(1000)]
        line0 = Line(vertices, crs=SphericalEarth)
        line1 = Line(vertices, crs=LonLatWGS84)
        mp = Multipoint(vertices, crs=SphericalEarth)
        line2 = Line(vertices, crs=SphericalEarth)
        poly = Polygon(vertices, crs=SphericalEarth)
        point = Point(vertices[0], crs=SphericalEarth)

        self.assertEqual(hash(line0), hash(line2))
        self.assertNotEqual(hash(line0), hash(line1))

        self.assertNotEqual(hash(line0), hash(mp))
        self.assertNotEqual(hash(line0), hash(poly))

        self.assertEqual(hash(point), hash(mp[0]))
        return

    def test_flatten1(self):
        arr0 = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]
        arr1 = [[(1, 2), (3, 4)], [(5, 6), (7, 8), (9, 10)]]
        self.assertEqual(_flatten(arr1), arr0)
        return

    def test_flatten2(self):
        arr0 = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]
        arr1 = [(1, 2), (3, 4), [[(5, 6), (7, 8)], (9, 10)]]
        self.assertEqual(_flatten(arr1), arr0)
        return

    def test_flatten3(self):
        arr0 = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]
        arr1 = [[(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]]
        self.assertEqual(_flatten(arr1), arr0)
        return

class TestGeometryProj(unittest.TestCase):

    def setUp(self):
        self.vancouver = Point((-123.1, 49.25), crs=LonLatWGS84)
        self.ottawa = Point((-75.69, 45.42), crs=LonLatWGS84)
        self.whitehorse = Point((-135.05, 60.72), crs=LonLatWGS84)
        return

    def test_greatcircle(self):
        d1 = self.vancouver.distance(self.ottawa)
        d2 = self.vancouver.distance(self.whitehorse)
        d3 = self.whitehorse.distance(self.ottawa)
        d4 = self.whitehorse.distance(self.vancouver)
        self.assertTrue(abs(d1 - 3549030.70541) < 1e-5)
        self.assertTrue(abs(d2 - 1483327.53922) < 1e-5)
        self.assertTrue(abs(d3 - 4151366.88185) < 1e-5)
        self.assertTrue(abs(d4 - 1483327.53922) < 1e-5)
        return

    def test_azimuth_lonlat(self):
        """ Verify with
        echo "49.25dN 123.1dW 45.42dW 75.69dW" | invgeod +ellps=WGS84 -f "%.6f"
        """
        az1 = self.vancouver.azimuth(self.ottawa)
        az2 = self.vancouver.azimuth(self.whitehorse)
        self.assertAlmostEqual(az1, 78.483344, places=6)
        self.assertAlmostEqual(az2, -26.135827, places=6)
        return

    def test_walk_lonlat(self):
        start = Point((-132.14, 54.01), crs=LonLatWGS84)
        dest = start.walk(5440.0, 106.8)
        self.assertAlmostEqual(dest.x, -132.0605910876)
        self.assertAlmostEqual(dest.y, 53.99584742821)
        return


class TestAffineTransforms(unittest.TestCase):

    def setUp(self):
        self.square = Polygon([(0, 0), (0, 1), (1, 1), (1, 0)])
        return

    def test_translate_point(self):
        pt = Point((0, 0), crs=Cartesian)
        newpt = pt.apply_transform(np.array([[0, 0, 1], [0, 0, 2]]))
        self.assertEqual(newpt.x, 1.0)
        self.assertEqual(newpt.y, 2.0)
        return

    def test_transform_multiline(self):
        g = Multiline([[(0,0), (1,1), (1,2)], [(-3,2),  (-2,-1), (0,1)]])
        pi = math.pi
        gnew = g.apply_transform(np.array([[math.cos(0.5*pi), -math.sin(0.5*pi), 0],
                                           [math.sin(0.5*pi), math.cos(0.5*pi), 0]]))
        l1, l2 = gnew.get_vertices()
        self.assertTrue(np.allclose(l1, np.array([(0,0), (-1,1), (-2,1)])))
        self.assertTrue(np.allclose(l2, np.array([(-2,-3), (1,-2), (-1,0)])))

        gnew2 = gnew.apply_transform(np.array([[2, 0, 0],
                                               [0, -3, 0]]))
        l1, l2 = gnew2.get_vertices()
        self.assertTrue(np.allclose(l1, np.array([(0,0), (-2,-3), (-4,-3)])))
        self.assertTrue(np.allclose(l2, np.array([(-4,9), (2,6), (-2,0)])))
        return

    def test_translate_multipoint(self):
        M = affine_matrix(Multipoint([(0,0), (1,0), (0,1)]),
                          Multipoint([(1,0), (2,0), (1,1)]))
        Mans = np.array([[1, 0, 1], [0, 1, 0]])
        self.assertTrue(np.allclose(M, Mans))

        translated_square = self.square.apply_transform(M)
        ans = np.array([[1, 0], [1, 1], [2, 1], [2, 0]])
        self.assertTrue(np.allclose(translated_square.get_vertices(), ans))
        return

    def test_rotate_multipoint(self):
        s2 = math.sqrt(0.5)
        M = affine_matrix(Multipoint([(0,0), (1,0), (0,1)]),
                          Multipoint([(0,0), (s2,s2), (-s2,s2)]))
        Mans = np.array([[s2, -s2, 0], [s2, s2, 0]])
        self.assertTrue(np.allclose(M, Mans))

        translated_square = self.square.apply_transform(M)
        ans = np.array([[0, 0], [-s2, s2], [0, 2*s2], [s2, s2]])
        self.assertTrue(np.allclose(translated_square.get_vertices(), ans))
        return

    def test_stretch_multipoint(self):
        M = affine_matrix(Multipoint([(0,0), (1,0), (0,1)]),
                          Multipoint([(0,0), (2,0), (0,2)]))
        Mans = np.array([[2, 0, 0], [0, 2, 0]])
        self.assertTrue(np.allclose(M, Mans))

        translated_square = self.square.apply_transform(M)
        ans = np.array([[0, 0], [0, 2], [2, 2], [2, 0]])
        self.assertTrue(np.allclose(translated_square.get_vertices(), ans))
        return

class VectorCRSTests(unittest.TestCase):

    def assertTupleAlmostEqual(self, t1, t2, places=7):
        self.assertEqual(len(t1), len(t2))
        for (a,b) in zip(t1, t2):
            self.assertAlmostEqual(a, b, places=places)
        return

    def test_vertices_in_crs(self):
        point = Point((-123.0, 49.0), crs=SphericalEarth)
        self.assertEqual(point.get_vertex(SphericalEarth), (-123.0, 49.0))

    def test_vertices_in_crs2(self):
        point = Point((-123.0, 49.0), crs=LonLatWGS84)
        BCAlbers = ProjectedCRS("+proj=aea +lat_1=50 +lat_2=58.5 +lat_0=45 "
                    "+lon_0=-126 +x_0=1000000 +y_0=0 +ellps=GRS80 +datum=NAD83 "
                    "+units=m +no_defs", "BC Albers")
        self.assertTupleAlmostEqual(point.get_vertex(BCAlbers),
                                    (1219731.770879303, 447290.49891930853))
        return

    def test_vertices_in_crs3(self):
        line = Line([(2.0, 34.0),
                     (2.15, 34.2),
                     (2.7, 34.1)], crs=LonLatWGS84)
        UTM31N = ProjectedCRS("+proj=utm +zone=31 +ellps=WGS84 "
                    "+datum=WGS84 +units=m +no_defs", "UTM 31N (WGS 84)")
        ans = [[407650.39665729, 3762606.65987638],
               [421687.71905897, 3784658.46708431],
               [472328.10951276, 3773284.48524179]]
        for v0, v1 in zip(line.get_vertices(UTM31N), ans):
            self.assertTupleAlmostEqual(v0, v1, places=6)
        return

class WalkTests(unittest.TestCase):

    def test_walk_cartesian(self):
        start = Point((-3, -4), crs=Cartesian)
        dest = start.walk(5.0, 90-math.atan2(4.0, 3.0)*180/math.pi)
        self.assertAlmostEqual(dest.x, 0.0)
        self.assertAlmostEqual(dest.y, 0.0)
        return

    def test_walk(self):
        start = Point((-123.1, 49.25), crs=LonLatWGS84)
        dest = start.walk(1e5, 80.0)
        self.assertAlmostEqual(dest.x, -121.743196, places=6)
        self.assertAlmostEqual(dest.y, 49.398187, places=6)
        return

    def test_walk_albers_geodetic(self):
        AlaskaAlbers = ProjectedCRS("+proj=aea +lat_1=55 +lat_2=65 +lat_0=50 +lon_0=-154 "
                                "+x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs",
                                "+ellps=GRS80")
        start = Point((-2658638, 2443580), crs=AlaskaAlbers)
        dest = start.walk(4500, 195.0, projected=False)
        self.assertAlmostEqual(dest.x, -2662670.889, places=3)
        self.assertAlmostEqual(dest.y, 2441551.155, places=3)

    def test_walk_albers_projected(self):
        AlaskaAlbers = ProjectedCRS("+proj=aea +lat_1=55 +lat_2=65 +lat_0=50 +lon_0=-154 "
                                "+x_0=0 +y_0=0 +ellps=GRS80 +datum=NAD83 +units=m +no_defs",
                                "+ellps=GRS80")
        start = Point((-2658638, 2443580), crs=AlaskaAlbers)
        dest = start.walk(4500, 195.0)
        self.assertAlmostEqual(dest.x, -2659802.686, places=3)
        self.assertAlmostEqual(dest.y, 2439233.334, places=3)
        return

class TableAttributeTests(unittest.TestCase):

    def test_table_attribute_str(self):
        g = Multipoint(zip(range(5), range(5, 0, -1)),
                 data={"a": range(5), "b": [a**2 for a in range(-2, 3)]})
        self.assertEqual(g.d["a"], list(range(5)))
        self.assertEqual(g.d["b"], [a**2 for a in range(-2, 3)])
        return

    def test_table_attribute_int(self):
        g = Multipoint(zip(range(5), range(5, 0, -1)),
                 data={"a": range(5), "b": [a**2 for a in range(-2, 3)]})
        self.assertEqual(g.d[3], {"a": 3, "b": 1})
        return

    def test_None_data(self):
        g = Multipoint(zip(range(5), range(5, 0, -1)))
        self.assertEqual(g.d[0], {})
        return

if __name__ == "__main__":
    unittest.main()
