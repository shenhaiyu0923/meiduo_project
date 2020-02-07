
import requests
import pprint
def putong()  :  # 修改库存
    data ={
        "sku_id": "6428630",
        "change_amount": +1,#加减数量
        "operate_type": "fix_data",
        "comment": "test",
    }
    url ='http://api-t4.vova.com/v1/notify/changeStorage'
    r=requests.post(url,data=data)
    pprint.pprint(r.json())

putong()

def haiwaicang()  :  # 海外仓
    data ={
        "sku_id": "6428630",
        "change_amount": -2,#加减数量
        "operate_type": "fix_data",
        "comment": "test",
    }
    url ='http://api-t6.vova.com/v1/notify/changeFbvStorage'
    r=requests.post(url,data=data)
    pprint.pprint(r.json())
haiwaicang()
