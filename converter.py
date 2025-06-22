import argparse
import logging
from converter.reader import FileReader
from converter.writer import FileWriter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

def parse_args():
    parser = argparse.ArgumentParser(description="Convert image volume to multiscale OME-Zarr.")
    
    # Positional arguments
    parser.add_argument("input", type=str, help="Input file or directory path")
    parser.add_argument("output", type=str, help="Output directory for OME-Zarr")
    
    # Input handling
    parser.add_argument("--input-type", choices=["auto", "single", "series"], default="auto",
                        help="Specify input type: single 3D file or series of 2D slices")
    parser.add_argument("--validate-all", action="store_true",
                        help="Validate shape and dtype for all slices in a series")

    # Memory/processing options
    parser.add_argument("--memory-limit", type=int, default=32,
                        help="Maximum memory (in GB) for temp buffers")
    parser.add_argument("--resize-order", type=int, default=0,
                        help="Interpolation order for resizing: 0=nearest, 1=bilinear, 2=quadratic, 3=bicubic, 4=biquartic, 5=quintic")
    parser.add_argument("--downscale-factor", type=int, default=2,
                        help="Downsampling factor per pyramid level")
    parser.add_argument("--levels", type=int, default=5,
                        help="Number of pyramid levels to generate")
    parser.add_argument("--chunk-size", type=int, default=128,
                        help="Chunk size for Zarr storage")

    # Optional override
    parser.add_argument("--override-shape", type=int, nargs=3, metavar=("Z", "Y", "X"),
                        help="Override the full-resolution volume shape")

    return parser.parse_args()

def main():
    args = parse_args()

    logging.info("Starting conversion process.")
    logging.info(f"Input path: {args.input}")
    logging.info(f"Output path: {args.output}")
    logging.info(f"Input type: {args.input_type}")
    logging.info(f"Memory limit: {args.memory_limit} GB")

    reader = FileReader(
        input_path=args.input,
        input_type=args.input_type,
        validate_all=args.validate_all,
        memory_limit_gb=args.memory_limit
    )

    full_res_shape = args.override_shape if args.override_shape else reader.volume_shape
    logging.info(f"Full-resolution shape: {full_res_shape}")

    writer = FileWriter(
        reader=reader,
        output_path=args.output,
        full_res_shape=full_res_shape,
        n_level=args.levels,
        resize_factor=args.downscale_factor,
        chunk_size=args.chunk_size,
        memory_threshold=args.memory_limit,
        resize_order=args.resize_order
    )

    logging.info("Writing multiscale OME-Zarr...")
    writer.write()
    logging.info("Conversion complete.")

if __name__ == "__main__":
    main()