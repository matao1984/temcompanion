from rsciio.emd import file_reader as emd_reader
from rsciio.digitalmicrograph import file_reader as dm_reader
from rsciio.tia import file_reader as tia_reader
from rsciio.tiff import file_reader as tif_reader
from rsciio.tiff import file_writer as tif_writer
from rsciio.image import file_reader as im_reader
from rsciio.mrc import file_reader as mrc_reader
from rsciio.empad import file_reader as empad_reader
from rsciio.usid import file_reader as usid_reader
from skimage.color import rgb2gray
import h5py

# from rsciio.image import file_writer as im_writer
import math
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import copy
import json
import pickle

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QDialogButtonBox,
    QMenu,
    QAction,
)

# Internal modules
from . import filters


def find_system_font():
    if os.name == "nt":  # Windows
        font_path = os.path.join(os.environ["SystemRoot"], "Fonts", "segoeui.ttf")
        if os.path.exists(font_path):
            return font_path

    elif os.name == "posix":
        if "Darwin" in os.uname().sysname:  # macOS
            font_paths = [
                "/System/Library/Fonts/SFNS.ttf",
                "/System/Library/Fonts/SFNSDisplay.ttf",
            ]
            for path in font_paths:
                if os.path.exists(path):
                    return path
        else:
            font_paths = [
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            ]

            for path in font_paths:
                if os.path.exists(path):
                    return path


def norm_img(data, vmin=None, vmax=None):
    if vmin is None:
        vmin = np.min(data)
    if vmax is None:
        vmax = np.max(data)
    # Normalize a data array
    data = data.astype("float32")  # Int32 for calculation
    norm = (data - vmin) / (vmax - vmin)
    return norm


# def hsv2rgb(hsv):
#     # Convert HSV array to RGB array
#     rgb = np.zeros(hsv.shape, dtype=np.uint8)
#     for i in range(hsv.shape[0]):
#         for j in range(hsv.shape[1]):
#             h, s, v = hsv[i, j]
#             r, g, b = hsv_to_rgb(h, s, v)
#             rgb[i, j] = (int(r * 255), int(g * 255), int(b * 255))
#     return rgb


def getDirectory(path):
    return os.path.dirname(path)


def getFileNameType(path):
    file = os.path.basename(path)
    name_ext = os.path.splitext(file)
    name = name_ext[0]
    ext = name_ext[1][1:]  # Remove the dot
    return name, ext


def apply_filter(img, filter_type, **kwargs):
    """Wrapper function to apply different filters
    img: 2D or 3D numpy array
    filter_type: 'Wiener', 'ABS', 'NL', 'BW', 'Gaussian'
    kwargs: parameters for different filters
    """
    filter_dict = {
        "Wiener": filters.wiener_filter,
        "ABS": filters.abs_filter,
        "NL": filters.nlfilter,
        "BW": filters.bw_lowpass,
        "Gaussian": filters.gaussian_lowpass,
    }
    if img.ndim == 2:
        # Apply the selected filter only on 2D array
        if filter_type in filter_dict.keys():
            result = filter_dict[filter_type](img, **kwargs)
            if filter_type in ["Wiener", "ABS", "NL"]:
                return result[0]
            elif filter_type in ["BW", "Gaussian"]:
                return result
    elif img.ndim == 3:
        # Apply to image stacks
        img_shape = img.shape
        result = np.zeros(img_shape)
        for i in range(img_shape[0]):
            result_i = apply_filter(img[i], filter_type, **kwargs)
            result[i] = result_i
        return result
    else:
        raise ValueError("Unsupported image dimensions")


def apply_filter_on_img_dict(img_dict, *args, **kwargs):
    # Take a image dictionary, apply the filter onto the data, and return the modified dictionary
    data = img_dict["data"]
    filtered_data = apply_filter(data, *args, **kwargs)
    filtered_dict = copy.deepcopy(img_dict)
    filtered_dict["data"] = filtered_data
    return filtered_dict


def save_as_tif16(
    input_file,
    f_name,
    output_dir,
    dtype="int16",
    apply_wf=False,
    apply_absf=False,
    apply_nl=False,
    apply_bw=False,
    apply_gaussian=False,
):
    img = copy.deepcopy(input_file)

    img["data"] = img["data"].astype(dtype)

    # Save unfiltered
    tif_writer(os.path.join(output_dir, f_name + ".tiff"), img)

    # Save filtered
    if apply_wf:
        img["data"] = input_file["wf"]
        save_as_tif16(img, f_name + "_WF", output_dir, dtype)

    if apply_absf:
        img["data"] = input_file["absf"]
        save_as_tif16(img, f_name + "_ABSF", output_dir, dtype)

    if apply_nl:
        img["data"] = input_file["nl"]
        save_as_tif16(img, f_name + "_NL", output_dir, dtype)

    if apply_bw:
        img["data"] = input_file["bw"]
        save_as_tif16(img, f_name + "_BW", output_dir, dtype)

    if apply_gaussian:
        img["data"] = input_file["gaussian"]
        save_as_tif16(img, f_name + "_Gaussian", output_dir, dtype)


def save_with_pil(
    input_file,
    f_name,
    output_dir,
    f_type,
    scalebar=True,
    apply_wf=False,
    apply_absf=False,
    apply_nl=False,
    apply_bw=False,
    apply_gaussian=False,
):
    im_data = norm_img(input_file["data"]) * 255
    im = Image.fromarray(im_data.astype("int16"))
    im = im.convert("L")
    if im.size[0] <= 64 or im.size[1] <= 64:
        scalebar = False  # Remove scalebar for very small images to avoid error
    if scalebar:
        # Add a scale bar
        unit = input_file["axes"][1]["units"]
        scale = input_file["axes"][1]["scale"]
        add_scalebar_to_pil(im, scale, unit)
    im.save(os.path.join(output_dir, f_name + f".{f_type}"))

    if apply_wf:
        wf = {
            "data": input_file["wf"],
            "axes": input_file["axes"],
            "metadata": input_file["metadata"],
        }
        save_with_pil(wf, f_name + "_WF", output_dir, f_type, scalebar=scalebar)

    if apply_absf:
        absf = {
            "data": input_file["absf"],
            "axes": input_file["axes"],
            "metadata": input_file["metadata"],
        }
        save_with_pil(absf, f_name + "_ABSF", output_dir, f_type, scalebar=scalebar)

    if apply_nl:
        nl = {
            "data": input_file["nl"],
            "axes": input_file["axes"],
            "metadata": input_file["metadata"],
        }
        save_with_pil(nl, f_name + "_NL", output_dir, f_type, scalebar=scalebar)

    if apply_bw:
        bw = {
            "data": input_file["bw"],
            "axes": input_file["axes"],
            "metadata": input_file["metadata"],
        }
        save_with_pil(bw, f_name + "_BW", output_dir, f_type, scalebar=scalebar)

    if apply_gaussian:
        gaussian = {
            "data": input_file["gaussian"],
            "axes": input_file["axes"],
            "metadata": input_file["metadata"],
        }
        save_with_pil(
            gaussian, f_name + "_Gaussian", output_dir, f_type, scalebar=scalebar
        )


def save_as_gif(data, file_path, duration=500, loop=0, label=None):
    # Save a 3D numpy array as a GIF animation
    frames = []
    default_font = find_system_font()
    z, y, x = data.shape

    for i in range(z):
        im_data = norm_img(data[i]) * 255
        im = Image.fromarray(im_data.astype("int16"))
        im = im.convert("RGB")

        if label is not None:
            draw = ImageDraw.Draw(im)
            fn = i + 1  # noqa: F841
            text = label  # Label accepts fn for frame number and {} for expression
            if "fn" in label and "{" in label and "}" in label:
                text = eval(
                    f'f"{label}"'
                )  # Evaluate the label as an f-string to replace fn and expressions
            text_x = int(x / 50)
            text_y = int(y / 50)
            font_size = max(int(x / 30), 12)  # Limit the font size down to 12
            draw.text(
                (text_x, text_y),
                text,
                font=ImageFont.truetype(default_font, font_size),
                fill="yellow",
            )
        frames.append(im)

    frames[0].save(
        file_path, save_all=True, append_images=frames[1:], duration=duration, loop=loop
    )


def add_scalebar_to_pil(im, scale, unit):
    """Add a scalebar to a PIL image"""
    # Handle micrometer sign
    if unit in ["µm", "um"]:
        unit = "\u03bc" + "m"  # Normal \mu letter
    im_x, im_y = im.size
    fov_x = im_x * scale
    # Find a good integer length for the scalebar
    sb_len_float = fov_x / 6  # Scalebar length is about 1/6 of FOV
    # A list of allowed lengths for the scalebar
    sb_lst = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000, 5000]
    # Find the closest value in the list
    sb_len = sorted(sb_lst, key=lambda a: abs(a - sb_len_float))[0]
    sb_len_px = sb_len / scale
    sb_start_x, sb_start_y = (
        im_x / 12,
        im_y * 11 / 12,
    )  # Bottom left corner from 1/12 of FOV
    draw = ImageDraw.Draw(im)
    sb = (sb_start_x, sb_start_y, sb_start_x + sb_len_px, sb_start_y + im_y / 80)
    outline_width = round(im_y / 300)
    if outline_width == 0:
        outline_width = 1
    draw.rectangle(sb, fill="white", outline="black", width=outline_width)
    # Add text
    if unit is None:
        unit = "px"
    text = str(sb_len) + " " + unit
    fontsize = int(im_x / 20)
    # Choose a good font according to the os
    default_font = find_system_font()
    if default_font:
        font = ImageFont.truetype(default_font, fontsize)
    else:
        font = ImageFont.load_default(fontsize)

    txt_x, txt_y = (sb_start_x * 1.1, sb_start_y - fontsize * 1.1 - im_y / 80)
    # Add outline to the text
    dx = im_x / 800
    draw.text((txt_x - dx, txt_y - dx), text, font=font, fill="black")
    draw.text((txt_x + dx, txt_y - dx), text, font=font, fill="black")
    draw.text((txt_x - dx, txt_y + dx), text, font=font, fill="black")
    draw.text((txt_x + dx, txt_y + dx), text, font=font, fill="black")
    draw.text((txt_x, txt_y), text, font=font, fill="white", anchor=None)


def save_file_as(input_file, f_name, output_dir, f_type, **kwargs):
    apply_wf = kwargs["apply_wf"]
    delta_wf = kwargs["delta_wf"]
    order_wf = kwargs["order_wf"]
    cutoff_wf = kwargs["cutoff_wf"]
    apply_absf = kwargs["apply_absf"]
    delta_absf = kwargs["delta_absf"]
    order_absf = kwargs["order_absf"]
    cutoff_absf = kwargs["cutoff_absf"]
    apply_nl = kwargs["apply_nl"]
    delta_nl = kwargs["delta_nl"]
    order_nl = kwargs["order_nl"]
    cutoff_nl = kwargs["cutoff_nl"]
    N = kwargs["N"]
    apply_bw = kwargs["apply_bw"]
    order_bw = kwargs["order_bw"]
    cutoff_bw = kwargs["cutoff_bw"]
    apply_gaussian = kwargs["apply_gaussian"]
    cutoff_gaussian = kwargs["cutoff_gaussian"]
    scale_bar = kwargs["scalebar"]
    # Save images

    # Check if the output_dir exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    if apply_wf:
        print(f"Applying Wiener filter to {f_name}...")
        input_file["wf"] = apply_filter(
            input_file["data"],
            "Wiener",
            delta=delta_wf,
            lowpass_order=order_wf,
            lowpass_cutoff=cutoff_wf,
        )

    if apply_absf:
        print(f"Applying ABS filter to {f_name}...")
        input_file["absf"] = apply_filter(
            input_file["data"],
            "ABS",
            delta=delta_absf,
            lowpass_order=order_absf,
            lowpass_cutoff=cutoff_absf,
        )

    if apply_nl:
        print(f"Applying Non-Linear filter to {f_name}...")
        input_file["nl"] = apply_filter(
            input_file["data"],
            "NL",
            N=N,
            delta=delta_nl,
            lowpass_order=order_nl,
            lowpass_cutoff=cutoff_nl,
        )
    if apply_bw:
        print(f"Applying Butterworth low-pass filter to {f_name}...")
        input_file["bw"] = apply_filter(
            input_file["data"], "BW", order=order_bw, cutoff_ratio=cutoff_bw
        )

    if apply_gaussian:
        print(f"Applying Gaussian low-pass filter to {f_name}...")
        input_file["gaussian"] = apply_filter(
            input_file["data"], "Gaussian", cutoff_ratio=cutoff_gaussian
        )
    if f_type == "tiff":
        # For tiff format, save directly as 16-bit with calibration, no scalebar
        # No manipulation of data but just set to int16
        if np.all(input_file["data"] % 1 == 0):
            dtype = "int16"  # All integer values set to int16
        else:
            dtype = "float32"  # Float values set to float32
        save_as_tif16(
            input_file,
            f_name,
            output_dir,
            dtype=dtype,
            apply_wf=apply_wf,
            apply_absf=apply_absf,
            apply_nl=apply_nl,
            apply_bw=apply_bw,
            apply_gaussian=apply_gaussian,
        )

    else:
        if f_type == "tiff + png":
            if np.all(input_file["data"] % 1 == 0):
                dtype = "int16"  # All integer values set to int16
            else:
                dtype = "float32"  # Float values set to float32
            save_as_tif16(
                input_file,
                f_name,
                output_dir,
                dtype=dtype,
                apply_wf=apply_wf,
                apply_absf=apply_absf,
                apply_nl=apply_nl,
                apply_bw=apply_bw,
                apply_gaussian=apply_gaussian,
            )
            f_type = "png"

        save_with_pil(
            input_file,
            f_name,
            output_dir,
            f_type,
            scalebar=scale_bar,
            apply_wf=apply_wf,
            apply_absf=apply_absf,
            apply_nl=apply_nl,
            apply_bw=apply_bw,
            apply_gaussian=apply_gaussian,
        )


def load_file(file, file_type):
    # file: full path of the file
    # file_type: selected file type from the dialog
    # Load emd file:
    if file_type == "Velox emd Files (*.emd)":
        f = emd_reader(file, select_type="images")

    # Load dm file:
    elif file_type == "DigitalMicrograph Files (*.dm3 *.dm4)":
        f = dm_reader(file)

    # Load TIA file
    elif file_type == "TIA ser Files (*.ser)":
        f = tia_reader(file)

    # Load tif formats
    elif file_type == "Tiff Files (*.tif *.tiff)":
        try:
            f = tif_reader(file)
            # Add RGB to grayscale conversion for TIFF files too
            for img in f:
                # Check if the data is RGB/RGBA
                if img["data"].dtype.names is not None:  # Structured array (RGB/RGBA)
                    # Convert structured RGB array to regular 3D array
                    if (
                        "R" in img["data"].dtype.names
                        and "G" in img["data"].dtype.names
                        and "B" in img["data"].dtype.names
                    ):
                        rgb_array = np.stack(
                            [img["data"]["R"], img["data"]["G"], img["data"]["B"]],
                            axis=-1,
                        )
                        img["data"] = rgb2gray(rgb_array)
                elif img["data"].ndim == 3 and img["data"].shape[2] in [
                    3,
                    4,
                ]:  # Regular RGB/RGBA array
                    img["data"] = rgb2gray(img["data"])

        except Exception as e:  # Error, fall back to image format
            print(f"Error loading TIFF file: {e}. Try loading as image format.")
            # f = im_reader(file)
            file_type = "Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp)"
            f = load_file(file, file_type)

    # Load MRC TIFF stack
    elif file_type == "MRC Files (*.mrc)":
        f = mrc_reader(file)

    # Load image formats
    elif file_type == "Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp)":
        f = im_reader(file)
        for img in f:
            # If RGB or RGBA image, convert to grayscale
            if img["data"].dtype.names is not None:  # Structured array (RGB/RGBA)
                # Convert structured RGB array to regular 3D array
                if (
                    "R" in img["data"].dtype.names
                    and "G" in img["data"].dtype.names
                    and "B" in img["data"].dtype.names
                ):
                    rgb_array = np.stack(
                        [img["data"]["R"], img["data"]["G"], img["data"]["B"]], axis=-1
                    )
                    img["data"] = rgb2gray(rgb_array)

            elif img["data"].ndim == 3 and img["data"].shape[2] in [
                3,
                4,
            ]:  # Regular RGB/RGBA array
                img["data"] = rgb2gray(img["data"])

    # Load pickle dictionary
    elif file_type == "Pickle Dictionary Files (*.pkl)":
        with open(file, "rb") as file:
            f = []
            f.append(pickle.load(file))

    # USID
    elif file_type == "USID (*.h5 *.hdf5)":
        f = usid_reader(file)

    # NPY
    elif file_type == "Numpy Array Files (*.npy)":
        data = np.load(file)
        if data.ndim != 2 and data.ndim != 3:
            print(
                "Unsupported data dimensions in NPY file! Only 2D or 3D arrays are supported."
            )
            return
        metadata = {
            "General": {
                "original_filename": os.path.basename(file),
                "title": getFileNameType(file)[0],
            },
            "Signal": {"signal_type": "image"},
        }
        original_metadata = {}
        axes = [None] * data.ndim
        for i in range(data.ndim):
            axes[i] = {
                "size": data.shape[i],
                "index_in_array": i,
                "name": f"axis_{i}",
                "scale": 1,
                "offset": 0.0,
                "units": None,
                "navigate": False,
            }
        img_dict = {
            "data": data,
            "metadata": metadata,
            "original_metadata": original_metadata,
            "axes": axes,
        }
        f = [img_dict]

    # Load image series from a folder
    # Will load all the files whose type matches the selected one found in the folder and stack them together
    elif file_type == "Image Series (*.*)":
        file_dir = getDirectory(file)
        f = []
        file_list = []
        ext = getFileNameType(file)[1].lower()
        # set correct file_type
        if ext == "emd":
            file_type = "Velox emd Files (*.emd)"
        elif ext in ["dm3", "dm4"]:
            file_type = "DigitalMicrograph Files (*.dm3 *.dm4)"
        elif ext == "ser":
            file_type = "TIA ser Files (*.ser)"
        elif ext in ["tif", "tiff"]:
            file_type = "Tiff Files (*.tif *.tiff)"
        elif ext in ["jpg", "jpeg", "png", "bmp"]:
            file_type = "Image Formats (*.tif *.tiff *.jpg *.jpeg *.png *.bmp)"
        elif ext == "pkl":
            file_type = "Pickle Dictionary Files (*.pkl)"
        elif ext == "npy":
            file_type = "Numpy Array Files (*.npy)"
        else:
            print("Unsupported file formats for image series!")
            return

        # Iterate over all files in the specified directory
        for filename in os.listdir(file_dir):
            # Check if the file matches the pattern
            if filename.endswith(f".{ext}"):
                # Construct the full file path
                file_path = os.path.join(file_dir, filename)
                # Ensure it is a file
                if os.path.isfile(file_path):
                    file_list.append(file_path)

        if file_list:
            file_list.sort()  # Sort the file list alphabetically

        # A dialog to reorder the loaded images
        stack_list = [getFileNameType(img_file)[0] for img_file in file_list]
        dialog = ImportStackDialog(stack_list)
        if dialog.exec_() == QDialog.Accepted:
            reorder = dialog.ordered_items_idx
            reordered_file = [file_list[idx] for idx in reorder]
        else:
            return

        stack_img = []
        for img_file in reordered_file:
            try:
                img = load_file(img_file, file_type)
                stack_img.append(img[0])
            except Exception as e:
                print(f"Error loading {img_file}: {e} Skipped.")

        stack_dict = stack_img[0]
        img_size = stack_dict["data"].shape
        if len(img_size) != 2:
            print("Invalid image size! Images must be 2-dimensional!")
            return
        stack_array = []
        for img_dict in stack_img:
            if img_dict["data"].shape == img_size:
                stack_array.append(img_dict["data"])
            else:
                print(
                    f"{img_dict['metadata']['General']['original_filename']} has been skipped due to invalid image size!"
                )
        stack = np.stack(stack_array)

        stack_dict["data"] = stack
        # reformat the axes
        z_axis = {
            "size": stack_dict["data"].shape[0],
            "index_in_array": 0,
            "name": "z",
            "scale": 1,
            "offset": 0.0,
            "units": None,
            "navigate": True,
        }
        stack_dict["axes"].insert(0, z_axis)
        stack_dict["axes"][1]["index_in_array"] = 1
        stack_dict["axes"][2]["index_in_array"] = 2
        f = [stack_dict]

    # Validate the content of f
    f_valid = []
    for img_dict in f:
        img_valid = {}
        for key in ["data", "axes", "metadata"]:
            if key in img_dict.keys():
                img_valid[key] = img_dict[key]
                # ['data', 'axes', 'metadata'] are necessary
            else:
                img_valid = {}
                break
        if img_valid:
            try:
                img_valid["original_metadata"] = img_dict["original_metadata"]
                # ['original_metadata'] is optional
            except Exception:
                pass
            for axis in img_valid["axes"]:
                if "navigate" not in axis.keys():
                    # Need this navigate key to write some formats
                    axis.setdefault("navigate", False)
            if len(img_valid["axes"]) == 3:
                # For image stacks, the first axis is navigable
                img_valid["axes"][0]["navigate"] = True
            f_valid.append(img_valid)

    return f_valid


def load_4dstem(file, file_type, lazy=False):
    # Placeholder function for loading 4D-STEM data
    # The actual implementation will depend on the specific format of the 4D-STEM data and may require additional libraries
    print(f"Loading 4D-STEM data from {file} with type {file_type}...")
    # EMPAD file
    if file_type == "EMPAD Files (*.xml)":
        f = empad_reader(file, lazy=lazy)[0]

    elif file_type == "Pickle Dictionary Files (*.pkl)":
        with open(file, "rb") as file:
            f = pickle.load(file)

    elif file_type == "USID (*.h5 *.hdf5)":
        f = usid_reader(file, lazy=lazy)[0]

    elif file_type == "py4DSTEM (*.h5 *.hdf5)":
        f_list = load_py4dstem(file)
        if len(f_list) > 1:
            dialog = Select4DDatasetDialog(f_list)
            if dialog.exec_() == QDialog.Accepted:
                f = dialog.selected
            else:
                return
        elif len(f_list) == 1:
            f = f_list[0]
        else:
            print("No valid 4D dataset found in this file!")
            return

    elif file_type == "DigitalMicrograph Files (*.dm3 *.dm4)":
        f = dm_reader(file)[0]

    elif file_type == "Numpy Array Files (*.npy)":
        data = np.load(file)
        if data.ndim != 4:
            raise ValueError(
                "Invalid 4D-STEM data! The numpy array must be 4-dimensional."
            )
        f = {
            "data": data,
            "axes": [
                {
                    "name": "scan_y",
                    "size": data.shape[0],
                    "index_in_array": 0,
                    "scale": 1,
                    "offset": 0.0,
                    "units": None,
                    "navigate": True,
                },
                {
                    "name": "scan_x",
                    "size": data.shape[1],
                    "index_in_array": 1,
                    "scale": 1,
                    "offset": 0.0,
                    "units": None,
                    "navigate": True,
                },
                {
                    "name": "height",
                    "size": data.shape[2],
                    "index_in_array": 2,
                    "scale": 1,
                    "offset": 0.0,
                    "units": None,
                    "navigate": False,
                },
                {
                    "name": "width",
                    "size": data.shape[3],
                    "index_in_array": 3,
                    "scale": 1,
                    "offset": 0.0,
                    "units": None,
                    "navigate": False,
                },
            ],
            "metadata": {
                "General": {
                    "original_filename": os.path.basename(file),
                    "title": getFileNameType(file)[0],
                }
            },
            "original_metadata": {},
        }

    # Validate the content of f
    f_valid = {}
    for key in ["data", "axes", "metadata"]:
        if key in f.keys():
            f_valid[key] = f[key]
        else:
            f_valid = {}
            break

    if f_valid:
        # Some data contains NaN. Replace with zero
        # data = f_valid["data"]
        # np.nan_to_num(data, copy=False)
        try:
            f_valid["original_metadata"] = f["original_metadata"]
            # ['original_metadata'] is optional
        except Exception:
            pass
        for axis in f_valid["axes"]:
            if "navigate" not in axis.keys():
                # Need this navigate key to write some formats
                axis.setdefault("navigate", True)
        # Set the last two axes to be non-navigable
        f_valid["axes"][-1]["navigate"] = False
        f_valid["axes"][-2]["navigate"] = False

        return f_valid

    else:
        print(f"Invalid 4D-STEM data! Missing key: {key}")
        return


# A very basic reader for py4DSTEM h5/hdf5 files
def load_py4dstem(file_path):
    """
    Read HDF5 file saved by py4DSTEM with the schema:
      <unknown_root>/datacube/data
      <unknown_root>/datacube/dim0, dim1, dim2, dim3
      <unknown_root>/metadatabundle/calibration (optional)

    Returns:
      {
        "data": np.ndarray,
        "metadata": dict,
        "axes": list[dict]
      }
    """

    def decode_if_bytes(value):
        if isinstance(value, (bytes, bytearray)):
            return value.decode("utf-8", errors="replace")
        return value

    def to_python(obj):
        if isinstance(obj, h5py.Dataset):
            value = obj[()]
            if isinstance(value, np.ndarray):
                if value.dtype.kind in {"S", "O"}:
                    return np.vectorize(decode_if_bytes)(value)
                return value
            if isinstance(value, np.generic):
                return decode_if_bytes(value.item())
            return decode_if_bytes(value)

        if isinstance(obj, h5py.Group):
            out = {}
            if obj.attrs:
                out["_attrs"] = {k: decode_if_bytes(v) for k, v in obj.attrs.items()}
            for k, v in obj.items():
                out[k] = to_python(v)
            return out

        return obj

    def scalar(value):
        if isinstance(value, np.ndarray):
            if value.size == 1:
                return decode_if_bytes(
                    value.reshape(-1)[0].item()
                )  # Get the first element safely
            return value.tolist()
        if isinstance(value, np.generic):
            return decode_if_bytes(value.item())
        return decode_if_bytes(value)

    def find_root_group(h5_file):
        # Find the root group in the HDF5 file
        for obj in h5_file.values():
            if isinstance(obj, h5py.Group):
                return obj
        raise KeyError("Could not find a root group in this file!")

    def find_4D_data_group(root):
        # Find the 4D data group that contains the 'data' dataset
        datagroups = []
        for group in root.values():
            if isinstance(group, h5py.Group):
                if (
                    "data" in group
                    and isinstance(group["data"], h5py.Dataset)
                    and group["data"].ndim == 4
                ):
                    datagroups.append(group)
        return datagroups

    def get_calibration(root):
        # Try to get calibration of the 4D dataset if available, otherwise return default values
        for group in root.values():
            if isinstance(group, h5py.Group):
                if "calibration" in group:
                    calibration = to_python(group["calibration"])
                    r_scale = scalar(calibration.get("R_pixel_size", 1))
                    r_units = scalar(calibration.get("R_pixel_units", None))
                    q_scale = scalar(calibration.get("Q_pixel_size", 1))
                    q_units = scalar(calibration.get("Q_pixel_units", None))

                    return {
                        "R_pixel_size": r_scale,
                        "R_pixel_units": r_units,
                        "Q_pixel_size": q_scale,
                        "Q_pixel_units": q_units,
                    }
        return {
            "R_pixel_size": 1,
            "R_pixel_units": None,
            "Q_pixel_size": 1,
            "Q_pixel_units": None,
        }

    def get_4D_data(group):
        data = to_python(group["data"][()])
        return data

    with h5py.File(file_path, "r") as f:
        file_name = os.path.basename(file_path)
        root = find_root_group(f)
        calibration = get_calibration(root)
        r_scale = calibration["R_pixel_size"]
        r_units = calibration["R_pixel_units"]
        q_scale = calibration["Q_pixel_size"]
        q_units = calibration["Q_pixel_units"]
        data_groups = find_4D_data_group(root)
        data_dictionaries = []
        if data_groups:
            for group in data_groups:
                try:
                    data = get_4D_data(group)
                    axis_names = ["scan_y", "scan_x", "height", "width"]
                    axis_scales = [r_scale, r_scale, q_scale, q_scale]
                    axis_units = [r_units, r_units, q_units, q_units]
                    navigation_flags = [True, True, False, False]
                    axes = [
                        {
                            "index_in_array": i,
                            "name": axis_names[i],
                            "navigate": navigation_flags[i],
                            "offset": 0,
                            "scale": axis_scales[i],
                            "size": int(data.shape[i]),
                            "units": axis_units[i],
                        }
                        for i in range(4)
                    ]
                    metadata = {
                        "General": {
                            "title": os.path.basename(group.name),
                            "original_filename": file_name,
                        },
                        "Signal": {"signal_type": "electron_diffraction"},
                    }

                    data_dict = {
                        "data": data,
                        "metadata": metadata,
                        "axes": axes,
                        "original_metadata": {},
                    }
                    data_dictionaries.append(data_dict)

                except Exception as e:
                    print(f"Error processing group {group.name}: {e}")
                    continue

        return data_dictionaries


class Select4DDatasetDialog(QDialog):
    def __init__(self, datasets, parent=None):
        super().__init__(parent)

        self.datasets = datasets if datasets is not None else []
        self.selected = None

        self.setWindowTitle("Select 4D-STEM dataset")
        self.setGeometry(100, 100, 200, 100)

        layout = QVBoxLayout()

        self.listWidget = QListWidget(self)

        for idx, dataset in enumerate(self.datasets):
            title = ""
            try:
                title = dataset["metadata"]["General"]["title"]
            except Exception:
                title = ""

            if not title:
                title = f"Dataset {idx}"

            self.listWidget.addItem(QListWidgetItem(title))

        if self.listWidget.count() > 0:
            self.listWidget.setCurrentRow(0)

        layout.addWidget(self.listWidget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

        app = QApplication.instance()
        if app is not None:
            screen = app.primaryScreen()
            if screen is not None:
                frame = self.frameGeometry()
                frame.moveCenter(screen.availableGeometry().center())
                self.move(frame.topLeft())

    def handle_ok(self):
        row = self.listWidget.currentRow()
        if 0 <= row < len(self.datasets):
            self.selected = self.datasets[row]
        else:
            self.selected = None
        self.accept()


class ImportStackDialog(QDialog):
    def __init__(self, items):
        super().__init__()

        self.ordered_items_idx = []
        self.item_to_index = {item: idx for idx, item in enumerate(items)}

        self.setWindowTitle("Reorder image stack")
        self.setGeometry(100, 100, 300, 400)

        # Layout
        layout = QVBoxLayout()

        # QListWidget setup
        self.listWidget = QListWidget(self)
        self.listWidget.setDragDropMode(QListWidget.InternalMove)

        # Add items to the QListWidget
        reordered = sorted(items)
        for item in reordered:
            listItem = QListWidgetItem(item)
            self.listWidget.addItem(listItem)

        # Add QListWidget to the layout
        layout.addWidget(self.listWidget)

        # OK button to confirm and close
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.handle_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Set the layout for the dialog
        self.setLayout(layout)

        app = QApplication.instance()
        if app is not None:
            screen = app.primaryScreen()
            if screen is not None:
                frame = self.frameGeometry()
                frame.moveCenter(screen.availableGeometry().center())
                self.move(frame.topLeft())

    def contextMenuEvent(self, event):
        # Check if there is an item at the current mouse position
        item = self.listWidget.itemAt(self.listWidget.mapFromGlobal(event.globalPos()))
        if item:
            # Create context menu
            menu = QMenu(self)
            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.deleteItem(item))
            menu.addAction(delete_action)

            move_to_top_action = QAction("Move to Top", self)
            move_to_top_action.triggered.connect(lambda: self.moveToTop(item))
            menu.addAction(move_to_top_action)

            move_to_bottom_action = QAction("Move to Bottom", self)
            move_to_bottom_action.triggered.connect(lambda: self.moveToBottom(item))
            menu.addAction(move_to_bottom_action)

            # Show context menu
            menu.exec_(event.globalPos())

    def deleteItem(self, item):
        # Remove the item from the list widget
        self.listWidget.takeItem(self.listWidget.row(item))

    def moveToTop(self, item):
        # Get the row of the current item and remove it
        row = self.listWidget.row(item)
        self.listWidget.takeItem(row)
        # Insert it at the top
        self.listWidget.insertItem(0, item)

    def moveToBottom(self, item):
        # Get the row of the current item and remove it
        row = self.listWidget.row(item)
        self.listWidget.takeItem(row)
        # Insert it at the bottom
        self.listWidget.addItem(item)

    def handle_ok(self):
        for index in range(self.listWidget.count()):
            item_text = self.listWidget.item(index).text()
            original_index = self.item_to_index[item_text]
            self.ordered_items_idx.append(original_index)
            self.accept()


def convert_file(file, filetype, output_dir, f_type, save_metadata=False, **kwargs):
    # f_type: The file type to be saved. e.g., '.tif', '.png', '.jpg'
    #
    f_name = getFileNameType(file)[0]

    f = load_file(file, filetype)

    if len(f) != 0:  # Valid input containing at least one image
        if f[0]["data"].ndim == 3:
            DCFI = True
        else:
            DCFI = False

        if not DCFI:
            # Non DCFI, convert directly
            for img in f:
                try:
                    title = img["metadata"]["General"]["title"]
                except Exception:
                    title = ""

                new_name = f_name + "_" + title

                save_file_as(img, new_name, output_dir, f_type=f_type, **kwargs)

                if save_metadata:
                    metadata = img["metadata"]
                    try:
                        extra_metadata = img["original_metadata"]
                        metadata.update(extra_metadata)
                    except Exception as e:
                        print(f"Error reading original metadata: {e}")
                    with open(
                        os.path.join(output_dir, new_name + ".json"), "w"
                    ) as j_file:
                        json.dump(metadata, j_file, indent=4)

        else:
            # DCFI images, convert into a folder
            new_dir = os.path.join(output_dir, f_name)
            if not os.path.exists(new_dir):
                os.makedirs(new_dir)
            for img in f:
                data = img["data"]
                metadata = img["metadata"]
                try:
                    title = img["metadata"]["General"]["title"]
                except Exception:
                    title = ""
                stack_num = img["data"].shape[0]  # Number of stacks

                # Modify the axes
                axes = img["axes"]
                if len(axes) == 3:
                    axes.pop(0)
                    axes[0]["index_in_array"] = 0
                    axes[1]["index_in_array"] = 1

                if save_metadata:
                    try:
                        metadata_to_save = metadata.copy()
                        extra_metadata = img["original_metadata"]
                        metadata_to_save.update(extra_metadata)
                    except Exception as e:
                        print(f"Error reading original metadata: {e}")
                    with open(
                        os.path.join(new_dir, title + "_metadata.json"), "w"
                    ) as j_file:
                        json.dump(metadata_to_save, j_file, indent=4)

                for idx in range(stack_num):
                    new_img = {"data": data[idx], "axes": axes, "metadata": metadata}
                    new_name = title + "_{}".format(idx)

                    save_file_as(new_img, new_name, new_dir, f_type, **kwargs)


def gamma_correct_lut(lut: np.ndarray, gamma: float) -> np.ndarray:
    """Return a gamma-corrected copy of LUT (Nx4 uint8), where input x in [0,1]
    is remapped by x' = x ** (1/gamma) before sampling the base LUT."""
    try:
        g = float(gamma)
    except Exception:
        g = 1.0
    if g <= 0:
        g = 1.0
    if abs(g - 1.0) < 1e-6:
        return lut

    n = lut.shape[0]
    x = np.linspace(0.0, 1.0, n, dtype=np.float32)
    y = np.power(x, g)  # remapped positions
    idx = y * (n - 1)
    i0 = np.floor(idx).astype(np.int32)
    i1 = np.clip(i0 + 1, 0, n - 1)
    t = (idx - i0).astype(np.float32)[:, None]

    lut_f = lut.astype(np.float32)
    out = (1.0 - t) * lut_f[i0] + t * lut_f[i1]
    return out.astype(np.uint8)


def calculate_angle_from_3_points(A, B, C):
    """
    Calculate the <ABC when their coordinates are given
    """
    # A, B, C are the coordinates of the points (x, y)
    # Vector AB
    AB = (A[0] - B[0], A[1] - B[1])
    # Vector BC
    BC = (C[0] - B[0], C[1] - B[1])

    # Dot product of AB and BC
    dot_product = AB[0] * BC[0] + AB[1] * BC[1]

    # Magnitude of AB and BC
    magnitude_AB = math.sqrt(AB[0] ** 2 + AB[1] ** 2)
    magnitude_BC = math.sqrt(BC[0] ** 2 + BC[1] ** 2)

    # Cosine of the angle
    cos_theta = dot_product / (magnitude_AB * magnitude_BC)
    cos_theta = np.clip(
        cos_theta, -1.0, 1.0
    )  # Ensure the value is within valid range for acos

    # Angle in radians
    angle_rad = math.acos(cos_theta)

    # Angle in degrees
    angle_deg = math.degrees(angle_rad)

    return angle_deg


def calculate_angle_to_horizontal(A, B):
    """
    Calculate the angle of A, B and x direction
    """
    y = B[1] - A[1]
    x = B[0] - A[0]
    if x == 0:
        if y > 0:
            ang = -90
        else:
            ang = 90
        return ang
    ang_rad = math.atan((B[1] - A[1]) / (B[0] - A[0]))
    ang = math.degrees(ang_rad)

    # Reformat the angle to be -180 to 180
    if x > 0 and y > 0:
        return -1 * ang
    if x > 0 and y < 0:
        return -1 * ang
    if x < 0 and y > 0:
        return -180 - ang
    if x < 0 and y < 0:
        return 180 - ang

    return ang


def measure_distance(A, B, scale=1):
    x0, y0 = A
    x1, y1 = B
    distance_pixels = np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
    distance_units = distance_pixels * scale
    return distance_units


def closer_point(p0, p1, p2):
    # Calculate the Euclidean distance from p0 to p1
    distance_p1 = measure_distance(p0, p1)

    # Calculate the Euclidean distance from p0 to p2
    distance_p2 = measure_distance(p0, p2)

    # Determine which point is closer to p0 and return it
    if distance_p1 < distance_p2:
        return p1, p2
    else:
        return p2, p1


def line(p1, p2):
    """
    Find a line function from two points
    Return k ,b in the form of y = kx + b
    """
    A = p2[1] - p1[1]
    B = p2[0] - p1[0]
    k = A / B
    return k, -k * p1[0] + p1[1]


def find_img_by_title(img_dict, title):
    # Find an image in img_dict by its title
    # img_dict should be UI_TemCompanion.preview_dict
    return img_dict.get(title, None)
    # for plot in img_dict.values():
    #     if plot.canvas.canvas_name == title:
    #         return plot
