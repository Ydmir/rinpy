=======
PyGnssr
=======

Purpose
=======
Read and store RINEX data for GNSSR-community and wider GNSS use.

Requirements
============
1. Fast.
2. Multi-GNSS support.
3. Adaptable. E.g options to read and store specific data (such as only SNR).

Bonus
=====
I.e. not required but good if they exist.
1. Language agnostic. Files usable not only in python.
2. RINEX3 support.


Functionality
=============
class RinexData
  init(options)
    Determine if all data is to be read, or just some types.

  read(rinexfilename, rinexversion)

  load(storagefilename)

  save(storagefilename)

  ...
  
