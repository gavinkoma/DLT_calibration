#base file for dlt math


import numpy as np

def compute_dlt(object_points, image_points):
	"""
	compute regular standard 11-parameter dlt coeffs, no geometric constraint
	(modified 11-parameter)

	object_points:
		Nx3 array of known x,y,z coordinates

	image_points:
		Nx2 array of clicked u,v pixel coordinates
	"""

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
		M[2i+1,7]=1
		M[2*i+1,8:11] = -u[i]*object_points[i]

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



















