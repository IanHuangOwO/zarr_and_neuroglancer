import tifffile
import zarr
import argparse
import os
import numpy as np

from skimage.transform import resize
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

"""
Usage:
python tiff_to_zarr.py 
    <tiff_path>         F:\Lab\others\YA_HAN\BIRDs\annotation_cropped.tif 
    <zarr_path>         F:\Lab\others\YA_HAN\annotation.zarr
    --chunk-size        128 128 128
    --resized-shape     1950 8800 3800
"""

def resize_image(image_xy, output_shape, dtype):
    """
    Resize a single 2D image (slice) to the specified shape using nearest-neighbor interpolation.
    
    Parameters:
        image_xy (np.ndarray): The 2D input image to be resized.
        output_shape (tuple): The desired (height, width) of the output image.
        dtype (numpy dtype): The target data type for the resized image.
    
    Returns:
        np.ndarray: The resized image in the given dtype.
    """
    resized = resize(
        image=image_xy,
        output_shape=output_shape,
        order=0,           # Nearest-neighbor interpolation
        mode='reflect',
        preserve_range=True
    ).astype(dtype)
    return resized

def reesize_and_save(data: np.ndarray, resize_factors: tuple, zarr_output):
    """
    Resize a 3D image volume (Z, Y, X) to a new shape in two steps:
    1. Resize along the Z axis (depth).
    2. Resize each 2D slice (XY plane) in parallel using threads.
    
    The result is written to a Zarr array in chunks.

    Parameters:
        data (np.ndarray): The original 3D TIFF image volume.
        resize_factors (tuple): The desired (Z, Y, X) shape of the resized volume.
        zarr_output (zarr.core.Array): The output Zarr array for storing resized images.
    """
    # Step 1: Resize the entire 3D volume along the Z axis
    output_shape_z = (resize_factors[0], data.shape[1], data.shape[2])
    data_resized_z = resize_image(data, output_shape_z, data.dtype)
    
    # Step 2: Resize each 2D XY slice in parallel
    output_shape_xy = (resize_factors[1], resize_factors[2])
    with ThreadPoolExecutor() as executor:
        for idx in tqdm(range(0, resize_factors[0], zarr_output.chunks[0]), desc="Resizing and writing chunks"):
            start_idx = idx
            end_idx = min(idx + zarr_output.chunks[0], resize_factors[0])
            
            # Submit tasks to resize each XY slice in the current Z chunk
            futures = [
                executor.submit(resize_image, image_xy, output_shape_xy, data.dtype)
                for image_xy in data_resized_z[start_idx:end_idx]
            ]
            
            # Gather the results in the original order
            resized_images = [future.result() for future in futures]
            
            # Save the resized chunk to the Zarr array
            zarr_output[start_idx:end_idx, :, :] = np.array(resized_images)

def tiff_to_zarr(input_tiff_path, output_zarr_path, resized_size=None, chunk_size=(128, 128, 128), compressor=None):
    """
    Convert a 3D TIFF image to a Zarr array, optionally resizing it during the process.

    Parameters:
        input_tiff_path (str): Path to the input 3D TIFF file.
        output_zarr_path (str): Path to the output Zarr storage.
        resized_size (tuple, optional): Desired (Z, Y, X) shape of the output. If None, no resizing is done.
        chunk_size (tuple): Zarr chunk size. Default is (128, 128, 128).
        compressor (zarr.Compressor, optional): Compressor for Zarr (e.g., Blosc, Zlib). Default is None.
    """
    if not os.path.exists(input_tiff_path):
        raise FileNotFoundError(f"The input TIFF file '{input_tiff_path}' does not exist.")
    
    # Load the TIFF as a 3D NumPy array
    print("Reading TIFF file...")
    with tifffile.TiffFile(input_tiff_path) as tiff:
        data = tiff.asarray()
    
    print(f"Original TIFF shape: {data.shape}, dtype: {data.dtype}")

    if resized_size is not None:
        if len(resized_size) != len(data.shape):
            raise ValueError(f"Resized dimensions {resized_size} must match input dimensions {len(data.shape)}.")

        print(f"Resizing image to shape {resized_size}...")

        # Create an empty Zarr array with the desired shape
        zarr_output = zarr.open(
            output_zarr_path,
            mode='w',
            shape=resized_size,
            dtype=data.dtype,
            chunks=chunk_size,
            compressor=compressor
        )

        # Perform resizing and write results to Zarr
        reesize_and_save(data, resized_size, zarr_output)
    else:
        # No resizing, just save the original data directly to Zarr
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a 3D TIFF image to a Zarr format with optional resizing.")
    parser.add_argument("tiff_path", type=str, help="Path to the input 3D TIFF file.")
    parser.add_argument("zarr_path", type=str, help="Path to save the output Zarr file.")
    parser.add_argument("--resized-shape", type=int, nargs='+', default=None,
                        help="Resize shape for Z, Y, X dimensions (e.g., 100 512 512).")
    parser.add_argument("--chunk-size", type=int, nargs='+', default=[128, 128, 128],
                        help="Chunk size for Zarr array.")
    parser.add_argument("--compressor", type=str, default=None,
                        help="Zarr compressor to use: 'blosc' or 'zlib'. Default is None.")

    args = parser.parse_args()

    # Select the appropriate Zarr compressor
    compressor = None
    if args.compressor:
        if args.compressor.lower() == 'blosc':
            compressor = zarr.Blosc()
        elif args.compressor.lower() == 'zlib':
            compressor = zarr.Zlib()
        else:
            raise ValueError(f"Unsupported compressor: {args.compressor}")
    
    if args.resized_shape:
        tuple(args.resized_shape)
    
    # Start the conversion process
    tiff_to_zarr(args.tiff_path, args.zarr_path, args.resized_shape, tuple(args.chunk_size), compressor)
