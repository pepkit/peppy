
Protocol mapping YAML
******************************************

The protocol mappings explains how the Looper should map from a sample protocol (like RNA-seq) to a particular pipeline (like rnaseq.py), or group of pipelines.
You can map multiple pipelines to a single protocol if you want samples of a type to kick of more than one pipeline run

The basic format for pipelines run simultaneously is:
``PROTOCOL: pipeline1 [, pipeline2, ...]``

Use semi-colons to indicate dependency.

.. warning::
	Pipeline dependency is not implemented yet.

Rules:

- **Basic case:** one protocol maps to one pipeline: ``RNA-seq: rnaseq.py``
- **Case:** one protocol maps to multiple independent pipelines: ``Drop-seq: quality_control.py, dropseq.py``
- **Case:** a protocol runs one pipeline which depends on another: ``WGBSNM: first;second;third;(fourth, fifth)``


Examples:

.. code-block:: yaml

	RRBS: rrbs.py
	WGBS: wgbs.py
	EG: wgbs.py
	WGBSQC: >
	  wgbs.py;
	  (nnm.py, pdr.py)
	SMART:  >
	  rnaBitSeq.py -f;
	  rnaTopHat.py -f
	SMART-seq:  >
	  rnaBitSeq.py -f;
	  rnaTopHat.py -f
	ATAC: atacseq.py
	ATAC-SEQ: atacseq.py
	CHIP: chipseq.py
	CHIP-SEQ: chipseq.py
	CHIPMENTATION: chipseq.py
	STARR: starrseq.py
	STARR-SEQ: starrseq.py
