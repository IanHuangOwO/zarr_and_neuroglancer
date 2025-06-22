import logging
import numpy as np
import zarr
from pathlib import Path
from skimage.transform import resize
from concurrent.futures import ProcessPoolExecutor

# Set up module-level logger
logger = logging.getLogger(__name__)

def resize_xy_slice(args):
    slice_xy, target_y, target_x, dtype, order = args
    resized = resize(
        slice_xy, (target_y, target_x),
        order=order, preserve_range=True, anti_aliasing=False
    ).astype(dtype)
    return resized


def resize_xz_slice(args):
    slice_xz, target_z, target_x, dtype, order = args
    resized = resize(
        slice_xz, (target_z, target_x),
        order=order, preserve_range=True, anti_aliasing=False
    ).astype(dtype)
    return resized


def can_use_memory(current_shape, target_y, target_x, dtype, memory_threshold_gb):
    current_z = current_shape[0]
    bytes_per_element = np.dtype(dtype).itemsize
    total_bytes = current_z * target_y * target_x * bytes_per_element
    total_gb = (total_bytes / (1024 ** 3)) * 2
    logger.info(f"Estimated memory usage: {total_gb:.2f} GB")
    return total_gb <= memory_threshold_gb


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

    def _resize_level_zero(self, out_ds):
        current_z, current_y, current_x = self.reader.volume_shape
        target_z, target_y, target_x = self.full_res_shape

        if (current_z, current_y, current_x) == (target_z, target_y, target_x):
            logger.info("Level 0: shapes match, copying raw data without resizing.")
            out_ds.create_dataset(
                "0", shape=self.full_res_shape, dtype=self.reader.volume_dtype,
                chunks=(self.chunk_size, self.chunk_size, self.chunk_size), overwrite=True
            )
            for z_start in range(0, current_z, self.chunk_size):
                z_end = min(z_start + self.chunk_size, current_z)
                logger.debug(f"Copying raw block: Z {z_start}-{z_end}")
                block = self.reader.read(z_start=z_start, z_end=z_end)
                out_ds["0"][z_start:z_end] = block
            return

        logger.info("Resizing level 0 from raw data")
        self._resize_and_write_level(
            out_ds, level=0,
            current_shape=(current_z, current_y, current_x),
            target_shape=self.full_res_shape,
            order=self.resize_order
        )

    def _resize_and_write(self, out_ds, level):
        if level == 0:
            self._resize_level_zero(out_ds)
        else:
            prev_shape = out_ds[str(level - 1)].shape
            current_z, current_y, current_x = prev_shape
            target_z = current_z // self.resize_factor
            target_y = current_y // self.resize_factor
            target_x = current_x // self.resize_factor

            logger.info(f"Resizing level {level} from shape {prev_shape} to {(target_z, target_y, target_x)}")

            self._resize_and_write_level(
                out_ds, level,
                current_shape=prev_shape,
                target_shape=(target_z, target_y, target_x),
                order=self.resize_order
            )

    def _resize_and_write_level(self, out_ds, level, current_shape, target_shape, order):
        current_z, _, _ = current_shape
        target_z, target_y, target_x = target_shape

        logger.info(f"Creating dataset for level {level} with shape {target_shape}")
        out_ds.create_dataset(
            str(level), shape=(target_z, target_y, target_x), dtype=self.reader.volume_dtype,
            chunks=(self.chunk_size, self.chunk_size, self.chunk_size), overwrite=True
        )

        use_temp_store = not can_use_memory(
            current_shape, target_y, target_x,
            self.reader.volume_dtype, self.memory_threshold
        )

        if use_temp_store:
            logger.info("Using temp storage for intermediate resizing")
            out_ds.create_dataset(
                'temp', shape=(current_z, target_y, target_x), dtype=self.reader.volume_dtype,
                chunks=(self.chunk_size, self.chunk_size, self.chunk_size), overwrite=True
            )
            temp = out_ds['temp']
        else:
            logger.info("Using in-memory buffer for intermediate resizing")
            temp = np.empty((current_z, target_y, target_x), dtype=self.reader.volume_dtype)

        with ProcessPoolExecutor(max_workers=8) as executor:
            for z_start in range(0, current_z, self.chunk_size):
                z_end = min(z_start + self.chunk_size, current_z)
                logger.debug(f"Resizing XY: Z {z_start}-{z_end}")

                if level == 0:
                    block = self.reader.read(start_z=z_start, end_z=z_end)
                else:
                    block = out_ds[str(level - 1)][z_start:z_end, :, :]

                args_list = [
                    (block[idx], target_y, target_x, self.reader.volume_dtype, order)
                    for idx in range(z_end - z_start)
                ]
                results = executor.map(resize_xy_slice, args_list)
                resized_block = np.stack(list(results))
                temp[z_start:z_end, :, :] = resized_block

            for y_start in range(0, target_y, self.chunk_size):
                y_end = min(y_start + self.chunk_size, target_y)
                logger.debug(f"Resizing XZ: Y {y_start}-{y_end}")

                block = temp[:, y_start:y_end, :]
                args_list = [
                    (block[:, idx, :], target_z, target_x, self.reader.volume_dtype, order)
                    for idx in range(y_end - y_start)
                ]
                results = executor.map(resize_xz_slice, args_list)
                resized_block = np.stack(list(results)).transpose(1, 0, 2)
                out_ds[str(level)][:, y_start:y_end, :] = resized_block

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
            logger.info(f"Processing level {level}")
            self._resize_and_write(group, level=level)

        if 'temp' in group:
            logger.info("Cleaning up temporary dataset")
            del group['temp']

        self._write_multiscale_metadata(group)
        logger.info("Write process complete.")