while :
do
    nice -n 19 python3.9 traderProTVLWArbitrum.py
    nice -n 19 python3.9 traderProTVLWBase.py
    sleep 86400
done
