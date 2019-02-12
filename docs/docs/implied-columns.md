# Implied columns

At some point, you may have a situation where you need a single sample attribute (or column) 
to populate several different pipeline arguments with different values. 
In other words, the value of a given attribute may *imply* values for other attributes. 
It would be nice if you didn't have to enumerate all of these secondary, implied attributes, 
and could instead just infer them from the value of the original attribute. 

For example, if my `organism` attribute is `human`, this implies a few other secondary attributes 
(which may be project-specific): For one project, I want to set `genome` to `hg38` and `macs_genome_size` to `hs`. 
Of course, I could just define columns called `genome` and `macs_genome_size`, but these would be constant across samples, so it feels inefficient and unwieldy. 
Plus, changing the aligned genome would require changing the sample annotation sheet (every sample, in fact). 
You can certainly do this with `looper`, but a better way is to handle these things at the project level.

As a more elegant alternative, in a project config file `looper` will recognize a section called `implied_columns`. 
Instead of hard-coding `genome` and `macs_genome_size` in the sample annotation sheet, 
you can simply specify that the attribute `organism` *implies* additional attribute-value pairs 
(which may vary by sample based on the value of the `organism` attribute). 
This lets you specify assemblies, genome size, and other similar variables all in your project config file.

To do this, just add an `implied_columns` section to your project_config.yaml file. Example:

```yaml
implied_columns:
  organism:
    human:
      genome: "hg38"
      macs_genome_size: "hs"
    mouse:
      genome: "mm10"
      macs_genome_size: "mm"
```

There are 3 levels in the `implied_columns` hierarchy. 
The first (directly under `implied_columns`; here, `organism`), are primary columns from which new attributes will be inferred. 
The second layer (here, `human` or `mouse`) are possible values your samples may take in the primary column. 
The third layer (`genome` and `macs_genome_size`) are the key-value pair of new, implied columns 
for any samples with the required value for that primary column. 

In this example, any samples with organism set to `"human"` will automatically also have attributes for `genome` (`"hg38"`) and for `macs_genome_size` (`"hs"`). 
Any samples with `organism` set to `"mouse"` will have the corresponding values. 
A sample with `organism` set to `"frog"` would lack attributes for `genome` and `macs_genome_size`, since those columns are not implied by `"frog"`.

This system essentially lets you set global, species-level attributes at the project level instead of duplicating 
that information for every sample that belongs to a species.
Even better, it's generic, so you can do this for any partition of samples (just replace `organism` with whatever you like). 

This makes your project more portable and does a better job conceptually with separating sample attributes from project attributes. 
After all, a reference assembly is not a property of a sample, but is part of the broader project context.
