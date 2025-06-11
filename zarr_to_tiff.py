import tifffile as tiff
import os
import argparse
import dask.array as da
from skimage.transform import resize

def zarr_to_tiff(zarr_path, tiff_path, resize_factors=None, interpolation_order=1, output_dtype='uint16'):
    """
    Convert a Zarr file back to TIFF format, with optional resizing using Dask and TIFF writing with ImageJ compatibility.

    Parameters:
        zarr_path (str): Path to the input Zarr file.
        tiff_path (str): Path to save the output TIFF file.
        resize_factors (tuple or None): Factors by which to resize (z, y, x). Default is None.
        interpolation_order (int): The order of the spline interpolation. Default is 1 (linear interpolation).
        output_dtype (str): Data type for the output TIFF file (e.g., 'uint8', 'uint16', 'float32'). Default is 'uint16'.
    """
    # Check if the Zarr file exists
    if not os.path.exists(zarr_path):
        raise FileNotFoundError(f"The file {zarr_path} does not exist.")

    # Open the Zarr file as a Dask array
    zarr_data = da.from_zarr(zarr_path)

    # Apply resizing if factors are provided
    if resize_factors:
        zarr_data = da.map_overlap(
            lambda block, _: resize(
                block,
                output_shape=tuple(int(s * f) for s, f in zip(block.shape, resize_factors)),
                order=interpolation_order,
                mode='reflect',
                preserve_range=True
            ),
            zarr_data,
            depth={0: interpolation_order, 1: interpolation_order, 2: interpolation_order},
            boundary='reflect',
            dtype=zarr_data.dtype
        )

    # Ensure ImageJ-compatible data types
    if output_dtype not in ["uint8", "uint16", "float32"]:
        raise ValueError(f"The specified data type '{output_dtype}' is not supported by the ImageJ format. Use 'uint8', 'uint16', or 'float32'.")

    # Compute the entire array and save it as a contiguous TIFF file
    print("Computing the entire dataset...")
    full_data = zarr_data.compute()
    
    print("Writing data to the TIFF file...")
    with tiff.TiffWriter(tiff_path, imagej=True) as tiff_writer:
        tiff_writer.write(full_data.astype(output_dtype), metadata={'axes': 'ZYX'})

    print(f"Zarr file has been successfully converted to TIFF format at {tiff_path}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a Zarr file back to TIFF format, with optional resizing using Dask.")
    parser.add_argument("zarr_path", type=str, help="Path to the input Zarr file.")
    parser.add_argument("tiff_path", type=str, help="Path to save the output TIFF file.")
    parser.add_argument("--resize-factors", type=float, nargs=3, default=None, help="Factors to resize the Z, Y, X dimensions (e.g., 0.5 0.5 0.5). Default is no resizing.")
    parser.add_argument("--resize-algorithm", type=int, default=1, help="The order of the spline interpolation (e.g., 0 for nearest, 1 for linear). Default is 1.")
    parser.add_argument("--output_dtype", type=str, default="uint16", help="Data type for the output TIFF file (e.g., 'uint8', 'uint16', 'float32'). Default is 'uint16'.")

    args = parser.parse_args()
    
    zarr_to_tiff(args.zarr_path, args.tiff_path, args.resize_factors, args.resize_algorithm, args.output_dtype)