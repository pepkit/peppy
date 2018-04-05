# Documentation readme

The best way to do the tutorials for python packages like this is to use Jupyter notebooks. We should produce such notebooks and stick them in the `example_peps`, but then also render them here. We can do that with the `nbsphinx` extension, which lets you render jupyter notebooks into the sphinx docs.

Then just stick those here in the `jupyter` subfolder under `source` and make sure to stick them in the `TOC`.

Sync with:

```
rsync ${CODEBASE}example_peps/*ipynb doc/source/jupyter/

```