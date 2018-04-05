
Installing and Hello, World!
=====================================

Installing
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


You can install the latest release from `pypi <https://pypi.python.org/pypi/peppy>`_ using ``pip``:

.. code-block:: bash

	pip install --user peppy


Update ``peppy`` with:

.. code-block:: bash

	pip install --user --upgrade peppy


Or install any release on the `GitHub peppy releases page <https://github.com/pepkit/peppy/releases>`_:

.. code-block:: bash

	pip install --user https://github.com/pepkit/peppy/zipball/master


Hello world!
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now, to test ``peppy``, let's grab an clone an example project that follows PEP format. We've produced a bunch of example PEPs in the `example_peps repository on GitHub <https://github.com/pepkit/example_peps>`_. Let's clone that repository:

.. code-block:: bash

	git clone https://github.com/pepkit/example_peps.git

Then, from within the ``example_peps`` folder, enter the following commands in a python interactive session:

.. code-block:: python

	import peppy

	proj1 = peppy.Project("example1/project_config.yaml")
	samp = proj1.samples
	# Find the input file for the first sample in the project
	samp[0].file


That's it! You've got ``peppy`` running on an example project. Now you can play around with project metadata from within python. This example and others are explored in more detail in the tutorials section.