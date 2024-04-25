##---------备份运行目录----------##
now=`date "+%Y%m%d%H%M%S"`
finalname="${appType}-"$now
if [ ! -d ./backup ];then
mkdir ./backup &>/dev/null
fi

## 删除历史备份，保留最后5份
files=$(ls ./backup | sort -n)
count=$(ls ./backup | wc -l)
((count = count -5))
for file in $files
do
   if [ $count -gt 0 ]; then
        ((count--))
   else
        break
   fi
   rm -rf ./backup/$file
done

if [ -d ./${appType} ];then
cp -R ./${appType} ./backup/$finalname &>/dev/null
fi

rm -rf ${appType}
cp -a tmp/${appType} ./
chmod -R 755 ./${appType}