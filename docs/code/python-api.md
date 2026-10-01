# Package `peppy` Documentation

## Package Overview

The `peppy` package provides a Python interface for working with Portable Encapsulated Projects (PEPs). A PEP is a standardized format for organizing metadata for biological samples and sample-intensive data.

### Key Features

- **Project Management**: Create and manage collections of samples with metadata
- **Sample Access**: Retrieve individual samples and their attributes
- **Amendments**: Activate different project configurations
- **Validation**: Validate projects against schemas

### Installation

```bash
pip install peppy
```

### Quick Example

```python
from peppy import Project

# Initialize with a project config file
prj = Project(cfg="ngs.yaml")

# Access samples
samples = prj.samples
```

## API Reference

### Project Class

The main class for working with PEPs:

::: peppy.Project
    options:
      docstring_style: google
      show_source: true
      show_signature: true
      merge_init_into_class: true

### Sample Class

::: peppy.Sample
    options:
      docstring_style: google
      show_source: true
      show_signature: true
      merge_init_into_class: true
