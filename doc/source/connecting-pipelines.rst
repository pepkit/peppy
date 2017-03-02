Connecting pipelines
=============================================

.. HINT:: 

	Pipeline users don't need to worry about this section. This is for those who develop pipelines.

Looper can connect any pipeline, as long as it runs on the command line and uses text command-line arguments. These pipelines can be simple shell scripts, python scripts, perl scripts, or even pipelines built using a framework. Typically, we use python pipelines built using the `pypiper <https://databio.org/pypiper>`_ package, which provides some additional power to looper, but this is optional.

Regardless of what pipelines you use, you will need to tell looper how to interface with your pipeline. You do that by specifying a *pipeline interface*, which currently consists of two files:

1. **Protocol mappings** - a ``yaml`` file that maps sample **library** to one or more **pipeline scripts**.
2. **Pipeline interface** -  a ``yaml`` file telling ``Looper`` the arguments and resources required by each pipeline script.

Let's go through each one in detail:

.. include:: protocol-mappings.rst

.. include:: pipeline-interface.rst

