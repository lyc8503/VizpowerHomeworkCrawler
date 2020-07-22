import requests
import uuid
import sys
# 要安装 pycryptodome 库
from Crypto.Cipher import AES
import base64
import logging
import os
import re

# 调试时输出所有信息
logging.basicConfig(level=logging.DEBUG)

# 输入
prefix = input("Prefix (example: prefix for cc.kehou.com is cc): ")

# 获取相关地区配置
r = requests.post("https://" + prefix + ".kehou.com/app/config/mobileConfig.htm", verify=False)
logging.debug("Config got: " + str(r.json()))
region_config = r.json()

# 输入
account = input("User account: ")
password = input("Password: ")


mobile_url = region_config['mobileDomain']
exer_url = region_config['exerDomain']
# 随机生成用于标识身份的 meeting_id
meeting_id = str(uuid.uuid1()).upper()

logging.info("Logging in...")

# 密码使用 AES 加密
BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS)
cipher = AES.new("wgjdsfog123login".encode("utf-8"), AES.MODE_ECB)
password_encrypted = base64.b64encode(cipher.encrypt(pad(password).encode("utf-8"))).decode("utf-8")
logging.debug("Password encrypted: " + password_encrypted)

# 发送登陆请求
r = requests.post(mobile_url + "/app/login.htm", verify=False, headers={
    "Cake": "MEETING-ID=" + meeting_id + ";",
    "User-Agent": "netstudy_7740.0_2020041320_7410.0_1-device_iPhone 6_0_netstudy_phone"
}, data={
    "userDto.password": password_encrypted,
    "userDto.username": account,
    "verifyCode": "",
    "__data": "true"
})

logging.debug("Response: " + r.text)


if r.json()['status'] != "success":
    logging.critical("Failed to log in.")
    meeting_id = input("Try to enter the Meeting ID manually: ")

logging.info("** LOGIN SUCCESS **")
logging.info("Your MEETING_ID: " + meeting_id)

headers_with_cake = {
    "Cake": "MEETING-ID=" + meeting_id + ";userName=" + account + ";userType=0;",
    "User-Agent": "netstudy_7740.0_2020041320_7410.0_1-device_iPhone 6_0_netstudy_phone"
}

# 获取个人信息 + id
try:
    r = requests.post(mobile_url + "/app/index.htm", verify=False, headers=headers_with_cake)
    info = r.json()
    logging.debug(info)

    file_path = "./" + account + "_" + info['agency'] + "_" + info['user']['className'] + "_" + info['user']['realName'] + "/"
except Exception as e:
    logging.critical("Invalid login. " + str(e))
    meeting_id = input("Try to enter the Meeting ID manually: ")
    headers_with_cake = {
        "Cake": "MEETING-ID=" + meeting_id + ";userName=" + account + ";userType=0;",
        "User-Agent": "netstudy_7740.0_2020041320_7410.0_1-device_iPhone 6_0_netstudy_phone"
    }
    r = requests.post(mobile_url + "/app/index.htm", verify=False, headers=headers_with_cake)
    info = r.json()
    logging.debug(info)

    file_path = "./" + account + "_" + info['agency'] + "_" + info['user']['className'] + "_" + info['user']['realName'] + "/"


logging.info("文件储存路径: " + file_path)
os.mkdir(file_path)


all_homework = []

# 遍历获取所有作业(1代表未完成, 2代表已完成)
for hw_type in (1, 2):
    for hw_page in range(1, 10000000):
        r = requests.post(exer_url + "/pad/exer/student/myExer.htm", verify=False, headers=headers_with_cake, data={
            "__data": "true",
            "type": hw_type,
            "page.currentPage": hw_page
        })

        if len(r.json()['data']['exers']) == 0:
            logging.debug("finish.")
            break

        for homework in r.json()['data']['exers']:
            all_homework.append(homework)


logging.debug(all_homework)

# 创建文件夹并获取作业图片
for i in all_homework:
    try:
        logging.info("Getting... " + str(i))
        sub_name = i['subjectName'] + "_" + i['title']
        # 排除非法字符
        rstr = r'[\\/:*?"<>|\r\n]+'
        sub_name = re.sub(rstr, "_", sub_name)

        os.mkdir(file_path + sub_name)
        save_dir = file_path + sub_name + "/"

        with open(save_dir + "data.json", "w") as f:
            f.write(str(i))
            f.close()

        r = requests.post(exer_url + "/pad/exer/student/noCardDetail.htm", verify=False, headers=headers_with_cake, data={
            "__data": "true",
            "exerId": i['exerId']
        })

        detail_url = str(r.json()['data']['answerAreaUrl']).replace("userId=0", "userId=" + str(info['user']['id']))
        r = requests.post(detail_url, verify=False, headers=headers_with_cake)

        with open(save_dir + "index.html", "wb") as f:
            f.write(r.content)
            f.close()

        # 正则解析 html 中的图片链接
        for url in re.finditer("background-image:url([\\s\\S]*?);", r.text):
            real_url = "https:" + url.group()[21:-2]
            filename = re.search("/[0-9a-zA-Z\\-]+_[0-9a-zA-Z]+.[0-9a-zA-Z]+", real_url).group()[1:]

            if "." in filename:
                r = requests.get(real_url, verify=False)
                with open(save_dir + filename, "wb") as f:
                    f.write(r.content)
                    f.close()
    except Exception as e:
        logging.error("出现未知错误: " + str(e))


logging.info("done.")
