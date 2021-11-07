import os
import re
import time


import feedparser
import requests
import redis
import base64

requests.packages.urllib3.disable_warnings()

ok_code = [200, 201, 202, 203, 204, 205, 206]

r_host = 'redis-12906.c285.us-west-2-2.ec2.cloud.redislabs.com'
r_port = 12906
r_passwd = os.getenv('REDIS_PWD')



def write_log(content, level="INFO"):
    date_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
    update_log = f"[{date_str}] [{level}] {content}\n"
    print(update_log)



def get_subscribe_url():
    rss = feedparser.parse('http://feeds.feedburner.com/mattkaydiary/pZjG')
    entries = rss.get("entries")

    if not entries:
        write_log("更新失败！无法拉取原网站内容", "ERROR")
        return

    summary = entries[0].get("summary")
    if not summary:
        write_log("暂时没有可用的订阅更新", "WARN")
        return
    #v2ray_list = re.findall(r"v2ray\([\u4e00-\u9fa5]*\)：(.+?)</div>", summary)
    clash_list = re.findall(r"clash\([\u4e00-\u9fa5]*\)：(.+?)</div>", summary)

    # 获取普通订阅链接
    """
    if v2ray_list:
        v2ray_url = v2ray_list[-1].replace('amp;', '')
        v2ray_req = requests.request("GET", v2ray_url, verify=False)
        v2ray_code = v2ray_req.status_code
        if v2ray_code not in ok_code:
            write_log(f"获取 v2ray 订阅失败：{v2ray_url} - {v2ray_code}", "WARN")
        else:
            update_list.append(f"v2ray: {v2ray_code}")

            with open(dirs + '/v2ray.txt', 'w', encoding="utf-8") as f:
                f.write(v2ray_req.text)
    """
    # 获取clash订阅链接
    if clash_list:
        clash_url = clash_list[-1].replace('amp;', '')
        clash_req = requests.request("GET", clash_url, verify=False)

        clash_code = clash_req.status_code
        if clash_code not in ok_code:
            write_log(f"获取 clash 订阅失败：{clash_url} - {clash_code}", "WARN")
        else:
            clash_content = clash_req.content.decode("utf-8")
            clash_content = clash_content.replace('mattkaydiary.com|', "")
            str_clash_content = clash_content.encode('utf-8')
            byte_clash_content = base64.b64encode(str_clash_content)
            r = redis.StrictRedis(host=r_host,port=r_port,password=r_passwd, charset="utf-8", decode_responses=True)
            r.set('clash_byte', byte_clash_content)
            write_log(f"clash 已经更新", "INFO")

                
get_subscribe_url()
