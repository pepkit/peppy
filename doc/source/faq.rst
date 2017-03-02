FAQ
=========================

- Why isn't the ``looper`` executable in my path?
	By default, Python packages are installed to ``~/.local/bin``. You can add this location to your path by appending it (``export PATH=$PATH:~/.local/bin``). See discussion about this issue here: https://github.com/epigen/looper/issues/8

- How can I run my jobs on a cluster?
	See :ref:`cluster resource managers <cluster-resource-managers>`.

- Which configuration file has which settings?
	Here's a list: :doc:`config files <config-files>`

- What's the difference between `looper` and `pypiper`?
	`Pypiper <http://pypiper.readthedocs.io/>`_ and `Looper <http://looper.readthedocs.io/>`_ work together as a comprehensive pipeline management system. `Pypiper <http://pypiper.readthedocs.io/>`_ builds individual, single-sample pipelines that can be run one sample at a time. `Looper <http://looper.readthedocs.io/>`_ then processes groups of samples, submitting appropriate pipelines to a cluster or server. The two projects are independent and can be used separately, but they are most powerful when combined.
