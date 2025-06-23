import logging
import numpy as np
import zarr

from pathlib import Path
from skimage.transform import resize
from concurrent.futures import ProcessPoolExecutor

# Set up module-level logger
logger = logging.getLogger(__name__)

def _resize_xy_worker(args):
    """
    args = (slice_xy, target_y, target_x, dtype, order)
    """
    slice_xy, ty, tx, dt, ord = args
    return resize(
        slice_xy,
        (ty, tx),
        order=ord,
        preserve_range=True,
        anti_aliasing=False
    ).astype(dt)

def _resize_xz_worker(args):
    """
    args = (slice_xz, target_z, target_x, dtype, order)
    """
    slice_xz, tz, tx, dt, ord = args
    return resize(
        slice_xz,
        (tz, tx),
        order=ord,
        preserve_range=True,
        anti_aliasing=False
    ).astype(dt)

def two_pass_resize_zarr(
    input_source,
    output_arr: zarr.Array,
    temp_group: zarr.Group,
    target_shape: tuple[int,int,int],
    dtype: np.dtype,
    order: int = 1,
    chunk_size: int = 64,
):
    """
    Resize a 3D Zarr array in two passes with an on‐disk temp.

    Args:
      input_arr: zarr.Array, shape (Z, Y, X)
      output_arr: zarr.Array, pre‐created with shape (target_z, target_y, target_x)
      temp_group: zarr.Group in which to create temp_key dataset
      temp_key: name of the temp dataset (e.g. "temp")
      target_shape: (target_z, target_y, target_x)
      dtype: output dtype
      order: interpolation order for skimage.resize
      chunk_size: slices (for XY pass) and rows (for XZ pass)
      memory_threshold_gb: unused here (always temp→zarr), but kept for signature
    """

    current_z, _, _ = (
        input_source.volume_shape if hasattr(input_source, 'read')
        else input_source.shape
    )
    target_z, target_y, target_x = target_shape
    
    # 1) create (or overwrite) the on‐disk temp buffer
    temp_arr = temp_group.require_dataset(
        "temp",
        shape=(current_z, target_y, target_x),
        dtype=dtype,
        chunks=(chunk_size, chunk_size, chunk_size),
        compression=None,
        overwrite=True
    )
    
    def _get_z_block(z0, z1):
        if hasattr(input_source, 'read'):
            return input_source.read(z_start=z0, z_end=z1)
        else:
            return input_source[z0:z1]

    # Pass 1: XY → temp_arr (unchanged)
    with ProcessPoolExecutor(max_workers=8) as exe:
        for z0 in range(0, current_z, chunk_size):
            z1 = min(z0 + chunk_size, current_z)
            block = _get_z_block(z0, z1)  # (dz, Y, X)
            args = [
                (block[i], target_y, target_x, dtype, order)
                for i in range(block.shape[0])
            ]
            resized_slices = list(exe.map(_resize_xy_worker, args))
            logger.info(f"Writing volume to temp z: {z0} - {z1}")
            temp_arr[z0:z1, :, :] = np.stack(resized_slices)

    # Pass 2: XZ → output_arr (now with threaded writes)
    with ProcessPoolExecutor(max_workers=8) as exe:
        for y0 in range(0, target_y, chunk_size):
            y1 = min(y0 + chunk_size, target_y)
            block = temp_arr[:, y0:y1, :]  # (Z, dy, X)
            args = [
                (block[:, j, :], target_z, target_x, dtype, order)
                for j in range(block.shape[1])
            ]
            resized_slices = list(exe.map(_resize_xz_worker, args))
            stack = np.stack(resized_slices)
            logger.info(f"Writing volume to OME y: {y0} - {y1}")
            output_arr[:, y0:y1, :] = stack.transpose(1, 0, 2)

    # Clean up
    logger.info(f"Cleaning temp zarr")
    del temp_group["temp"]


class FileWriter:
    def __init__(self, reader, output_path, full_res_shape, n_level=6, resize_factor=2,
                 chunk_size=128, memory_threshold=32, resize_order=1):
        self.reader = reader
        self.output_path = Path(output_path)
        self.ome_path = self.output_path / f"{reader.volume_name}_ome.zarr"
        self.full_res_shape = full_res_shape
        self.n_level = n_level
        self.resize_factor = resize_factor
        self.chunk_size = chunk_size
        self.memory_threshold = memory_threshold
        self.resize_order = resize_order
        logger.info(f"Initialized FileWriter with output: {self.ome_path}")

    def _resize_and_write(self, out_ds, level):
        if level == 0:
            current_z, current_y, current_x = self.reader.volume_shape
            target_z, target_y, target_x = self.full_res_shape
                
        else:
            prev_shape = out_ds[str(level - 1)].shape
            current_z, current_y, current_x = prev_shape
            target_z = current_z // self.resize_factor
            target_y = current_y // self.resize_factor
            target_x = current_x // self.resize_factor

        logger.info(f"Resizing level {level} from shape {(current_z, current_y, current_x)} to {(target_z, target_y, target_x)}")

        self._resize_and_write_level(
            out_ds, level,
            target_shape=(target_z, target_y, target_x),
            order=self.resize_order
        )

    def _resize_and_write_level(self, out_ds, level, target_shape, order):
        logger.info(f"Creating dataset for level {level} with shape {target_shape}")
        
        out_ds.create_dataset(
            str(level), shape=target_shape, dtype=self.reader.volume_dtype,
            chunks=(self.chunk_size, self.chunk_size, self.chunk_size), compression=None,
        )
        
        if level == 0:
            two_pass_resize_zarr(
                input_source=self.reader,
                output_arr=out_ds[str(level)],
                temp_group=out_ds,
                target_shape=target_shape,
                dtype=self.reader.volume_dtype,
                order=order,
                chunk_size=self.chunk_size
            )
        else:
            two_pass_resize_zarr(
                input_source=out_ds[str(level-1)],
                output_arr=out_ds[str(level)],
                temp_group=out_ds,
                target_shape=target_shape,
                dtype=self.reader.volume_dtype,
                order=order,
                chunk_size=self.chunk_size
            )

    def _write_multiscale_metadata(self, group):
        logger.info("Writing OME-Zarr multiscale metadata")
        datasets = []
        for level in range(self.n_level):
            scale_factor = self.resize_factor ** level
            datasets.append({
                "path": str(level),
                "coordinateTransformations": [
                    {
                        "type": "scale",
                        "scale": [scale_factor] * 3
                    }
                ]
            })

        multiscales = [{
            "version": "0.4",
            "name": "image",
            "axes": [
                {"name": "z", "type": "space"},
                {"name": "y", "type": "space"},
                {"name": "x", "type": "space"}
            ],
            "datasets": datasets
        }]

        group.attrs["multiscales"] = multiscales

    def write(self):
        logger.info(f"Starting write process to {self.ome_path}")
        store = zarr.DirectoryStore(self.ome_path)
        group = zarr.group(store=store)

        for level in range(self.n_level):
            if str(level) in group:
                logger.info(f"Level {level} already exists, skipping.")
                continue

            logger.info(f"Processing level {level}")
            self._resize_and_write(group, level=level)

        self._write_multiscale_metadata(group)
        logger.info("Write process complete.")