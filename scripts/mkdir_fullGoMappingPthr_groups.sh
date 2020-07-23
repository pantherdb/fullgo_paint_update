GROUPNUM=0
CURRENTSIZE=0
MAXSIZE=5000
CWD=$(pwd)
for f in $1/* ; do
    FILESIZE=$(stat -c%s "$f")
    FILESIZE=$(expr $FILESIZE / 1024 / 1024)
    CURRENTSIZE=$(expr $CURRENTSIZE + $FILESIZE)
    FBASENAME=$(basename $f)
    echo $f
    if [ $CURRENTSIZE -gt $MAXSIZE ]
    then
        # Primarily meant for goa_uniprot_all.gaf - Average line count is 700-800 mil
        echo "Splitting $FBASENAME"
        split --suffix-length=1 -d -l 300000000 $f $f.
        for split_f in $f.* ; do
            GROUPDIR=$1/group_$GROUPNUM
            mkdir -p $GROUPDIR
            
            FULL_FPATH=$(realpath $split_f)
            FBASENAME=$(basename $split_f)
            cd $GROUPDIR
            ln -s $FULL_FPATH $FBASENAME
            cd $CWD
            GROUPNUM=$(expr $GROUPNUM + 1)
        done

        CURRENTSIZE=0
    else
        GROUPDIR=$1/group_$GROUPNUM
        mkdir -p $GROUPDIR
        
        FULL_FPATH=$(realpath $f)
        cd $GROUPDIR
        ln -s $FULL_FPATH $FBASENAME
        cd $CWD
    fi
done