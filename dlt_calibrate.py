#lets calibrate

import argparse
from pathlib import Path
import tkinter as tk
from tkinter import filedialog

import numpy as np

import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from matplotlib.widgets import Button

from dlt_math import (load_object_points, 
	compute_dlt, 
	compute_modified_dlt, 
	project_points
	)

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

	plt.subplots_adjust(bottom=0.18)

	zoom_ax = fig.add_axes([
		0.77,
		0.70,
		0.20,
		0.22])

	zoom_ax.set_title(
		"Magnified view",
		fontsize=9)

	zoom_ax.set_xticks([])
	zoom_ax.set_yticks([])

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
	finished = False

	calibration_result = {
		"standard_coefficients":None,
		"standard_rmse":None,
		"modified_coefficients":None,
		"modified_rmse":None
		}

	point_markers = [None] * len(object_points)
	point_labels = [None] * len(object_points)

	status_text = fig.text(
		0.05,
		0.08,
		"",
		fontsize=11
		)

	def update_status():
		if current_point<len(object_points):
			X,Y,Z = object_points[current_point]

			status_text.set_text(
				f"Current point: {current_point+1} / {len(object_points)}"
				f' XYZ: [{X:.2f}, {Y:.2f} ,{Z:.2f}]'
				)

		else:
			status_text.set_text(
				"All calibration markers have been clicked."
				)

		fig.canvas.draw_idle()

	update_status()


	#zoom view // magnified box
	def on_move(event):
		if event.inaxes != ax:
			return

		u = event.xdata
		v = event.ydata

		if u is None or v is None:
			return

		half_width = 15

		x_min = int(max(0, u-half_width))
		x_max = int(min(image.shape[1], u+half_width))

		y_min = int(max(0,v-half_width))
		y_max = int(min(image.shape[0], v+half_width))

		crop = image[
			y_min:y_max,
			x_min:x_max
			]

		if crop.size == 0:
			return

		zoom_ax.clear()

		zoom_ax.imshow(
			crop,
			interpolation="nearest"
			)

		#cursor location inside the cropped iamage
		cursor_x = u-x_min
		cursor_y = v-y_min

		#crosshair on magnified view
		zoom_ax.axvline(
			cursor_x,
			color='red',
			linewidth=1.0
			)

		zoom_ax.axhline(
			cursor_y,
			linewidth=0.8
			)

		#small center marker
		zoom_ax.plot(
			cursor_x,
			cursor_y,
			marker='+',
			color='red',
			markersize=10,
			markeredgewidth=1.2
			)

		zoom_ax.set_title(
			f"u={u:.1f},v={v:.1f}",
			fontsize=9
			)

		zoom_ax.set_xticks([])
		zoom_ax.set_yticks([])

		fig.canvas.draw_idle()


	#mouse click
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


		#auto-advance
		if current_point<len(object_points) - 1:
			current_point+=1

		else:
			current_point+=1
			print("All calibration markers have been clicked!")

		update_status()


	#previous point logic
	def previous_point(event=None):
		nonlocal current_point

		current_point = max(
			0,
			current_point-1
			)

		update_status()

	#next point
	def next_point(event=None):
		nonlocal current_point

		current_point=min(
			len(object_points)-1,
			current_point+1
			)

		update_status()

	#finish calibration
	def finish_calibration(event=None):
		nonlocal finished

		if finished:
			return
		finished=True

		print("\nComputing calibration...")

		standard_coefficients, standard_rmse=compute_dlt(
			object_points,
			image_points
			)

		modified_coefficients,modified_rmse=compute_modified_dlt(
			object_points,
			image_points
			)

		calibration_result["standard_coefficients"]=standard_coefficients
		calibration_result['standard_rmse']=standard_rmse
		calibration_result['modified_coefficients']=modified_coefficients
		calibration_result['modified_rmse']=modified_rmse

		status_text.set_text(
			f"Calibration complete | "
			f"Standard RMSE: {standard_rmse:.3f} px |"
			f"Modified RMSE: {modified_rmse:.3f} px"
			)

		fig.canvas.draw_idle()

		print(
			f"\nStandard DLT residual: {standard_rmse:.3f} pixels"
			)


	#keyboard control
	def on_key(event):
		if event.key == "left":
			previous_point()

		elif event.key == "right":
			next_point()

		elif event.key == "enter":
			finish_calibration()


	#buttons
	previous_ax = fig.add_axes([
		0.55,
		0.045,
		0.10,
		0.055
		])

	next_ax = fig.add_axes([
		0.66,
		0.045,
		0.10,
		0.055
		])

	finish_ax = fig.add_axes([
		0.78,
		0.045,
		0.17,
		0.055
		])

	previous_button = Button(
		previous_ax,
		"Previous"
		)

	next_button = Button(
		next_ax,
		"Next"
		)

	finish_button = Button(
		finish_ax,
		"Finish / Complete"
		)

	previous_button.on_clicked(previous_point)
	next_button.on_clicked(next_point)
	finish_button.on_clicked(finish_calibration)

	#connect events

	fig.canvas.mpl_connect(
		"button_press_event",
		on_click
		)

	fig.canvas.mpl_connect(
		"key_press_event",
		on_key)

	fig.canvas.mpl_connect(
		"motion_notify_event",
		on_move)

	plt.show()

	return image_points, calibration_result

def save_calibration_results(
		output_dir,
		camera_number,
		object_points,
		image_points,
		coefficients,
		rmse):

	output_dir.mkdir(parents=True, exist_ok=True)

	coefficients_file = output_dir / f"{camera_number}_dlt_coefficients.csv"
	points_file = output_dir / f"{camera_number}_clicked_points.csv"

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
	
def save_combined_coefficients(
	camera_results,
	output_dir):

	output_dir.mkdir(
		parents=True,
		exist_ok=True
		)

	coefficient_matrix=np.column_stack([
		result["modified_coefficients"]
		for result in camera_results
		])

	header = ",".join([
		f"camera_{result['camera_number']}"
		for result in camera_results
		])

	output_file = (
		output_dir / 
		"dlt_coefficients_all_cameras.csv"
		)

	np.savetxt(
		output_file,
		coefficient_matrix,
		delimiter=",",
		header=header,
		comments="",
		fmt="%.12g"
		)

	print(
		"\nCombined DLT coefficients saved:"
		)

	print(output_file)


def save_sanity_check_image(
	image_path,
	output_dir,
	camera_number,
	object_points,
	image_points,
	coefficients):
	
	image = mpimg.imread(image_path)

	reprojected_points = project_points(
		coefficients,
		object_points)

	output_file = (
		output_dir / 
		f"camera_{camera_number}_sanity_check.png")

	fig,ax = plt.subplots(figsize=(14,8))

	ax.imshow(image)
	ax.set_title(
		f"Camera {camera_number} sanity check",
		fontsize=12)
	ax.axis("off")

	#add the clicked points 
	ax.scatter(
		image_points[:,0],
		image_points[:,1],
		s=110,
		marker='o',
		facecolors="none",
		edgecolors='red',
		linewidths=1.8,
		zorder=3,
		label="Clicked points")

	#reprojected points 
	ax.scatter(
		reprojected_points[:,0],
		reprojected_points[:,1],
		s=55,
		marker="+",
		c="blue",
		linewidths=1.8,
		zorder=4,
		label="Reprojected points")

	#point numbers
	for i in range(len(object_points)):
		u=image_points[i,0]
		v=image_points[i,1]

		ax.text(
			u+5,
			v+5,
			str(i+1),
			color="white",
			fontsize=9)

	ax.legend(loc="upper right")

	plt.tight_layout()
	plt.savefig(
		output_file,
		dpi=200,
		bbox_inches="tight"
		)

	plt.close(fig)

	print("\nSanity check image save:")
	print(output_file)


def main():
	args=parse_args()

	if args.csv is None:
		object_file = DEFAULT_OBJECT_FILE
	else:
		object_file = args.csv

	object_points = load_object_points(object_file)

	#empty list for camera results
	camera_results = []

	#iterable value for which we're on
	camera_number = 1

	while True:
		print("DLT Camera Calibration")
		print(f"Calibration object: {object_file}")
		print(f"Loaded {len(object_points)}")
		print(f"\n --- CAMERA {camera_number} ---")

		image_path = choose_calibration_image()
		print(f"Calibration image: {image_path}")

		output_dir = image_path.parent

		image_points,calibration_result = show_calibration_image(
			image_path,
			object_points
			)


		standard_coefficients = calibration_result['standard_coefficients']
		standard_rmse = calibration_result['standard_rmse']

		modified_coefficients = calibration_result['modified_coefficients']
		modified_rmse = calibration_result['modified_rmse']

		camera_results.append({
			"camera_number":camera_number,
			"image_path": image_path,
			"image_points":image_points,
			"standard_coefficients":standard_coefficients,
			"standard_rmse":standard_rmse,
			"modified_coefficients":modified_coefficients,
			"modified_rmse":modified_rmse
			})


		save_calibration_results(
			output_dir = output_dir,
			camera_number = camera_number,
			object_points = object_points,
			image_points = image_points,
			coefficients = modified_coefficients,
			rmse = modified_rmse)

		save_sanity_check_image(
			image_path = image_path,
			output_dir=output_dir,
			camera_number=camera_number,
			object_points=object_points,
			image_points=image_points,
			coefficients=modified_coefficients)

		print("\nSTANDARD 11-PARAMETER DLT")
		print(f"Residual: {standard_rmse:.3f} pixels")
		print("Coefficients:")
		print(standard_coefficients)

		print("\nMODIFIED 11-PARAMETER DLT")
		print(f"Residual: {modified_rmse:.3f} pixels")
		print("Coefficients:")
		print(modified_coefficients)

		response=input(
			"\nAdd another camera? [Y/N]: "
			).strip().lower()

		if response!='y':
			break

		camera_number+=1

	print(f"\nCalibration complete: "
		f"{len(camera_results)} camera(s) calibrated."
		)

	combined_output_dir = camera_results[0]["image_path"].parents[2]

	save_combined_coefficients(
		camera_results,
		combined_output_dir
		)

if __name__ == '__main__':
		main()













