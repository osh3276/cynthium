import numpy as np
from cynthium.app.engine.simulation.stats import calculate_path_stats
from affine import Affine

def approx(val):
    class Approx:
        def __init__(self, v): self.v = v
        def __eq__(self, other): return abs(self.v - other) < 1e-6
    return Approx(val)

def test_calculate_path_stats_integrated():
    # Create a simple 10x10 elevation map where elevation = row
    elevation_map = np.zeros((10, 10))
    for r in range(10):
        elevation_map[r, :] = r
    
    # Transform: col 0->0, col 1->10 (res=10). row 0->0, row 1->-10 (res=-10)
    # y = 0 + (-10)*row  => row = -y/10
    # x = 0 + 10*col    => col = x/10
    transform = Affine.translation(0, 0) * Affine.scale(10, -10)
    
    # Path from (0,0) to (0,-90)
    # This corresponds to col=0, row from 0 to 9.
    # Waypoints: (0, 0, 0) and (0, -90, 9)
    waypoints = np.array([
        [0, 0, 0],
        [0, -90, 9]
    ])
    
    stats = calculate_path_stats(waypoints, elevation_map, transform)
    
    # We expect elevation to go from 0 to 9.
    # Total distance should be at least 90 (horizontal) + some vertical components.
    assert stats["total_elevation_gain"] == 9.0
    assert stats["net_elevation_change"] == 9.0
    assert stats["total_distance"] >= 90.0

def test_calculate_path_stats_integrated_climb_and_descend():
    elevation_map = np.zeros((10, 10))
    # row 0: 0, row 1: 10, row 2: 0
    elevation_map[0, :] = 0
    elevation_map[1, :] = 10
    elevation_map[2, :] = 0
    
    transform = Affine.translation(0, 0) * Affine.scale(1, -1)
    
    # Path from (0,0) to (0,-2)
    # world (0,0) -> pixel (0,0) -> elev 0
    # world (0,-1) -> pixel (0,1) -> elev 10
    # world (0,-2) -> pixel (0,2) -> elev 0
    waypoints = np.array([
        [0, 0, 0],
        [0, -2, 0]
    ])
    
    stats = calculate_path_stats(waypoints, elevation_map, transform)
    
    # It should see the climb to 10 and descent to 0.
    assert stats["total_elevation_gain"] == 10.0
    assert stats["net_elevation_change"] == 0.0

def test_calculate_path_stats_with_slope():
    # Test directional slope calculation (rise over run)
    elevation_map = np.zeros((10, 10))
    # row 0: 0m, row 1: 1m, row 2: 3m
    elevation_map[0, :] = 0
    elevation_map[1, :] = 1
    elevation_map[2, :] = 3
    
    # transform: resolution is 1m
    transform = Affine.translation(0, 0) * Affine.scale(1, -1)
    
    # Path from (0,0) to (0,-2)
    # Sample 0: (0,0) -> row 0, elev 0
    # Sample 1: (0,-1) -> row 1, elev 1
    # Sample 2: (0,-2) -> row 2, elev 3
    waypoints = np.array([
        [0, 0, 0],
        [0, -2, 0]
    ])
    
    stats = calculate_path_stats(waypoints, elevation_map, transform)
    
    # Segment 1: (0,0,0) to (0,-1,1)
    # horizontal distance = 1.0, vertical distance = 1.0
    # slope = atan2(1, 1) = 45 degrees
    
    # Segment 2: (0,-1,1) to (0,-2,3)
    # horizontal distance = 1.0, vertical distance = 2.0
    # slope = atan2(2, 1) = 63.4349 degrees
    
    expected_slope1 = np.degrees(np.arctan2(1.0, 1.0))
    expected_slope2 = np.degrees(np.arctan2(2.0, 1.0))
    expected_avg = (expected_slope1 + expected_slope2) / 2
    
    assert approx(stats["average_slope"]) == expected_avg
    assert approx(stats["max_slope"]) == expected_slope2
    assert approx(stats["min_slope"]) == expected_slope1

def test_calculate_path_stats_with_downhill():
    # Test directional slope with downhill (negative slope)
    elevation_map = np.zeros((10, 10))
    # row 0: 10m, row 1: 5m, row 2: 0m
    elevation_map[0, :] = 10
    elevation_map[1, :] = 5
    elevation_map[2, :] = 0
    
    transform = Affine.translation(0, 0) * Affine.scale(1, -1)
    
    waypoints = np.array([
        [0, 0, 0],
        [0, -2, 0]
    ])
    
    stats = calculate_path_stats(waypoints, elevation_map, transform)
    
    # Segment 1: elev 10 to 5 -> diff -5, run 1. slope = atan2(-5, 1) = -78.69 deg
    # Segment 2: elev 5 to 0 -> diff -5, run 1. slope = atan2(-5, 1) = -78.69 deg
    
    expected_slope = np.degrees(np.arctan2(-5.0, 1.0))
    
    assert approx(stats["average_slope"]) == expected_slope
    assert approx(stats["max_slope"]) == expected_slope
    assert approx(stats["min_slope"]) == expected_slope

def test_calculate_path_stats_empty():
    points = np.empty((0, 3))
    stats = calculate_path_stats(points)
    assert stats["total_distance"] == 0.0
    assert stats["total_elevation_gain"] == 0.0
    assert stats["net_elevation_change"] == 0.0

def test_calculate_path_stats_single_point():
    points = np.array([[0, 0, 0]])
    stats = calculate_path_stats(points)
    assert stats["total_distance"] == 0.0
    assert stats["total_elevation_gain"] == 0.0
    assert stats["net_elevation_change"] == 0.0

def test_calculate_path_stats_simple_climb():
    # A path from (0,0,0) to (10,0,10)
    points = np.array([
        [0, 0, 0],
        [10, 0, 10]
    ])
    stats = calculate_path_stats(points)
    # distance = sqrt(10^2 + 0^2 + 10^2) = sqrt(200) approx 14.14
    assert approx(stats["total_distance"]) == np.sqrt(200)
    assert stats["total_elevation_gain"] == 10.0
    assert stats["net_elevation_change"] == 10.0

def test_calculate_path_stats_complex():
    # (0,0,0) -> (10,0,10) -> (20,0,5) -> (30,0,15)
    points = np.array([
        [0, 0, 0],
        [10, 0, 10],
        [20, 0, 5],
        [30, 0, 15]
    ])
    stats = calculate_path_stats(points)
    
    # Distances:
    # 0->1: sqrt(100+0+100) = 14.142
    # 1->2: sqrt(100+0+25) = 11.180
    # 2->3: sqrt(100+0+100) = 14.142
    expected_dist = np.sqrt(200) + np.sqrt(125) + np.sqrt(200)
    
    assert approx(stats["total_distance"]) == expected_dist
    # Elevation gains: 10 (0->10) and 10 (5->15). Total = 20.
    assert stats["total_elevation_gain"] == 20.0
    # Net: 15 - 0 = 15.
    assert stats["net_elevation_change"] == 15.0

if __name__ == "__main__":
    test_calculate_path_stats_integrated()
    test_calculate_path_stats_integrated_climb_and_descend()
    test_calculate_path_stats_with_slope()
    test_calculate_path_stats_with_downhill()
    test_calculate_path_stats_empty()
    test_calculate_path_stats_single_point()
    test_calculate_path_stats_simple_climb()
    test_calculate_path_stats_complex()
    print("All tests passed!")
