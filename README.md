Pipelines
---------

These pipelines use `pypiper` (see the corresponding repository).

How to use
----------

1. Clone this repository.
2. Clone the `pypiper` repository.
3. Produce a config file (it just has a bunch of paths).
4. Go!
```
git clone git@github.com:ComputationalEpigenetics/pipelines.git
git clone git@github.com:ComputationalEpigenetics/pypiper.git
```

If you are just _using the pypiper pipeline_ in a project, and you are _not developing the pipeline_, you should treat these cloned repos as read-only, frozen code, which should reside in a shared project workspace. There should be only one clone for the project, to avoid running data under changing pipeline versions. In other words, the cloned `pipeline` and `pypiper` repositories *should not change*, and you should not pull any pipeline updates (unless you plan to re-run the whole thing). You could enforce this like so (?):

```
chmod -R 544 pypiper
chmod -R 544 pipelines
```

In short, *do not develop pipelines from an active, shared, project-specific clone*. If you want to make changes, consider the following:

Running pipelines
-----------------

`python ~/repo/pipelines/src_pipeline/project_sample_loop.py -c metadata/config.txt`


Developing pipelines
--------------------

If you plan to develop pipelines, either by contributing a new pipeline or making changes to an existing pipeline, you should think about things differently. Instead of a project-specific clone, you should just clone the repos to your personal space, where you do the development. Push changes from there. Use this personal repo to run any tests or whatever, but this _is not your final project-specific result_, which should all be run from a frozen clone of the pipeline.


Accessory scripts
-----------------

I created a folder called `/bin` where I am putting some small scripts that help with things like monitoring running pipelines, summarizing pipeline outputs, etc. I see this as a folder of __accessory scripts__, not needed by the pipelines. Any scripts used by the pipelines themselevs, on the other hand, can live with them for now.
