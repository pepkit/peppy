
Protocol mapping YAML
******************************************

The protocol mappings explains how looper should map from a sample protocol (like RNA-seq) to a particular pipeline (like rnaseq.py), or group of pipelines. Here's how to build a pipeline_interface YAML file:

- **Case 1:** one protocol maps to one pipeline. Example: ``RNA-seq: rnaseq.py``

Any samples that list "RNA-seq" under ``library`` will be run using the ``rnaseq.py`` pipeline. You can list as many library types as you like in the protocol mappings, mapping to as many pipelines as you provide in your pipelines repository.

Example ``protocol_mappings.yaml``:

.. code-block:: yaml

	RRBS: rrbs.py
	WGBS: wgbs.py
	EG: wgbs.py
	ATAC: atacseq.py
	ATAC-SEQ: atacseq.py
	CHIP: chipseq.py
	CHIP-SEQ: chipseq.py
	CHIPMENTATION: chipseq.py
	STARR: starrseq.py
	STARR-SEQ: starrseq.py


- **Case 2:** one protocol maps to multiple independent pipelines. Example: ``Drop-seq: quality_control.py, dropseq.py``

You can map multiple pipelines to a single protocol if you want samples of a type to kick off more than one pipeline run.

Example ``protocol_mappings.yaml``:

.. code-block:: yaml

	RRBS: rrbs.py
	WGBS: wgbs.py
	SMART:  >
	  rnaBitSeq.py -f,
	  rnaTopHat.py -f
	SMART-seq:  >
	  rnaBitSeq.py -f,
	  rnaTopHat.py -f


- **Case 3:** a protocol runs one pipeline which depends on another. Example: ``WGBSNM: first;second;third;(fourth, fifth)``

.. warning::
	This feature, pipeline dependency is not implemented yet. This documentation describes a protocol that may be implemented in the future, if it is necessary to have dependency among pipeline submissions.

The basic format for pipelines run simultaneously is: ``PROTOCOL: pipeline1 [, pipeline2, ...]``. Use semi-colons to indicate dependency.

Example ``protocol_mappings.yaml``:

.. code-block:: yaml

	RRBS: rrbs.py
	WGBS: wgbs.py
	WGBSQC: >
	  wgbs.py;
	  (nnm.py, pdr.py)