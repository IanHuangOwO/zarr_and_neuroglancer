import tifffile
import zarr
import argparse
import os
import sys
import numpy as np

from skimage.transform import resize
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import cpu_count
from tqdm import tqdm

"""
Usage:
python tiff_to_zarr.py 
    <tiff_path>         F:\Lab\others\YA_HAN\BIRDs\annotation_cropped.tif 
    <zarr_path>         F:\Lab\others\YA_HAN\annotation.zarr
    --chunk-size        128 128 128
    --resize-shape      1950 8800 3800
    --resize-algorithm  nearest
"""

def resize_image(image_xy, output_shape, dtype, order):
    """
    Resize a single 2D image (slice) to the specified shape using the selected interpolation order.
    
    Parameters:
        image_xy (np.ndarray): The 2D input image to be resized.
        output_shape (tuple): The desired (height, width) of the output image.
        dtype (numpy dtype): The target data type for the resized image.
        order (int): Interpolation order (0=nearest, 1=bilinear, 3=bicubic, etc.)
    
    Returns:
        np.ndarray: The resized image in the given dtype.
    """
    resized = resize(
        image=image_xy,
        output_shape=output_shape,
        order=order,
        mode='reflect',
        preserve_range=True
    ).astype(dtype)
    return resized

def reesize_and_save(data: np.ndarray, resize_factors: tuple, zarr_output, order: int):
    """
    Resize a 3D image volume (Z, Y, X) to a new shape in two steps:
    1. Resize along the Z axis (depth).
    2. Resize each 2D slice (XY plane) in parallel using threads.

    Parameters:
        data (np.ndarray): The original 3D TIFF image volume.
        resize_factors (tuple): The desired (Z, Y, X) shape of the resized volume.
        zarr_output (zarr.core.Array): The output Zarr array for storing resized images.
        order (int): Interpolation order to use during resizing.
    """
    output_shape_z = (resize_factors[0], data.shape[1], data.shape[2])
    data_resized_z = resize_image(data, output_shape_z, data.dtype, order)
    
    output_shape_xy = (resize_factors[1], resize_factors[2])
    with ThreadPoolExecutor(max_workers = cpu_count() - 2) as executor:
        for idx in tqdm(range(0, resize_factors[0], zarr_output.chunks[0]), desc="Resizing and writing chunks"):
            start_idx, end_idx = idx, min(idx + zarr_output.chunks[0], resize_factors[0])
            
            futures = [
                executor.submit(resize_image, image_xy, output_shape_xy, data.dtype, order)
                for image_xy in data_resized_z[start_idx:end_idx]
            ]
            
            resized_images = [future.result() for future in futures]
            zarr_output[start_idx:end_idx, :, :] = np.array(resized_images)

def tiff_to_zarr(input_tiff_path, output_zarr_path, resized_size=None, chunk_size=(128, 128, 128), compressor=None, resize_order=0):
    """
    Convert a 3D TIFF image to a Zarr array, optionally resizing it during the process.

    Parameters:
        input_tiff_path (str): Path to the input 3D TIFF file.
        output_zarr_path (str): Path to the output Zarr storage.
        resized_size (tuple, optional): Desired (Z, Y, X) shape of the output. If None, no resizing is done.
        chunk_size (tuple): Zarr chunk size. Default is (128, 128, 128).
        compressor (zarr.Compressor, optional): Compressor for Zarr (e.g., Blosc, Zlib). Default is None.
        resize_order (int): Interpolation order to use during resizing (0=nearest, 1=bilinear, etc.)
    """
    if not os.path.exists(input_tiff_path):
        raise FileNotFoundError(f"The input TIFF file '{input_tiff_path}' does not exist.")
    
    print("Reading TIFF file...")
    with tifffile.TiffFile(input_tiff_path) as tiff:
        data = tiff.asarray()
    
    print(f"Original TIFF shape: {data.shape}, dtype: {data.dtype}")

    if resized_size is not None:
        if len(resized_size) != len(data.shape):
            raise ValueError(f"Resized dimensions {resized_size} must match input dimensions {len(data.shape)}.")

        print(f"Resizing image to shape {resized_size} using interpolation order {resize_order}...")

        zarr_output = zarr.open(
            output_zarr_path,
            mode='w',
            shape=resized_size,
            dtype=data.dtype,
            chunks=chunk_size,
            compressor=compressor
        )

        reesize_and_save(data, resized_size, zarr_output, resize_order)
    else:
        print("Saving original data without resizing...")
        zarr_output = zarr.open(
            output_zarr_path,
            mode='w',
            shape=data.shape,
            dtype=data.dtype,
            chunks=chunk_size,
            compressor=compressor
        )
        zarr_output[:] = data

    print(f"Zarr file saved at: {output_zarr_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert a 3D TIFF image to a Zarr format with optional resizing.")
    parser.add_argument("tiff_path", type=str, help="Path to the input 3D TIFF file.")
    parser.add_argument("zarr_path", type=str, help="Path to save the output Zarr file.")
    parser.add_argument("--resize-shape", type=int, nargs='+', default=None,
                        help="Resize shape for Z, Y, X dimensions (e.g., 100 512 512).")
    parser.add_argument("--chunk-size", type=int, nargs='+', default=[128, 128, 128],
                        help="Chunk size for Zarr array.")
    parser.add_argument("--compressor", type=str, default=None,
                        help="Zarr compressor to use: 'blosc' or 'zlib'. Default is None.")
    parser.add_argument("--resize-algorithm", type=str, choices=["nearest", "bilinear", "bicubic", "lanczos"], default="nearest",
                        help="Interpolation algorithm to use when resizing (default: nearest).")

    args = parser.parse_args()

    # Handle compressor option
    compressor = None
    if args.compressor:
        if args.compressor.lower() == 'blosc':
            compressor = zarr.Blosc()
        elif args.compressor.lower() == 'zlib':
            compressor = zarr.Zlib()
        else:
            raise ValueError(f"Unsupported compressor: {args.compressor}")

    # Map interpolation algorithm name to skimage order value
    interpolation_orders = {
        "nearest": 0,
        "bilinear": 1,
        "bicubic": 3,
        "lanczos": 5
    }
    resize_order = interpolation_orders[args.resize_algorithm]

    # Start the conversion
    tiff_to_zarr(args.tiff_path, args.zarr_path, tuple(args.resize_shape) if args.resize_shape else None, tuple(args.chunk_size), compressor, resize_order)
    
    
if __name__ == "__main__":
    sys.exit(main())