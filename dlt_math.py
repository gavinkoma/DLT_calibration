#base file for dlt math

import numpy as np
from scipy.optimize import minimize

def compute_dlt(object_points, image_points):
	"""
	compute regular standard 11-parameter dlt coeffs, no geometric constraint
	(modified 11-parameter)

	object_points:
		Nx3 array of known x,y,z coordinates

	image_points:
		Nx2 array of clicked u,v pixel coordinates
	"""

	#ensure working with floats
	object_points = np.asarray(object_points,dtype=float)
	image_points = np.asarray(image_points,dtype=float)

	#logic check, doublecheck shapes
	if object_points.ndim != 2 or object_points.shape[1] != 3:
		raise ValueError("object_points must have shape (N,3)")

	if image_points.ndim != 2 or image_points.shape[1] != 2:
		raise ValueError("image_points must have shape (N,2)")

	if len(object_points) != len(image_points):
		raise ValueError(
			"object_points & image_points must contain the same number of points"
			)

	#its possible some of the points wont always be visible so lets just handle that
	#doing this by creating a boolean mask for filtering, ~flips values
	valid_rows = (
		~np.isnan(object_points).any(axis=1)
		& ~np.isnan(image_points).any(axis=1)
		)

	object_points = object_points[valid_rows]
	image_points = image_points[valid_rows]

	if len(object_points) < 6:
		raise ValueError(
			"at least 6 valid calibration points are required for an 11 parameter DLT"
			)

	X = object_points[:,0]
	Y = object_points[:,1]
	Z = object_points[:,2]

	u = image_points[:,0]
	v = image_points[:,1]

	n = len(object_points)
	M = np.zeros((2*n, 11))

	for i in range(n):
		#equation for u
		M[2*i,0:3] = object_points[i]
		M[2*i,3] = 1
		M[2*i,8:11] = -u[i]*object_points[i]

		#equation for v
		M[2*i+1,4:7]=object_points[i]
		M[2*i+1,7]=1
		M[2*i+1,8:11] = -v[i]*object_points[i]

		'''
		~visualizaiton of above matrix definitions~
		columns:
		 0  1  2  3   4  5  6  7    8     9     10

		u row:
		 X  Y  Z  1   0  0  0  0   -uX   -uY   -uZ

		v row:
		 0  0  0  0   X  Y  Z  1   -vX   -vY   -vZ
		
		'''

	b = image_points.reshape(-1) #turns to vertical column vector

	coefficients, residuals, rank, singular_values = np.linalg.lstsq(
		M,
		b,
		rcond=None
		)

	rmse = reprojection_rmse(
		coefficients,
		object_points,
		image_points
		)

	return coefficients, rmse

def build_modified_coefficients(params):
    """
    build the full 11 modified-DLT coefficients from
    the 10 independently optimized parameters C2-C11.
    """

    params = np.asarray(params, dtype=float)

    if params.shape != (10,):
        raise ValueError("Modified DLT requires 10 parameters (C2 through C11)")

    C = np.zeros(11)

    #params contains MATLAB C2-C11
    C[1:11] = params

    #compute C1 from the modified-DLT nonlinear constraint
    C[0] = (
        -C[1] * C[5] * C[8]**2
        -C[1] * C[5] * C[10]**2
        -C[2] * C[6] * C[8]**2
        -C[2] * C[6] * C[9]**2
        +C[1] * C[9] * C[4] * C[8]
        +C[1] * C[9] * C[6] * C[10]
        +C[2] * C[10] * C[4] * C[8]
        +C[2] * C[10] * C[5] * C[9]
    ) / (
        C[4] * C[9]**2
        +C[4] * C[10]**2
        -C[8] * C[5] * C[9]
        -C[8] * C[6] * C[10]
    )

    return C


def modified_dlt_score(params, object_points, image_points):
    """
    reconstruct the full 11 modified-DLT coefficients from
    the 10 optimized parameters, then return reprojection RMSE.
    """

    C = build_modified_coefficients(params)

    return reprojection_rmse(
		C,
		object_points,
		image_points
		)

def compute_modified_dlt(object_points, image_points):

	#ensure working with floats
	object_points = np.asarray(object_points,dtype=float)
	image_points = np.asarray(image_points,dtype=float)
	valid_rows = (
		~np.isnan(object_points).any(axis=1)
		& ~np.isnan(image_points).any(axis=1)
		)

	object_points = object_points[valid_rows]
	image_points = image_points[valid_rows]


    standard_coefficients, _ = compute_dlt(
        object_points,
        image_points
  		)

    initial_guess = standard_coefficients[1:11]

    result = minimize(
        modified_dlt_score,
        initial_guess,
        args=(object_points, image_points),
        method="Nelder-Mead"
    )

    if not result.success:
        raise RuntimeError(
            f"Modified DLT optimization failed: {result.message}"
        )

    coefficients = build_modified_coefficients(result.x)

    rmse = reprojection_rmse(
    	coefficients,
    	object_points,
    	image_points
    	)

    return coefficients, rmse

def project_points(coefficients, object_points):
    """
    project known 3D object points into 2D image coordinates
    using 11-parameter DLT coefficients

    coefficients : np.ndarray
        Length-11 array of DLT coefficients.

    object_points : np.ndarray
        Nx3 array of X, Y, Z coordinates.

    projected_points : np.ndarray
        Nx2 array of predicted u, v image coordinates.
    """

    coefficients = np.asarray(coefficients, dtype=float)
    object_points = np.asarray(object_points, dtype=float)

    if coefficients.shape != (11,):
        raise ValueError("coefficients must contain exactly 11 values")

    if object_points.ndim != 2 or object_points.shape[1] != 3:
        raise ValueError("object_points must have shape (N, 3)")

    X = object_points[:, 0]
    Y = object_points[:, 1]
    Z = object_points[:, 2]

    L = coefficients

    denominator = (
        L[8] * X
        + L[9] * Y
        + L[10] * Z
        + 1
    )

    u = (
        L[0] * X
        + L[1] * Y
        + L[2] * Z
        + L[3]
    ) / denominator

    v = (
        L[4] * X
        + L[5] * Y
        + L[6] * Z
        + L[7]
    ) / denominator

    projected_points = np.column_stack((u, v))

    return projected_points

def reprojection_rmse(coefficients, object_points, image_points):
    """
    Compute image-space reprojection RMSE in pixels.
    """

    projected_points = project_points(
        coefficients,
        object_points
    )

    difference = projected_points - image_points

    rmse = np.sqrt(
        np.mean(difference ** 2)
    )

    return rmse

def load_object_points(filename):
	return np.loadtxt(
		filename,
		delimiter=',',
		skiprows=1
		)

object_points = load_object_points("obj_positions.csv")













