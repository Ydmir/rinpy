RinPy Repository
================

Python package for handling RINEX version 2.1x and 3.x, regardless of number of systems in the data.

Author:
`Joakim Strandberg <http://jstrandberg.se>`_

.. contents::

Installation
=============
::
  python setup.py develop

Usage
=====
RinPy can be use used to read data from a RINEX file and store it in numpy's compressed npz-format, or to load it directly into the workspace.

To load into memory and plot GPS SNR data for the L1 signal for satellite with PRN number 20:
```python
import rinpy
from matplotlib import pyplot as plt

systemdata, systemsatlists, prntoidx, obstypes, header, obstimes = rinpy.processrinexfile('GTGU2000.15o')
snr_idx = [idx for idx, type in enumerate(obstypes['G']) if 'S1' in type][0]

plt.plot(obstimes, systemdata['G'][:, prntoidx['G'][20], snr_idx])
plt.xlabel('Time'); plt.ylabel('SNR')
plt.show()
```

Saving to and loading from file:

To load into memory:
```python
import rinpy
rinpy.processrinexfile('GTGU2000.15o', 'GTGU2000.15o.npz')
systemdata, systemsatlists, prntoidx, obstypes, header, obstimes = rinpy.loadrinexfromnpz('GTGU2000.15o.npz')
```

Each of the outputs from `rinpy.processrinexfile` and `rinpy.loadrinexfromnpz` are dicts where the keys are the system letters used in the RINEX format, e.g.:
* **G** - for GPS
* **R** - for GLONASS
* **E** - for Galileo
* **S** - for SBAS
For example `obstypes['R']` gives a list of observables for the GLONASS system.

About
=====
The code in this package is part of a larger code written for analysing GNSS SNR data for GNSS reflectometry, and is part of the work made for the paper:
Strandberg, J., Hobiger, T. och Haas, R. (2016) Inverse modelling of GNSS multipath for sea level measurements - initial results.

License
-------
RinPy is licensed under the MIT license - see the LICENSE file.

