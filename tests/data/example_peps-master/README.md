# example_peps

This repository contains examples of **PEPs** (Portable Encapsulated Projects). Visit the [PEP2.0.0 specification webiste](http://pep.databio.org) to learn more about the PEP standard and features. Explore the examples interactively with `Python` or `R`:


## Python

Your basic python workflow uses the [`peppy`](http://github.com/pepkit/peppy) package and starts out like this:

```python
import peppy
proj1 = peppy.Project("example_basic/project_config.yaml")
```
More detailed Python vignettes are available as part of the [documentation for the `peppy` package](http://peppy.databio.org/en/latest/).

## R

Your basic `R` workflow uses the [`pepr`](http://github.com/pepkit/pepr) package and starts like this:

```r
library('pepr')
p = pepr::Project("example_basic/project_config.yaml")
```

More detailed R vignettes are available as part of the [documentation for the `pepr` package](http://code.databio.org/pepr).
