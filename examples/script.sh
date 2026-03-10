while :
do
    nice -n 19 python3.9 traderProEWArbitrum.py
    nice -n 19 python3.9 traderProEWBase.py
    nice -n 19 python3.9 traderProTVLWArbitrum.py
    nice -n 19 python3.9 traderProTVLWBase.py
    nice -n 19 python3.9 traderProLibertyEthereum.py
    sleep 14400
done
