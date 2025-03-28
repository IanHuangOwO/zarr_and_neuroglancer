import tifffile
import zarr
from skimage.transform import resize
import argparse
import os
from tqdm import tqdm

'''
python tiff_to_zarr.py tiff_path zarr_path 
'''

def resize_chunk(chunk, resize_factors):
    """
    Resize a single chunk using skimage.transform.resize.
    """
    return resize(
        chunk,
        output_shape=tuple(int(s * f) for s, f in zip(chunk.shape, resize_factors)),
        order=0,  # Nearest-neighbor interpolation
        mode='reflect',
        preserve_range=True
    ).astype(chunk.dtype)

def save_chunk_to_zarr(zarr_output, chunk, current_depth):
    """
    Save a resized chunk to the Zarr file at the appropriate depth.
    """
    depth = chunk.shape[0]
    zarr_output[current_depth:current_depth + depth, :, :] = chunk
    return current_depth + depth

def compute_resize_factors(original_shape, resized_to):
    """
    Compute the scale factors for resizing.
    """
    return tuple(new_dim / old_dim for new_dim, old_dim in zip(resized_to, original_shape))

def process_and_save_chunks(data, resize_factors, zarr_output, num_chunks):
    """
    Process data in chunks, resize, and save each chunk to Zarr.
    """
    chunk_depth = data.shape[0] // num_chunks
    chunks = [data[i:i + chunk_depth] for i in range(0, data.shape[0], chunk_depth)]
    current_depth = 0

    for chunk in tqdm(chunks, desc="Processing chunks"):
        resized_chunk = resize_chunk(chunk, resize_factors)
        current_depth = save_chunk_to_zarr(zarr_output, resized_chunk, current_depth)

def tiff_to_zarr(input_tiff_path, output_zarr_path, resized_to=None, num_chunks=10, chunk_size=(128, 128, 128), compressor=None):
    """
    Convert a 3D TIFF file to Zarr format with optional resizing using NumPy arrays.

    Parameters:
        input_tiff_path (str): Path to the input TIFF file.
        output_zarr_path (str): Path to the output Zarr file.
        resized_to (tuple, optional): Dimensions to resize the Z, Y, X dimensions. Defaults to None (no resizing).
        num_chunks (int): Number of chunks to divide the array into along the depth axis.
        chunk_size (tuple): Chunk size for Zarr storage.
        compressor (zarr.storage.Compressor, optional): Compressor to use for Zarr storage.

    Returns:
        None
    """
    # Check if the input file exists
    if not os.path.exists(input_tiff_path):
        raise FileNotFoundError(f"The input TIFF file '{input_tiff_path}' does not exist.")

    # Read the TIFF file into a NumPy array
    print("Reading TIFF file...")
    with tifffile.TiffFile(input_tiff_path) as tiff:
        data = tiff.asarray()

    print(f"Original TIFF file shape: {data.shape}, dtype: {data.dtype}")

    if resized_to is not None:
        if len(resized_to) != len(data.shape):
            raise ValueError(f"Resized dimensions {resized_to} must match the number of dimensions {len(data.shape)} of the input image.")

        print(f"Resizing 3D image to dimensions {resized_to}...")

        # Compute scale factors and initialize Zarr file
        resize_factors = compute_resize_factors(data.shape, resized_to)
        zarr_output = zarr.open(
            output_zarr_path,
            mode='w',
            shape=resized_to,
            dtype=data.dtype,
            chunks=chunk_size,
            compressor=compressor
        )

        # Process data in chunks
        process_and_save_chunks(data, resize_factors, zarr_output, num_chunks)

    else:
        # Save the original data to Zarr without resizing
        zarr_output = zarr.open(
            output_zarr_path,
            mode='w',
            shape=data.shape,
            dtype=data.dtype,
            chunks=chunk_size,
            compressor=compressor
        )
        print("Saving original data without resizing...")
        zarr_output[:] = data

    print(f"Zarr file saved at: {output_zarr_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert a TIFF file to a Zarr format, with optional resizing.")
    parser.add_argument("tiff_path", type=str, help="Path to the input TIFF file.")
    parser.add_argument("zarr_path", type=str, help="Path to save the output Zarr file.")
    parser.add_argument("--resized_shape", type=int, nargs='+', default=None, help="Dimensions to resize the Z, Y, X dimensions (e.g., 100 512 512). Default is no resizing.")
    parser.add_argument("--num_chunks", type=int, default=10, help="Number of chunks to divide the array into along the depth axis.")
    parser.add_argument("--chunk_size", type=int, nargs='+', default=[64, 64, 64], help="Chunk size for Zarr storage.")
    parser.add_argument("--compressor", type=str, default=None, help="Compressor to use for Zarr storage (e.g., 'blosc', 'zlib'). Default is None.")
    
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

    # Ensure chunk size is a tuple
    chunk_size = tuple(args.chunk_size)

    # try:
    tiff_to_zarr(args.tiff_path, args.zarr_path, tuple(args.resized_shape), args.num_chunks, chunk_size, compressor)
    # except Exception as e:
    #     print(f"An error occurred: {e}")
