# Run this script to build and deploy the mkdocs docs in /docs

JUPYTER_SOURCE="docs/jupyter_source"
JUPYTER_BUILD="docs/docs/jupyter_build"
AUTODOC_MODULES=("peppy")
AUTODOC_BUILD="docs/docs/autodoc_build"
USAGE_TEMPLATE=""
USAGE_CMDS=("")
RENDERED_DIR="$CODEBASE/code.databio.org/peppy"

# Build jupyter source documents into markdown
if [ ! -z "$JUPYTER_SOURCE" ]
then
  for NB in `ls "$JUPYTER_SOURCE"/*.ipynb`
  do
    jupyter nbconvert --to markdown "$NB" --output-dir "$JUPYTER_BUILD"
  done
else
  echo "No JUPYTER_SOURCE provided."
fi


# Build python autodocs into markdown
if [ ! -z "$AUTODOC_MODULES" ]
then
  for MODULE in $AUTODOC_MODULES
  do
    python $CODEBASE/gendocs.py $MODULE > $AUTODOC_BUILD/$MODULE.md
  done
else
  echo "No AUTODOC_MODULES provided."
fi


# Build an auto-usage page in markdown
if [ ! -z "$USAGE_CMDS" ]
then
  cp $USAGE_TEMPLATE usage_temp.md
  for cmd in "$USAGE_CMDS"; do
    echo $cmd
    echo -e "\n\`$cmd\`" >> usage_temp.md
    echo -e '```' >> usage_temp.md
    $cmd >> usage_temp.md 2>&1
    echo -e '```' >> usage_temp.md
  done
  mv usage_temp.md  docs/docs/usage.md
  cat docs/docs/usage.md
else
  echo "No USAGE_CMDS provided."
fi


# Render completed docs into output folder with `mkdocs`

mkdocs build -f docs/mkdocs.yml -d "$RENDERED_DIR"
