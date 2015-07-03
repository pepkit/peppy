# Deletes all directories with a failed flag
ls -d */*failed*

read -p "Are you sure? " -n 1 -r
echo    # (optional) move to a new line
if [[ $REPLY =~ ^[Yy]$ ]]
then
    ls -d */*failed* | cut -d'/' -f1 | xargs rm -rfv
fi

