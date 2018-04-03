
Installing and Hello, World!
=====================================

Release versions are posted on the GitHub `peppy releases page <https://github.com/pepkit/peppy/releases>`_. You can install the latest release from pypi


.. code-block:: bash

	pip install --user peppy

or directly from GitHub using pip:

.. code-block:: bash

	pip install --user https://github.com/pepkit/peppy/zipball/master


Update pep with:

.. code-block:: bash

	pip install --user --upgrade peppy


Now, to test pep, let's grab an clone an example project that follows PEP format:

.. code-block:: bash

	git clone https://github.com/epigen/microtest.git



enter the following commands within a python interactive session:

.. code-block:: python

	import peppy

	my_project = peppy.Project("microtest/config/microtest_config.yaml")
	my_samples = my_project.samples


That's it! Now you can play around with project metadata from within python.
