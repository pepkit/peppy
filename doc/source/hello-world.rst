
Installing and Hello, World!
=====================================

Release versions are posted on the GitHub `looper releases page <https://github.com/epigen/looper/releases>`_. You can install the latest release directly from GitHub using pip:

.. code-block:: bash

	pip install --user https://github.com/epigen/looper/zipball/master


Update looper with:

.. code-block:: bash

	pip install --user --upgrade https://github.com/epigen/looper/zipball/master


To put the ``looper`` executable in your ``$PATH``, add the following line to your ``.bashrc`` or ``.profile``:

.. code-block:: bash

	export PATH=~/.local/bin:$PATH


Now, to test looper, follow the commands in the `Hello, Looper! example repository <https://github.com/databio/hello_looper>`_. Details are located in the README file; Briefly, just run these 5 lines of code and you're running your first looper project!

.. code:: bash

	# Install the latest version of looper:
	pip install --user https://github.com/epigen/looper/zipball/master

	# download and unzip this repository
	wget https://github.com/databio/hello_looper/archive/master.zip
	unzip master.zip

	# Run it:
	cd hello_looper-master
	looper run project_config.yaml


.. HINT::

	If the looper executable isn't in your path, add it with ``export PATH=~/.local/bin:$PATH`` -- check out the :doc:`FAQ <faq>`.

Now just read the explanation in the `Hello, Looper! example repository <https://github.com/databio/hello_looper>`_ to understand what you've accomplished.