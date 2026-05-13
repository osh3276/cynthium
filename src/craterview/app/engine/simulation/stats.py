import numpy as np

def calculate_path_stats(points: np.ndarray, elevation_map: np.ndarray = None, transform = None):
    """
    Calculate statistics for a path of 3D points.
    
    If elevation_map and transform are provided, it integrates over the path
    by sampling elevation at every pixel step along the segments.
    
    :param points: np.ndarray of shape (N, 3) representing (x, y, z) coordinates.
    :param elevation_map: 2D numpy array of elevation data.
    :param transform: affine.Affine transform (rasterio style) from pixel to world.
    :return: dict with keys 'total_distance', 'total_elevation_gain', 'net_elevation_change'
    """
    if len(points) < 2:
        return {
            "total_distance": 0.0,
            "total_elevation_gain": 0.0,
            "net_elevation_change": 0.0
        }

    if elevation_map is not None and transform is not None:
        return _calculate_integrated_stats(points, elevation_map, transform)
    
    # Fallback to simple waypoint-only calculation if no map data
    diffs = np.diff(points, axis=0)
    distances = np.linalg.norm(diffs, axis=1)
    total_distance = np.sum(distances)
    z_diffs = diffs[:, 2]
    total_elevation_gain = np.sum(z_diffs[z_diffs > 0])
    net_elevation_change = points[-1, 2] - points[0, 2]
    
    return {
        "total_distance": total_distance,
        "total_elevation_gain": total_elevation_gain,
        "net_elevation_change": net_elevation_change
    }

def _calculate_integrated_stats(waypoints: np.ndarray, elevation_map: np.ndarray, transform):
    total_distance = 0.0
    total_climb_amount = 0.0
    
    # Rasterio transform: x = a*col + b*row + c, y = d*col + e*row + f
    # We need the inverse: (col, row) = ~transform * (x, y)
    inv_transform = ~transform
    
    # Sample path points
    sampled_points = []
    
    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i+1]
        
        # Determine number of samples based on distance and resolution
        # Resolution is approximately transform.a (x) and transform.e (y)
        res = min(abs(transform.a), abs(transform.e))
        dist_2d = np.linalg.norm(p2[:2] - p1[:2])
        
        if dist_2d == 0:
            num_samples = 1
        else:
            num_samples = int(np.ceil(dist_2d / res)) * 2 # Oversample slightly
        
        for j in range(num_samples):
            # Interpolate (x, y)
            frac = j / num_samples
            curr_xy = p1[:2] + frac * (p2[:2] - p1[:2])
            
            # Convert world (x, y) to pixel (col, row)
            col, row = inv_transform * (curr_xy[0], curr_xy[1])
            col, row = int(round(col)), int(round(row))
            
            # Stay within bounds
            row = max(0, min(row, elevation_map.shape[0] - 1))
            col = max(0, min(col, elevation_map.shape[1] - 1))
            
            z = elevation_map[row, col]
            sampled_points.append([curr_xy[0], curr_xy[1], z])
            
    # Add the final waypoint exactly
    sampled_points.append(waypoints[-1])
    
    sampled_points = np.array(sampled_points)
    
    # Calculate stats on sampled points
    diffs = np.diff(sampled_points, axis=0)
    distances = np.linalg.norm(diffs, axis=1)
    total_distance = np.sum(distances)
    
    z_diffs = diffs[:, 2]
    total_climb_amount = np.sum(z_diffs[z_diffs > 0])
    
    net_elevation_change = waypoints[-1, 2] - waypoints[0, 2]
    
    return {
        "total_distance": total_distance,
        "total_climb_amount": total_climb_amount,
        "net_elevation_change": net_elevation_change
    }
