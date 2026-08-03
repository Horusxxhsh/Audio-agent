# Data metadata

This directory contains tracked metadata that describes local or external
evaluation data without placing it at the repository root.

- `guitar_solo_evaluation_metadata.csv` is the input metadata used by
  `Source/compute_fad.py`. The script now resolves this path from the repository
  root by default.

The CSV was moved without changing any field values. In particular, any
platform-specific audio paths inside it require a separate data-portability
audit before modification.
