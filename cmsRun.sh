#!/bin/sh
#

jobcfg=$1
datafile=$2
SRM_OUTPUT_DIR=$3
SRM_OUTPUT_FILE="$SRM_OUTPUT_DIR/$datafile"
OSG_SETUP=/afs/hep.wisc.edu/cms/sw/osg/setup.sh

# special exit status to force job to leave the queue
FAIL_JOB=42

# core files have a nasty habit of filling up disks and causing trouble,
# so disable them.
ulimit -c 0

dashboard_completion() {
  export dboard_ExeExitCode=$1

  if [ "${FARMOUT_DASHBOARD_REPORTER}" != "" ]; then
      ${FARMOUT_DASHBOARD_REPORTER} completion
  fi
}

outputFileExists() {
  srm_fname="$1"

  info="`srm-get-metadata -retry_num=0 $srm_fname 2>/dev/null`"
  if [ "$?" != "0" ]; then
    return 1
  fi
  size_line="`echo \"$info\" | grep \"size :\"`"
  if [ "$?" != "0" ]; then
    return 1
  fi
  IFS=$' :\t'
  size="`echo \"$size_line\" | ( read label size; echo $size )`"
  unset IFS
  if [ "$size" != "0" ] && [ "$size" != "" ]; then
    return 0
  fi
  return 1
}

DoSrmcp() {
    src="$1"
    dest="$2"

    # The internal retries in srmcp are often useless, because a broken file
    # may be left behind (as of dCache 1.7.0-38), so further attempts to
    # copy the file will all fail with the error "file exists".  Therefore,
    # we have our own retry loop, including deletion of broken files.

    tries=0
    while [ "$tries" -lt 3 ]; do
      if [ "$tries" -gt 1 ]; then
        echo "Trying again at `date`: srmcp $src $dest"
      fi

      srmcp -debug=true -retry_num=0 "$src" "$dest"
      rc=$?

      if [ "$rc" = "0" ]; then
        return 0
      fi

      echo
      echo
      echo "srmcp exited with non-zero status $rc at `date`."
      echo "This happened when copying $src to $dest."
      echo

      if outputFileExists "$dest"; then
         echo "Cleaning up failed destination file $dest."
         srm-advisory-delete -debug=true -retry_num=0 "$dest"

         rc=$?
         if [ "$rc" != "0" ]; then
           echo "srm-advisory-delete failed with exit status $rc at `date`."
         fi
      fi

      tries=$(($tries+1))
    done

    echo "Giving up after $tries attempts to copy $src to $dest."
    return 1
}


if outputFileExists $SRM_OUTPUT_FILE; then
  echo "File already exists: $SRM_OUTPUT_FILE; exiting as though successful."
  exit 0
fi

if [ "${FARMOUT_DASHBOARD_REPORTER}" != "" ]; then
    ${FARMOUT_DASHBOARD_REPORTER} submission
    ${FARMOUT_DASHBOARD_REPORTER} execution
fi

start_time=`date "+%s"`

cmsRun $jobcfg
rc=$?

export dboard_ExeTime=$((`date "+%s"` -  $start_time))

if [ "$rc" != "0" ]; then
  echo "cmsRun exited with status $rc"
  if [ -f $datafile ]; then
    mv $datafile cmsRun_failed_$datafile
  fi

  dashboard_completion $rc

  # Do not try to run this job again.  Would be nice to detect transient
  # errors (e.g. dCache down) and retry in those cases.
  exit $FAIL_JOB
fi

if ! [ -f $datafile ]; then
  echo "cmsRun did not produce expected datafile $datafile"
  echo "ls -ltr"
  ls -ltr
  echo "End of ls output"
  exit $FAIL_JOB
fi

# load environment for using srmcp
source $OSG_SETUP

if ! DoSrmcp "file://localhost/`pwd`/$datafile" "$SRM_OUTPUT_FILE"; then
  dashboard_completion 60307
  exit 1
fi

rm $datafile

# Copy all other root files in the directory also

for file in `ls -1 *.root 2>/dev/null`; do
    if ! DoSrmcp file://localhost/`pwd`/$file $SRM_OUTPUT_DIR/$file; then
        dashboard_completion 60307
	exit 1
    fi
    rm $file
done

dashboard_completion 0

exit 0
