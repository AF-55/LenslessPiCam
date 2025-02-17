Dataset objects (for training and testing)
==========================================

The software below provides functionality (with PyTorch) to load
datasets for training and testing.

.. automodule:: lensless.utils.dataset

.. autoclass:: lensless.utils.dataset.DualDataset
    :members: _get_images_pair
    :special-members: __init__, __len__

.. autoclass:: lensless.utils.dataset.SimulatedFarFieldDataset
    :members:
    :special-members: __init__

.. autoclass:: lensless.utils.dataset.MeasuredDataset
    :members:
    :special-members: __init__

.. autoclass:: lensless.utils.dataset.MeasuredDatasetSimulatedOriginal
    :members:
    :special-members: __init__

.. autoclass:: lensless.utils.dataset.DiffuserCamTestDataset
    :members:
    :special-members: __init__
