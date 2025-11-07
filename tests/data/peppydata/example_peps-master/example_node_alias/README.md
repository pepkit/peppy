# YAML Aliases

You can also use YAML aliases in PEPs, since the config file is just a YAML file. These allow you to define variables within the YAML file, and then re-use these in other places in the file. Unfortunately, you can't import aliases across files (each file must contain its own definitions so it's self-sufficient as a YAML file).

To do it, just define a value as an anchor with the `&` character. Then, recall (duplicate) that value later with the `*` character. For example:

```
list:
- sandwich
- drink
- &thing chips
- crackers
- *thing
```

This will have `chips` twice in the list. In the first instance, we assigned it to `thing` with the `&thing` flag. Then, we repopulate `*thing` to chips.