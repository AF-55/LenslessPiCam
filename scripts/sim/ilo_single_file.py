"""

Simulate a mask, use face alignment on a face image and simulate a measurement with the mask on the image.

Procedure is as follows:

1) Simulate the mask.
2) Align the face.
3) Simulate a measurement with the mask and specified physical parameters.

Example usage:

Simulate FlatCam with separable simulation (https://arxiv.org/abs/1509.00116, Eq 7):
```
python scripts/sim/ilo_single_file.py mask.type=MLS simulation.flatcam=True recon.algo=tikhonov
```

Simulate FlatCam with PSF simulation:
```
python scripts/sim/ilo_single_file.py mask.type=MLS simulation.flatcam=False
```

Simulate Fresnel Zone Aperture camera with PSF simulation (https://www.nature.com/articles/s41377-020-0289-9):
```
python scripts/sim/ilo_single_file.py mask.type=FZA
```

Simulate PhaseContour camera with PSF simulation (https://ieeexplore.ieee.org/document/9076617):
```
python scripts/sim/ilo_single_file.py mask.type=PhaseContour
```

"""

import hydra
import warnings
from hydra.utils import to_absolute_path
from lensless.utils.io import load_psf  # , save_image
from lensless.utils.image import rgb2gray, rgb2bayer  # , align_face
from lensless.utils.align_face import align_face
import numpy as np
import matplotlib.pyplot as plt
from lensless.utils.plot import plot_image

# from lensless.eval.metric import mse, psnr, ssim, lpips
from waveprop.simulation import FarFieldSimulator
import os
from lensless.hardware.mask import CodedAperture, PhaseContour, FresnelZoneAperture


@hydra.main(version_base=None, config_path="../../configs", config_name="ilo_single_file")
def simulate(config):

    fp = to_absolute_path(config.files.original)
    assert os.path.exists(fp), f"File {fp} does not exist."

    # simulation parameters
    object_height = config.simulation.object_height
    scene2mask = config.simulation.scene2mask
    mask2sensor = config.simulation.mask2sensor
    sensor = config.simulation.sensor
    snr_db = config.simulation.snr_db
    downsample = config.simulation.downsample
    max_val = config.simulation.max_val

    image_format = config.simulation.image_format.lower()
    grayscale = False
    if image_format == "grayscale":
        grayscale = True

    # 1) simulate mask
    mask_type = config.mask.type
    if mask_type.upper() in ["MURA", "MLS"]:
        mask = CodedAperture.from_sensor(
            sensor_name=sensor,
            downsample=downsample,
            method=mask_type,
            distance_sensor=mask2sensor,
            **config.mask,
        )
        psf = mask.psf / np.linalg.norm(mask.psf.ravel())
    elif mask_type.upper() == "FZA":
        mask = FresnelZoneAperture.from_sensor(
            sensor_name=sensor,
            downsample=downsample,
            distance_sensor=mask2sensor,
            **config.mask,
        )
        psf = mask.psf / np.linalg.norm(mask.psf.ravel())
    elif mask_type == "PhaseContour":
        mask = PhaseContour.from_sensor(
            sensor_name=sensor,
            downsample=downsample,
            distance_sensor=mask2sensor,
            **config.mask,
        )
        psf = mask.psf / np.linalg.norm(mask.psf.ravel())
    else:
        psf_fp = to_absolute_path(config.files.psf)
        assert os.path.exists(psf_fp), f"PSF {psf_fp} does not exist."
        psf = load_psf(psf_fp, verbose=True, downsample=downsample)
        psf = psf.squeeze()

    if grayscale and psf.shape[-1] == 3:
        psf = rgb2gray(psf)
    if downsample > 1:
        print(f"Downsampled to {psf.shape}.")

    # 2) simulate measurement
    # image = load_image(fp, verbose=True)
    image = np.array(align_face(fp)) / 255
    if grayscale and len(image.shape) == 3:
        image = rgb2gray(image)

    flatcam_sim = config.simulation.flatcam
    if flatcam_sim and mask_type.upper() not in ["MURA", "MLS"]:
        warnings.warn(
            "Flatcam simulation only supported for MURA and MLS masks. Using far field simulation with PSF."
        )
        flatcam_sim = False

    # use far field simulator to get correct object plane sizing
    simulator = FarFieldSimulator(
        psf=psf,  # only support one depth plane
        object_height=object_height,
        scene2mask=scene2mask,
        mask2sensor=mask2sensor,
        sensor=sensor,
        snr_db=snr_db,
        max_val=max_val,
    )
    image_plane, object_plane = simulator.propagate(image, return_object_plane=True)

    if image_format == "grayscale":
        image_plane = rgb2gray(image_plane)
        object_plane = rgb2gray(object_plane)
    elif "bayer" in image_format:
        image_plane = rgb2bayer(image_plane, pattern=image_format[-4:])
        object_plane = rgb2bayer(object_plane, pattern=image_format[-4:])
    else:
        # make sure image is RGB
        assert image_plane.shape[-1] == 3, "Image plane must be RGB"
        assert object_plane.shape[-1] == 3, "Object plane must be RGB"

    if flatcam_sim:
        # apply flatcam simulation to object plane
        image_plane = mask.simulate(object_plane, snr_db=snr_db)

    # -- plot
    fig, ax = plt.subplots(ncols=3, nrows=1, figsize=(15, 5))
    plot_image(object_plane, ax=ax[0])
    ax[0].set_title("Object plane")
    plot_image(psf, ax=ax[1], gamma=3.5)
    ax[1].set_title("PSF")
    plot_image(image_plane, ax=ax[2])
    ax[2].set_title("Raw data")
    plt.savefig("result.png")
    fig.tight_layout()

    for a in ax:
        a.set_axis_off()

    plt.show()


if __name__ == "__main__":
    simulate()
