#lets calibrate

import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import numpy as np

import matplotlib.pyplot as plt
import matplotlib.image as mpimg

from dlt_math import load_object_points, compute_dlt, compute_modified_dlt

DEFAULT_OBJECT_FILE = Path(__file__).with_name("obj_positions.csv")

def parse_args():
	parser = argparse.ArgumentParser(
		description="DLT camera calibration"
		)

	parser.add_argument(
		"--csv",
		type=Path,
		default=None,
		help="Override the default calibration-object CSV"
		)

	return parser.parse_args()

def choose_calibration_image():
	root = tk.Tk()
	root.withdraw()

	image_path = filedialog.askopenfilename(
		title="Select calibration image",
		filetypes=[
			("Image files","*.png *.jpg *.jpeg *.tif *.tiff *.bmp"),
			("All files", "*.*"),
			]
			)

	root.destroy()

	if not image_path:
		raise RuntimeError("No calibration image selected.")

	return Path(image_path)

def show_calibration_image(image_path, object_points):
	image = mpimg.imread(image_path)

	fig,ax = plt.subplots(figsize=(12,8))

	ax.imshow(image)
	ax.set_title(image_path.name)
	ax.axis("off")

	#note one row per each calibration point
	#start with nan because we havent clicked yet
	image_points = np.full(
		(len(object_points),2),
		np.nan
		)

	current_point = 0

	point_markers = [None]*len(object_points)
	point_labels = [None]*len(object_points)

	def print_current_point():
		if current_point < len(object_points):
			print()
			print(f"Current point: {current_point + 1}")
			print(
				"Object coordinate:",
				object_points[current_point]
				)

	print_current_point()

	# print()
	# print(f"Current point: {current_point+1}")
	# print("Object coordinate:",
	# 	object_points[current_point]
	# 	)

	def on_click(event):
		nonlocal current_point

		if event.inaxes != ax:
			return

		if current_point >= len(object_points):
			return

		u = event.xdata
		v = event.ydata

		image_points[current_point] = [u,v]

		point_number = current_point + 1

		print(
			f"Point {point_number}: "
			f"u={u:.2f}, v={v:.2f}"
			)

		if point_markers[current_point] is not None:
			point_markers[current_point].set_data(
				[u],
				[v]
				)

			point_labels[current_point].set_position(
				(u+3,v+3)
				)

		else:
			marker, = ax.plot(
				u,
				v,
				"ro",
				markersize=5
				)

			label = ax.text(
				u+3,
				v+3,
				str(point_number),
				color="red",
				fontsize=10
				)

			point_markers[current_point] = marker
			point_labels[current_point] = label

		fig.canvas.draw()

		if current_point<len(object_points) - 1:
			current_point+=1
			print_current_point()

		else:
			current_point+=1
			print()
			print("All calibration markers have been clicked!")

	def on_key(event):
		nonlocal current_point

		if event.key == "left":
			current_point=max(
				0,
				current_point-1
				)

			print_current_point()

		elif event.key == "right":
			current_point = min(
				len(object_points)-1,
				current_point+1
				)

			print_current_point()


	fig.canvas.mpl_connect(
		"button_press_event",
		on_click
		)

	fig.canvas.mpl_connect(
		"key_press_event",
		on_key)

	plt.show()

	return image_points

def save_calibration_results(
		output_dir,
		image_path,
		object_points,
		image_points,
		coefficients,
		rmse):

	output_dir.mkdir(parents=True, exist_ok=True)
	stem = image_path.stem

	coefficients_file = output_dir / f"{stem}_dlt_coefficients.csv"
	points_file = output_dir / f"{stem}_clicked_points.csv"

	coefficient_data = np.column_stack([
		np.arange(1,12),
		coefficients
		])

	np.savetxt(
		coefficients_file,
		coefficient_data,
		delimiter=',',
		header="coefficient,value",
		comments="",
		fmt=["%d",'%.12g']
		)

	with open(coefficients_file,"a") as f:
		f.write(f"rmse_pixels,{rmse:.12g}\n")

	point_data = np.column_stack([
		np.arange(1,len(object_points)+1),
		object_points,
		image_points
		])

	np.savetxt(
		points_file,
		point_data,
		delimiter=',',
		header="point,X,Y,Z,u,v",
		comments="",
		fmt=["%d","%.12g","%.12g","%.12g","%.12g","%.12g"])

	print("\nCalibration saved:")
	print(coefficients_file)
	print(points_file)
	


def main():
	args=parse_args()

	if args.csv is None:
		object_file = DEFAULT_OBJECT_FILE
	else:
		object_file = args.csv

	object_points = load_object_points(object_file)

	print("DLT Camera Calibration")
	print(f"Calibration object: {object_file}")
	print(f"Loaded {len(object_points)}")

	image_path = choose_calibration_image()
	print(f"Calibration image: {image_path}")

	image_points = show_calibration_image(
		image_path,
		object_points
		)

	standard_coefficients, standard_rmse = compute_dlt(
		object_points,
		image_points
		)

	modified_coefficients, modified_rmse = compute_modified_dlt(
		object_points,
		image_points
		)

	output_dir = image_path.parent / "dlt_results"

	save_calibration_results(
		output_dir = output_dir,
		image_path = image_path,
		object_points = object_points,
		image_points = image_points,
		coefficients = modified_coefficients,
		rmse = modified_rmse)

	print("\nSTANDARD 11-PARAMETER DLT")
	print(f"Residual: {standard_rmse:.3f} pixels")
	print("Coefficients:")
	print(standard_coefficients)

	print("\nMODIFIED 11-PARAMETER DLT")
	print(f"Residual: {modified_rmse:.3f} pixels")
	print("Coefficients:")
	print(modified_coefficients)

if __name__ == '__main__':
		main()













