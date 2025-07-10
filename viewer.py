import neuroglancer
import time
from urllib.parse import urlparse, urlunparse

# Set up Neuroglancer viewer
neuroglancer.set_server_bind_address(bind_address='0.0.0.0', bind_port=7000)
viewer = neuroglancer.Viewer()

# Get and parse the original URL
original_url = viewer.get_viewer_url()
parsed = urlparse(original_url)

# Replace hostname with 'localhost'
modified_url = urlunparse(parsed._replace(netloc=f'localhost:{parsed.port}'))

defualt_path = 'zarr://http://localhost:8000'
with viewer.txn() as s:
    # Add raw image layer with default voxel size
    s.layers['defualt'] = neuroglancer.ImageLayer(
        source=defualt_path,
    )

# Print the updated URL
print("INFO:     Neuroglancer running on ", modified_url)

# Infinite loop to keep the Neuroglancer session alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Neuroglancer viewer stopped.")