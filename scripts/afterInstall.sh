rm -rf ./tmp

# chmod -R +x ./bin/*.sh

cw=`pwd`
mdps=${mce_sys_module_path}

cd $mdps
fls='dataframe_ex.py db_connect.py params_tree.py result_set.py'
for fl in $fls; do
  if [ -f "$fl" ]; then
    rm -rf $fl >/dev/null
  fi
done

cd $cw

