while :
do
    nice -n 19 python3.9 traderProEWArbitrum.py
    nice -n 19 python3.9 traderProEWBase.py
    sleep 86400
done
