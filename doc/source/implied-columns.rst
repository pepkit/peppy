.. _advanced-implied-columns:

Implied columns
=============================================

At some point, you will have a situation where you need a single sample attribute (or column) to populate several different pipeline arguments. In other words, the value of a given attribute may **imply** values for other attributes. It would be nice if you didn't have to enumerate all of these secondary, implied attributes, and could instead just infer them from the value of the original attribute. For example, if my `organism` attribute is ``human``, I want to set an attribute ``genome`` to ``hg38`` **and** an attribute ``genome_size`` to `hs`. Looper lets you do this with a feature called ``implied columns``. Instead of hard-coding ``genome`` and ``macs_genome_size`` in the sample annotation sheet, you can simply specify that organism ``human`` implies such-and-such additional attribute-value pairs (and, perhaps, organism ``mouse`` implies others), all in your project configuration file.

To do this, just add an ``implied_columns`` section to your project_config.yaml file.
Example:

.. code-block:: yaml

  implied_columns:
    organism:
      human:
        genome: "hg38"
        macs_genome_size: "hs"
      mouse:
        genome: "mm10"
        macs_genome_size: "mm"

In this example, any samples with organism set to "human" will automatically also have attributes for genome (hg38) and for macs_genome_size (hs). Any samples with organism set to "mouse" will have the corresponding values.