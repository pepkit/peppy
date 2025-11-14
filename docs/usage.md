# Usage reference

pephubclient is a command line tool that can be used to interact with the PEPhub API.
It can be used to create, update, delete PEPs in the PEPhub database.

Below are usage examples for the different commands that can be used with pephubclient.## `phc --help`
```console
                                                                                                                                                                                                                                        
 Usage: pephubclient [OPTIONS] COMMAND [ARGS]...                                                                                                                                                                                        
                                                                                                                                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --version             -v                                       App version                                                                                                                                                           │
│ --install-completion          [bash|zsh|fish|powershell|pwsh]  Install completion for the specified shell. [default: None]                                                                                                           │
│ --show-completion             [bash|zsh|fish|powershell|pwsh]  Show completion for the specified shell, to copy it or customize the installation. [default: None]                                                                    │
│ --help                                                         Show this message and exit.                                                                                                                                           │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ login                                  Login to PEPhub                                                                                                                                                                               │
│ logout                                 Logout                                                                                                                                                                                        │
│ pull                                   Download and save project locally.                                                                                                                                                            │
│ push                                   Upload/update project in PEPhub                                                                                                                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```

## `phc pull --help`
```console
                                                                                                                                                                                                                                        
 Usage: pephubclient pull [OPTIONS] PROJECT_REGISTRY_PATH                                                                                                                                                                               
                                                                                                                                                                                                                                        
 Download and save project locally.                                                                                                                                                                                                     
                                                                                                                                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    project_registry_path      TEXT  [default: None] [required]                                                                                                                                                                     │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --force     --no-force          Overwrite project if it exists. [default: no-force]                                                                                                                                                  │
│ --zip       --no-zip            Save project as zip file. [default: no-zip]                                                                                                                                                          │
│ --output                  TEXT  Output directory. [default: None]                                                                                                                                                                    │
│ --help                          Show this message and exit.                                                                                                                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```

## `phc push --help`
```console
                                                                                                                                                                                                                                        
 Usage: pephubclient push [OPTIONS] CFG                                                                                                                                                                                                 
                                                                                                                                                                                                                                        
 Upload/update project in PEPhub                                                                                                                                                                                                        
                                                                                                                                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    cfg      TEXT  Project config file (YAML) or sample table (CSV/TSV)with one row per sample to constitute project [default: None] [required]                                                                                     │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --namespace                        TEXT  Project namespace [default: None] [required]                                                                                                                                             │
│ *  --name                             TEXT  Project name [default: None] [required]                                                                                                                                                  │
│    --tag                              TEXT  Project tag [default: None]                                                                                                                                                              │
│    --force         --no-force               Force push to the database. Use it to update, or upload project. [default: no-force]                                                                                                     │
│    --is-private    --no-is-private          Upload project as private. [default: no-is-private]                                                                                                                                      │
│    --help                                   Show this message and exit.                                                                                                                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```

