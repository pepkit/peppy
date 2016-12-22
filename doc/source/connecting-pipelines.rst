Connecting pipelines
=============================================

If you're a pipeline author, you can connect any pipeline to work with looper, giving you the power of all of looper's features on your project. To connect your pipeline, you will need two files:

1. **Protocol mappings** - a ``yaml`` file that maps sample **library** to one or more **pipeline scripts**.
2. **Pipeline interface** -  a ``yaml`` file telling ``Looper`` the arguments and resources required by each pipeline script.

Let's go through each one in detail:

.. include:: protocol-mapping.rst

.. include:: pipeline-interface.rst

