Required Inputs
=============================================

You need 4 inputs to run looper:

1. **Sample annotation sheet** - a ``csv`` file with 1 row per sample
2. **Project config file** - a ``yaml`` file describing input and output file paths, compute settings, and other project settings
3. **Protocol mappings** - a ``yaml`` file that maps sample **library** to one or more **pipeline scripts**.
4. **Pipeline interface** -  a ``yaml`` file telling ``Looper`` the arguments and resources required by each pipeline script.


Let's go through each one in detail:


.. include:: sample-annotation-sheet.rst

.. include:: project-config.rst

.. include:: protocol-mapping.rst

.. include:: pipeline-interface.rst


