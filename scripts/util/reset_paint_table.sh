for var in "$@"
do
    # echo "$var"
    make reset_paint_table TABLE_NAME="$var"
done