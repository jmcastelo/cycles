"""
camera_view_angles
==================
Compute matplotlib Axes3D camera parameters (elev, azim, roll) so that
the camera looks *toward* the origin from a position defined by:

  • axis   – a 3-D direction vector (e.g. the axis of a cylinder)
  • angle  – azimuthal angle (rad) that rotates the camera *around* that axis
  • height – signed scalar: positive moves the camera in the +axis direction
              (upward for a vertical cylinder), negative moves it opposite.
              When height = 0 the camera sits in the plane perpendicular to axis.

The camera is always placed at unit distance from the origin (direction only),
so `height` and the radial component are used only for direction, not distance.

Returned angles plug directly into::

    ax.view_init(elev=elev, azim=azim, roll=roll)

Geometry
--------
1.  Build a right-handed frame {e_r, e_t, e_axis} around `axis`:
      e_axis = normalised axis
      e_r    = a radial direction perpendicular to e_axis
      e_t    = e_axis × e_r   (tangential, completes the frame)

2.  Camera position (direction vector from origin to camera):
      p = cos(height_angle) * [cos(angle)*e_r + sin(angle)*e_t]
        + sin(height_angle) * e_axis
    where height_angle = arctan2(height, 1) so height=0 → equatorial,
    height→±∞ → polar caps.

3.  The viewing direction is  d = -p  (camera looks toward origin).

4.  The "up" hint is e_axis (we want the cylinder axis to appear vertical
    in the image). Project it onto the image plane (perpendicular to d)
    to get the true up vector u_perp, then compute roll as the angle
    between the world-Z-projected-onto-image-plane and u_perp.

5.  Convert p to matplotlib's spherical convention:
      elev = arcsin(p_z)           [elevation above world XY plane]
      azim = arctan2(p_y, p_x)     [angle in world XY plane from X axis]
      roll = angle of u_perp in the image plane relative to the
             image-plane projection of world Z.
"""

import numpy as np


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _normalise(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError(f"Zero or near-zero vector: {v}")
    return v / n


def _perp_basis(e_axis: np.ndarray):
    """Return two unit vectors (e_r, e_t) perpendicular to e_axis."""
    # Pick a seed vector not parallel to e_axis
    seed = np.array([1.0, 0.0, 0.0])
    if abs(np.dot(seed, e_axis)) > 0.9:
        seed = np.array([0.0, 1.0, 0.0])
    e_r = _normalise(seed - np.dot(seed, e_axis) * e_axis)
    e_t = np.cross(e_axis, e_r)          # already unit length
    return e_r, e_t


# ---------------------------------------------------------------------------
# main function
# ---------------------------------------------------------------------------

def camera_view_angles(
    axis,
    angle: float,
    height: float,
    degrees: bool = False,
) -> tuple[float, float, float]:
    """
    Compute matplotlib camera angles for a view relative to an axis.

    Parameters
    ----------
    axis : array-like, shape (3,)
        Direction of the reference axis (e.g. cylinder axis). Need not be
        a unit vector – it is normalised internally.
    angle : float
        Azimuthal angle *around* the axis, in radians (or degrees if
        ``degrees=True``). angle=0 places the camera along the first
        perpendicular basis vector; angle=π/2 along the second.
    height : float
        Controls how far "above" or "below" the equatorial plane the camera
        is, measured in the same units as the radial distance (which is 1).
        Concretely, height_angle = arctan2(height, 1), so:
          height =  0  → equatorial (side) view
          height =  1  → 45° above the equator
          height → +∞  → top view (along +axis)
          height → −∞  → bottom view (along −axis)
    degrees : bool
        If True, ``angle`` is interpreted as degrees and all returned
        angles are in degrees.  Default False (radians in, degrees out
        is matplotlib's convention – see note below).

    Returns
    -------
    elev : float  – elevation above the world XY plane (degrees)
    azim : float  – azimuth in the world XY plane from X axis (degrees)
    roll : float  – camera roll so that the axis appears vertical (degrees)

    Note
    ----
    Matplotlib's ``view_init`` always expects *degrees*, so this function
    always returns degrees regardless of ``degrees``.
    """
    axis = np.asarray(axis, dtype=float)
    if axis.shape != (3,):
        raise ValueError("axis must be a 3-element vector")

    if degrees:
        angle = np.radians(angle)

    e_axis = _normalise(axis)
    e_r, e_t = _perp_basis(e_axis)

    # --- camera position direction -----------------------------------------
    # height_angle: elevation angle of camera above the equatorial plane
    height_angle = np.arctan2(height, 1.0)          # ∈ (-π/2, π/2)

    cos_h = np.cos(height_angle)
    sin_h = np.sin(height_angle)

    # radial direction at azimuthal angle `angle` around the axis
    e_radial = np.cos(angle) * e_r + np.sin(angle) * e_t

    cam_pos = cos_h * e_radial + sin_h * e_axis     # unit vector

    # --- matplotlib spherical angles from cam_pos -------------------------
    # elev: angle above the world XY plane
    elev = np.degrees(np.arcsin(np.clip(cam_pos[2], -1.0, 1.0)))
    # azim: angle in world XY plane (from +X toward +Y)
    azim = np.degrees(np.arctan2(cam_pos[1], cam_pos[0]))

    # --- roll: keep e_axis "up" in the image plane ------------------------
    # Viewing direction (from camera toward origin)
    d = -cam_pos                                    # unit vector

    # Project e_axis onto the image plane (plane ⊥ to d)
    up_hint = e_axis - np.dot(e_axis, d) * d
    norm_up = np.linalg.norm(up_hint)

    if norm_up < 1e-9:
        # Camera is looking exactly along ±axis → axis has no projection;
        # use e_r as the "up" hint instead (axis appears as a dot anyway)
        up_hint = e_r - np.dot(e_r, d) * d
        norm_up = np.linalg.norm(up_hint)

    up_hint = up_hint / norm_up                     # image-plane "up"

    # Matplotlib's default "up" in the image plane: projection of world +Z
    world_z = np.array([0.0, 0.0, 1.0])
    default_up = world_z - np.dot(world_z, d) * d
    norm_def = np.linalg.norm(default_up)

    if norm_def < 1e-9:
        # Looking straight up or down along world Z: use world X as reference
        world_x = np.array([1.0, 0.0, 0.0])
        default_up = world_x - np.dot(world_x, d) * d
        norm_def = np.linalg.norm(default_up)

    default_up = default_up / norm_def

    # Roll is the signed angle from default_up to up_hint in the image plane
    cos_roll = np.clip(np.dot(default_up, up_hint), -1.0, 1.0)
    cross = np.cross(default_up, up_hint)
    sin_roll = np.dot(cross, d)                     # signed via viewing dir
    roll = np.degrees(np.arctan2(sin_roll, cos_roll))

    return elev, azim, roll


# ---------------------------------------------------------------------------
# convenience wrappers for the three canonical views
# ---------------------------------------------------------------------------

def top_view(axis=(0, 0, 1)):
    """Look along +axis (top view)."""
    return camera_view_angles(axis, angle=0.0, height=1e6)


def bottom_view(axis=(0, 0, 1)):
    """Look along −axis (bottom view)."""
    return camera_view_angles(axis, angle=0.0, height=-1e6)


def side_view(axis=(0, 0, 1), angle=0.0, degrees=False):
    """Look perpendicularly to axis at azimuthal angle `angle`."""
    return camera_view_angles(axis, angle=angle, height=0.0, degrees=degrees)


# ---------------------------------------------------------------------------
# demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    rng = np.random.default_rng(42)

    # Generate points on/around a tilted cylinder
    AXIS = np.array([1.0, 1.0, 2.0])           # tilted cylinder axis
    n_pts = 300
    t = rng.uniform(0, 2 * np.pi, n_pts)
    z = rng.uniform(-1, 1, n_pts)

    # Build cylinder points in local frame then rotate to world frame
    e_axis = AXIS / np.linalg.norm(AXIS)
    seed = np.array([1, 0, 0]) if abs(e_axis[0]) < 0.9 else np.array([0, 1, 0])
    e_r = np.cross(e_axis, seed); e_r /= np.linalg.norm(e_r)
    e_t = np.cross(e_axis, e_r)

    pts = (np.cos(t)[:, None] * e_r +
           np.sin(t)[:, None] * e_t +
           z[:, None] * e_axis +
           rng.normal(0, 0.05, (n_pts, 3)))

    # Define views
    views = [
        ("Top view",    top_view(AXIS)),
        ("Bottom view", bottom_view(AXIS)),
        ("Side 0°",     side_view(AXIS, angle=0.0)),
        ("Side 90°",    side_view(AXIS, angle=np.pi / 2)),
        ("Side 180°",   side_view(AXIS, angle=np.pi)),
        ("Oblique 45°", camera_view_angles(AXIS, angle=np.pi / 4, height=0.8)),
    ]

    fig = plt.figure(figsize=(15, 8))
    for idx, (title, (elev, azim, roll)) in enumerate(views, 1):
        ax = fig.add_subplot(2, 3, idx, projection="3d")
        ax.scatter(*pts.T, s=4, alpha=0.5)
        # draw the axis
        for s in (-1, 1):
            ax.quiver(0, 0, 0, *(s * e_axis), length=1.2,
                      color="red", linewidth=1.5, arrow_length_ratio=0.1)
        ax.view_init(elev=elev, azim=azim, roll=roll)
        ax.set_title(f"{title}\nelev={elev:.1f}° azim={azim:.1f}° roll={roll:.1f}°",
                     fontsize=8)
        ax.set_xlabel("X"); ax.set_ylabel("Y"); ax.set_zlabel("Z")

    plt.tight_layout()
    plt.savefig("/mnt/user-data/outputs/camera_view_demo.png", dpi=150, bbox_inches="tight")
    print("Saved demo to camera_view_demo.png")
    plt.show()
