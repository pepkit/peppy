# Example PEPs

This repository contains examples of **PEPs** (Portable Encapsulated Projects). Visit the [PEP2.0.0 specification webiste](http://pep.databio.org) to learn more about the PEP standard and features. Explore the examples interactively with `Python` or `R`:

## Index

Here is a list of PEPs included in this repository. All PEPs must adhere to the [PEP2.0.0 spec](http://pep.databio.org/en/latest/) (validate against [PEP2.0.0 schema](https://schema.databio.org/pep/2.0.0.yaml))

### General

These PEPs demonstrate the features described in the PEP2.0.0 framework and implemented in [`peppy`](http://github.com/pepkit/peppy) and [`pepr`](http://github.com/pepkit/pepr)

- [example_basic](example_basic): the simplest PEP, not using any `sample_modifiers` or `project_modifiers`
- [example_append](example_append): demonstrates `sample_modifiers.append` feature
- [example_remove](example_remove): demonstrates `sample_modifiers.remove` feature
- [example_duplicate](example_duplicate): demonstrates `sample_modifiers.duplicate` feature
- [example_derive](example_derive): demonstrates `sample_modifiers.derive` feature
- [example_imply](example_imply):  demonstrates `sample_modifiers.imply` feature
- [example_derive_imply](example_derive_imply): demonstrates the combination of `sample_modifiers.imply` and `sample_modifiers.derive` features
- [example_imports](example_imports):  demonstrates the `imports` feature
- example_amendments: demonstrates `project_modifiers.amend` feature
  - [example_amendments1](example_amendments1)
  - [example_amendments2](example_amendments2)
- example_subtable: demonstrates `sample_subtable` feature
  - [example_subtable1](example_subtable1)
  - [example_subtable2](example_subtable2)
  - [example_subtable3](example_subtable3)
  - [example_subtable4](example_subtable4)
  - [example_subtable5](example_subtable5)
  - [example_subtables](example_subtables)

### Specialized

These PEPs extend the PEP2.0.0 framework and may include additional fields used by other tools that build on [`peppy`](http://github.com/pepkit/peppy) or [`pepr`](http://github.com/pepkit/pepr)

- [example_piface](example_piface): defines `pipeline_interface` property for each sample, which is used by [`looper`]() - a pipeline submission engine
- example_BiocProject: defines a `bioconductor` section that is used by [`BiocProject`] to link PEPs with Bioconductor
  - [example_BiocProject](example_BiocProject)
  - [example_BiocProject_exceptions](example_BiocProject_exceptions)
  - [example_BiocProject_remote](example_BiocProject_remote)
---
## Read PEPs in Python

Your basic python workflow uses the [`peppy`](http://github.com/pepkit/peppy) package and starts out like this:

```python
import peppy
proj1 = peppy.Project("example_basic/project_config.yaml")
```
More detailed Python vignettes are available as part of the [documentation for the `peppy` package](http://peppy.databio.org/en/latest/).

## Read PEPs in R

Your basic `R` workflow uses the [`pepr`](http://github.com/pepkit/pepr) package and starts like this:

```r
library('pepr')
p = pepr::Project("example_basic/project_config.yaml")
```

More detailed R vignettes are available as part of the [documentation for the `pepr` package](http://code.databio.org/pepr).
