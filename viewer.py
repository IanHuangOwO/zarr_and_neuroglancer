import neuroglancer
import time 

# Set up Neuroglancer viewer
neuroglancer.set_server_bind_address('127.0.0.1')
viewer = neuroglancer.Viewer()

# Define data sources for raw image and masks
raw_path = 'zarr://http://localhost:8000/raw_image_ome.zarr/0'
mask_lectin_path = 'zarr://http://localhost:8000/lectin_mask_ome.zarr/0'
mask_0_path = 'zarr://http://localhost:8000/lectin_mask_process_0.zarr/filtered_mask'
mask_1_path = 'zarr://http://localhost:8000/lectin_mask_process_0.zarr/skeletonize_mask'
mask_2_path = 'zarr://http://localhost:8000/lectin_mask_process_1.zarr/filtered_mask'
mask_3_path = 'zarr://http://localhost:8000/lectin_mask_process_1.zarr/skeletonize_mask'

mask_neun_path = 'zarr://http://localhost:8000/neun_mask_ome.zarr\0'
mask_4_path = 'zarr://http://localhost:8000/neun_mask_process_0.zarr/filtered_mask'
mask_5_path = 'zarr://http://localhost:8000/neun_mask_process_0.zarr/maxima_mask'
mask_6_path = 'zarr://http://localhost:8000/neun_mask_process_1.zarr/filtered_mask'
mask_7_path = 'zarr://http://localhost:8000/neun_mask_process_1.zarr/maxima_mask'

# Add layers to the viewer
with viewer.txn() as s:
    # Add raw image layer with default voxel size
    s.layers['raw_image'] = neuroglancer.ImageLayer(
        source=raw_path,
    )
    s.layers['lectin_mask'] = neuroglancer.SegmentationLayer(
        source=mask_lectin_path,
    )

print(viewer)

# Infinite loop to keep the Neuroglancer session alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Neuroglancer viewer stopped.")