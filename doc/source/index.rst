
pipelines documentation
=========================

the ``pipelines`` repository provides three things:

- **pipelines:** Pipelines used in-house for processing of most common NGS data types.
- **Looper:** A program that manages the submission of a project's samples to the pipelines.
- **microtest data:** A set of small files of various NGS data types used for quickly testing the pipelines.

All pipelines use ``Pypiper`` to run. 

How to use
--------------------

You can try it out using the microtest example like this (the -d option indicates a dry run, meaning submit scripts are created but not actually submitted).

.. code-block:: bash

    ./pipelines/looper.py -c pipelines/examples/microtest_project_config.yaml -d


Option 1 (clone the repository)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Clone this repository.
Clone the pypiper repository.
Produce a config file (it just has a bunch of paths).
Go!

.. code-block:: bash

    git clone git@github.com:epigen/pipelines.git
    git clone git@github.com:epigen/pypiper.git

If you are just using the pypiper pipeline in a project, and you are not developing the pipeline, you should treat these cloned repos as read-only, frozen code, which should reside in a shared project workspace. There should be only one clone for the project, to avoid running data under changing pipeline versions. In other words, the cloned pipeline and pypiper repositories should not change, and you should not pull any pipeline updates (unless you plan to re-run the whole thing). You could enforce this like so (?):

.. code-block:: bash

    chmod -R 544 pypiper
    chmod -R 544 pipelines


In short, do not develop pipelines from an active, shared, project-specific clone.

Option 2 (install the packages)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

    pip install https://github.com/epigen/pipelines/zipball/master
    pip install https://github.com/epigen/pypiper/zipball/master

You will have all runnable pipelines and accessory scripts (from scripts/, see below) in your $PATH.

Running pipelines
We use the Looper (looper.py) to run pipelines. This just requires a config file passed as an argument, which contains all the settings required. It submits each job to SLURM.

.. code-block:: bash

    python ~/repo/pipelines/looper.py -c metadata/config.txt

or

.. code-block:: bash

    looper -c metadata/config.txt


Developing pipelines
--------------------

If you plan to develop pipelines, either by contributing a new pipeline or making changes to an existing pipeline, you should think about things differently. Instead of a project-specific clone, you should just clone the repos to your personal space, where you do the development. Push changes from there. Use this personal repo to run any tests or whatever, but this is not your final project-specific result, which should all be run from a frozen clone of the pipeline.


Source code
--------------------

Source code is at http://github.com/epigen/pipelines/ .


Contents
--------

.. toctree::
    :maxdepth: 3

    getting-started.rst
    sample-annotation-sheet.rst
    config-files.rst
    pipelines.rst
    post-run.rst
    the-inner-workings.rst
    api.rst


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
