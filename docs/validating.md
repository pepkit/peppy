# How to validate a PEP

Starting with version `0.30.0`, peppy now includes a powerful validation framework. We provide a schema for the basic PEP specification, so you can validate that a PEP fills that spec. Then, you can also write an extended schema to validate a pep for a specific analysis. All of the PEP validation functionality is handled by a separate package called `eido`. You can read more in the eido documentation, including:

- How to validate a PEP against the generic PEP format
- How to validate a PEP against a custom schema
- How to write your own custom schema

See the [eido documentation](http://eido.databio.org/) for further detail.
