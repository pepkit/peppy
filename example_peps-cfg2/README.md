# example_peps

This repository contains examples of [Portable Encapsulated Projects](http://pepkit.github.io). Explore the examples interactively with `python` or `R`:


## Python

Your basic python workflow uses the [peppy](http://github.com/pepkit/peppy) package and starts out like this:

```{python}
import peppy
proj1 = peppy.Project("example_basic/project_config.yaml")
```
More detailed Python vignettes are available as part of the [documentation for the peppy package](https://peppy.readthedocs.io/en/latest/index.html).

## R

Your basic `R` workflow uses the [pepr](http://github.com/pepkit/pepr) package and starts like this:

```{r}
library('pepr')
p = pepr::Project("example_basic/project_config.yaml")
```

More detailed R vignettes are available as part of the [documentation for the pepr package](http://code.databio.org/pepr).

## Looper

These projects can also be run through any command-line tool (such as a pipeline) using [looper](https://github.com/pepkit/looper). To see a complete example of a PEP and a looper-compatible pipeline, visit the [hello looper repository](https://github.com/pepkit/hello_looper).
