import numpy as np


def compute_view_angles(camera_pos, target_pos, up_vector):
    """
    Compute matplotlib view_init angles with a specified up vector.

    Parameters:
    -----------
    camera_pos : array-like
        Camera position as (x, y, z)
    target_pos : array-like
        Target/look-at point as (x, y, z)
    up_vector : array-like
        Up direction vector (will be normalized)

    Returns:
    --------
    elev : float
        Elevation angle in degrees
    azim : float
        Azimuth angle in degrees
    roll : float
        Roll angle in degrees
    """

    camera_pos = np.array(camera_pos, dtype=float)
    target_pos = np.array(target_pos, dtype=float)
    up_vector = np.array(up_vector, dtype=float)
    up_vector = up_vector / np.linalg.norm(up_vector)

    # Viewing direction (from camera to target)
    view_dir = target_pos - camera_pos
    view_dir = view_dir / np.linalg.norm(view_dir)

    # Compute azimuth and elevation in the coordinate system where up_vector is "up"
    # Project view_dir onto the plane perpendicular to up_vector
    view_projected = view_dir - np.dot(view_dir, up_vector) * up_vector
    view_projected_norm = np.linalg.norm(view_projected)

    # Elevation: angle between view_dir and the plane perpendicular to up_vector
    elev = np.degrees(np.arcsin(np.dot(view_dir, up_vector)))

    # For azimuth, we need a reference direction perpendicular to both view_dir and up_vector
    # We'll use the global x-axis projected onto the plane perpendicular to up_vector
    ref_dir = np.array([1.0, 0.0, 0.0])
    ref_projected = ref_dir - np.dot(ref_dir, up_vector) * up_vector
    ref_projected = ref_projected / np.linalg.norm(ref_projected)

    # Second reference perpendicular to both up_vector and ref_projected
    ref_perp = np.cross(up_vector, ref_projected)
    ref_perp = ref_perp / np.linalg.norm(ref_perp)

    # Compute azimuth as angle from ref_projected to view_projected
    if view_projected_norm > 1e-6:
        view_projected_normalized = view_projected / view_projected_norm
        azim = np.degrees(np.arctan2(np.dot(view_projected_normalized, ref_perp),
                                     np.dot(view_projected_normalized, ref_projected)))
        if azim < 0:
            azim += 360
    else:
        azim = 0

    # Roll is typically 0 when up_vector is aligned with the camera's up direction
    roll = 0.0

    return elev, azim, roll


def get_symmetry_axis_views(axis_direction, center=None, view_type='all',
                            lateral_angle=0, height=0, distance=2.0):
    """
    Generate view angles for an object with a symmetry axis.
    The camera's up vector always aligns with the symmetry axis.

    Parameters:
    -----------
    axis_direction : array-like
        The symmetry axis direction as (x, y, z), will be normalized
    center : array-like, optional
        Center point of the object. Default is (0, 0, 0)
    view_type : str
        Type of view to compute:
        - 'top': Along positive axis direction
        - 'bottom': Along negative axis direction
        - 'lateral': Perpendicular to axis at specified angle and height
        - 'all': Top, bottom, and lateral views at 0°, 90°, 180°, 270°
    lateral_angle : float
        For lateral views, the angle in degrees around the axis (0 to 360)
    height : float
        Height along the axis from center (-1 to 1, where -1 is bottom, 0 is center, 1 is top)
    distance : float
        Distance of camera from the center point

    Returns:
    --------
    dict or list of dict
        Dictionary/list with keys: 'view_type', 'elev', 'azim', 'roll',
        'camera_pos', 'target_pos', 'lateral_angle', 'height'
    """

    axis_direction = np.array(axis_direction, dtype=float)
    axis_direction = axis_direction / np.linalg.norm(axis_direction)

    if center is None:
        center = np.array([0, 0, 0], dtype=float)
    else:
        center = np.array(center, dtype=float)

    results = []

    # Top view: camera along positive axis direction
    if view_type in ['top', 'all']:
        camera_pos = center + axis_direction * distance
        target_pos = center  # Always looking at center height
        elev, azim, roll = compute_view_angles(camera_pos, target_pos, axis_direction)
        results.append({
            'view_type': 'top',
            'elev': elev,
            'azim': azim,
            'roll': roll,
            'camera_pos': camera_pos,
            'target_pos': target_pos,
            'lateral_angle': None,
            'height': 0,
            'description': 'Top view: looking along positive symmetry axis'
        })

    # Bottom view: camera along negative axis direction
    if view_type in ['bottom', 'all']:
        camera_pos = center - axis_direction * distance
        target_pos = center  # Always looking at center height
        elev, azim, roll = compute_view_angles(camera_pos, target_pos, axis_direction)
        results.append({
            'view_type': 'bottom',
            'elev': elev,
            'azim': azim,
            'roll': roll,
            'camera_pos': camera_pos,
            'target_pos': target_pos,
            'lateral_angle': None,
            'height': 0,
            'description': 'Bottom view: looking along negative symmetry axis'
        })

    # Lateral views: perpendicular to axis
    if view_type in ['lateral', 'all']:
        # Find two orthogonal vectors perpendicular to the axis
        if abs(axis_direction[0]) < 0.9:
            perp1 = np.array([1, 0, 0], dtype=float)
        else:
            perp1 = np.array([0, 1, 0], dtype=float)

        perp1 = perp1 - np.dot(perp1, axis_direction) * axis_direction
        perp1 = perp1 / np.linalg.norm(perp1)

        # Second perpendicular vector
        perp2 = np.cross(axis_direction, perp1)
        perp2 = perp2 / np.linalg.norm(perp2)

        if view_type == 'lateral':
            # Single lateral view at specified angle and height
            angle_rad = np.radians(lateral_angle)
            direction = np.cos(angle_rad) * perp1 + np.sin(angle_rad) * perp2
            camera_pos = center + direction * distance + axis_direction * height
            target_pos = center + axis_direction * height
            elev, azim, roll = compute_view_angles(camera_pos, target_pos, axis_direction)
            results.append({
                'view_type': 'lateral',
                'elev': elev,
                'azim': azim,
                'roll': roll,
                'camera_pos': camera_pos,
                'target_pos': target_pos,
                'lateral_angle': lateral_angle,
                'height': height,
                'description': f'Lateral view at {lateral_angle}° and height {height}'
            })
        else:
            # Multiple lateral views at different angles
            for angle in [0, 90, 180, 270]:
                angle_rad = np.radians(angle)
                direction = np.cos(angle_rad) * perp1 + np.sin(angle_rad) * perp2
                camera_pos = center + direction * distance + axis_direction * height
                target_pos = center + axis_direction * height
                elev, azim, roll = compute_view_angles(camera_pos, target_pos, axis_direction)
                results.append({
                    'view_type': 'lateral',
                    'elev': elev,
                    'azim': azim,
                    'roll': roll,
                    'camera_pos': camera_pos,
                    'target_pos': target_pos,
                    'lateral_angle': angle,
                    'height': height,
                    'description': f'Lateral view at {angle}° and height {height}'
                })

    return results if isinstance(results, list) and len(results) != 1 else (results if isinstance(results, list) else results[0])