import io
import shutil
import asyncio
from nonebot.adapters.onebot.v11 import Bot, MessageEvent, GroupMessageEvent, MessageSegment
from nonebot import require, on_command, logger
from nonebot.plugin import PluginMetadata
import nonebot
import os
import httpx
import requests
import re
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import json
import sqlite3
import random
import time
import toml

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler

plugin_version = "1.1.18"

def connect_api(
        type: str,
        url: str,
        post_json=None,
        file_path: str = None):
    logger.debug(f"connect_api请求URL：{url}")
    h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/118.0.0.0 Safari/537.36 Edg/118.0.2088.76"}
    if type == "json":
        if post_json is None:
            return json.loads(httpx.get(url, headers=h).text)
        else:
            return json.loads(httpx.post(url, json=post_json, headers=h).text)
    elif type == "image":
        if url is None or url in ["none", "None", "", " "]:
            image = draw_text("获取图片出错", 50, 10)
        else:
            try:
                image = Image.open(BytesIO(httpx.get(url).content))
            except Exception as e:
                image = draw_text("获取图片出错", 50, 10)
        return image
    elif type == "file":
        cache_file_path = file_path + "cache"
        f = open(cache_file_path, "wb")
        try:
            res = httpx.get(url, headers=h).content
            f.write(res)
            logger.debug(f"下载完成-{file_path}")
        except:
            raise Exception
        finally:
            f.close()
        shutil.copyfile(cache_file_path, file_path)
        os.remove(cache_file_path)
    return

config = nonebot.get_driver().config
# 读取配置
# -》无需修改代码文件，请在“.env”文件中改。《-
#
# 配置1：
# 管理员账号SUPERUSERS
# 需要添加管理员权限，参考如下：
# SUPERUSERS=["12345678"]
#
# 配置2：
# 文件存放目录
# 该目录是存放插件数据的目录，参考如下：
# bilipush_basepath="./"
# bilipush_basepath="C:/"
#
# 配置3：
# api地址
# 配置api地址，如未填写则使用默认地址，参考如下：
# bilipush_apiurl="http://cdn.kanon.ink"
#
# 配置4：
# 是否使用api来获取emoji图像
# 为True时使用api，为False时不使用api，为空时自动选择。
# bilipush_emojiapi=True
#
# 配置5：
# 刷新间隔
# 每次刷新间隔多少分钟，默认为12分钟。
# bilipush_waittime=12
#
# 配置6：
# 发送间隔
# 每次发送完成后等待的时间，单位秒，默认10-30秒。
# 时间为设置的时间再加上随机延迟10-20秒
# bilipush_sleeptime=10
#
# 配置7：
# 只响应一个bot
# 配置一个群中是否只响应1次
# 为True时只响应1个bot，默认为False
# bilipush_botswift=False
#
# 配置8：
# 读取自定义的命令前缀
# COMMAND_START=["/", ""]
#
# 配置9：
# 单次最大发送限制
# 限制单次发送消息的数量，减小风控概率
# 默认为5条，为0时不限制
# bilipush_maximum_send=5
#
# 配置10：
# DebugLog
#
# 配置11：
# 推送样式配置
# bilipush_push_style="[绘图][标题][链接][内容][图片]"
#

# 配置1：
try:
    adminqq = config.superusers
    adminqq = list(adminqq)
except Exception as e:
    adminqq = []
# 配置2：
try:
    basepath = config.bilipush_basepath
    if "\\" in basepath:
        basepath = basepath.replace("\\", "/")
    if basepath.startswith("./"):
        basepath = os.path.abspath('.') + "/" + basepath.removeprefix(".")
        if not basepath.endswith("/"):
            basepath += "/"
    else:
        basepath += "/"
except Exception as e:
    basepath = os.path.abspath('.') + "/"
# 配置3：
try:
    apiurl = config.bilipush_apiurl
except Exception as e:
    apiurl = "http://cdn.kanon.ink"
# 配置4：
try:
    use_api = config.bilipush_emojiapi
except Exception as e:
    try:
        get_url = apiurl + "/json/config?name=ping"
        return_json = connect_api("json", get_url)
        if return_json["code"] == 0:
            use_api = True
        else:
            use_api = False
    except Exception as e:
        use_api = False
# 配置5：
try:
    waittime = str(config.bilipush_waittime)
except Exception as e:
    waittime = "12"
# 配置6：
try:
    sleeptime = int(config.bilipush_sleeptime)
except Exception as e:
    sleeptime = 10
# 配置7：
try:
    config_botswift = config.bilipush_botswift
except Exception as e:
    config_botswift = False
# 配置8：
try:
    command_starts = config.COMMAND_START
except Exception as e:
    command_starts = ["/"]
# 配置9：
try:
    maximum_send = config.bilipush_maximum_send
    if maximum_send == 0:
        maximum_send = 99
except Exception as e:
    maximum_send = 5
# 配置10：
try:
    beta_test = config.bilipush_beta_test
except Exception as e:
    beta_test = False
# 配置11：
try:
    push_style = config.bilipush_push_style
    if push_style == "":
        push_style = "[绘图][标题][链接]"
except Exception as e:
    push_style = "[绘图][标题][链接]"
pilipala = "nonebot_plugin_bili_push"[17:19]  # Very使得代码狂跑good
pilipala += "bili_push"[0:2]


# 插件元信息
__plugin_meta__ = PluginMetadata(
    name="bili_push",
    description="推送b站动态",
    usage="/添加订阅/删除订阅/查看订阅/最新动态",
    type="application",
    # 发布必填，当前有效类型有：`library`（为其他插件编写提供功能），`application`（向机器人用户提供功能）。
    homepage="https://github.com/SuperGuGuGu/nonebot_plugin_bili_push",
    supported_adapters={"~onebot.v11"},
    # 支持的适配器集合，其中 `~` 在此处代表前缀 `nonebot.adapters.`，其余适配器亦按此格式填写。
    # 若插件可以保证兼容所有适配器（即仅使用基本适配器功能）可不填写，否则应该列出插件支持的适配器。
)

# 创建基础参数
returnpath = ""
if not os.path.exists(f"{basepath}db/bili_push/"):
    os.makedirs(f"{basepath}db/bili_push/")
livedb = f"{basepath}db/bili_push/bili_push.db"
heartdb = f"{basepath}db/bili_push/heart.db"


def plugin_config(config_name: str, groupcode: str):
    """
    读取群配置，如不存在则读取全局配置
    config[groupcode][config_name] = config_data
    :param config_name: 获取的配置名称
    :param groupcode: 所在群号
    :return: 配置内容
    """
    path = f"{basepath}db/bili_push/group_config.toml"

    # 保存配置
    def save_config():
        with open(path, 'w', encoding="utf-8") as config_file:
            toml.dump(config, config_file)

    # 如不存在配置文件，则新建一个
    if not os.path.exists(path):
        config = {"Group_Config":
                      {"nonebot_plugin_bili_push": "https://github.com/SuperGuGuGu/nonebot_plugin_bili_push"}
                  }
        save_config()
        logger.debug("未存在群配置文件，正在创建")

    # 读取配置
    config = toml.load(path)

    if groupcode in list(config):
        if config_name in list(config[groupcode]):
            group_config_data = config[groupcode][config_name]
        else:
            group_config_data = None
    else:
        group_config_data = None

    if config_name == "admin":
        if group_config_data is None:
            config_data = adminqq
        elif "gp" not in groupcode:
            config_data = group_config_data
            for qq in adminqq:
                config_data.appeng(qq)
        else:
            config_data = adminqq

    elif config_name == "bilipush_botswift":
        if group_config_data is not None:
            config_data = group_config_data
        else:
            config_data = config_botswift

    elif config_name == "group_command_starts":
        if group_config_data is not None:
            config_data = group_config_data
        else:
            config_data = command_starts

    elif config_name == "bilipush_push_style":
        if group_config_data is not None:
            config_data = group_config_data
        else:
            config_data = push_style

    elif config_name == "at_all":
        if group_config_data is not None:
            config_data = group_config_data
        else:
            config_data = False

    elif config_name == "ignore_live_list":
        if group_config_data is not None:
            config_data = group_config_data
        else:
            config_data = []

    elif config_name == "ignore_dynamic_list":
        if group_config_data is not None:
            config_data = group_config_data
        else:
            config_data = []

    elif config_name == "none":
        config_data = None
    elif config_name == "none":
        config_data = None
    elif config_name == "none":
        config_data = None
    elif config_name == "none":
        config_data = None
    else:
        config_data = None

    return config_data


def get_file_path(file_name):
    """
    获取文件的路径信息，如果没下载就下载下来
    :param file_name: 文件名。例：“file.zip”
    :return: 文件路径。例："c:/bot/cache/file/file.zip"
    """
    file_path = basepath + "cache/file/"
    if not os.path.exists(file_path):
        os.makedirs(file_path)
    file_path += file_name
    if not os.path.exists(file_path):
        # 如果文件未缓存，则缓存下来
        logger.debug("正在下载" + file_name)
        if use_api is True:
            url = apiurl + "/file/" + file_name
        else:
            if file_name == "NotoSansSC[wght].ttf":
                url = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosanssc/NotoSansSC%5Bwght%5D.ttf"
            elif file_name == "":
                url = ""
            else:
                url = ""
        connect_api(type="file", url=url, file_path=file_path)
    return file_path


def draw_text(texts: str,
              size: int,
              textlen: int = 20,
              fontfile: str = "",
              text_color="#000000",
              bili_emoji_infos=None,
              bili_at_infos=None,
              calculate=False
              ):
    """
    - 文字转图片

    :param texts: 输入的字符串
    :param size: 文字尺寸
    :param textlen: 一行的文字数量
    :param fontfile: 字体文字
    :param text_color: 字体颜色，例："#FFFFFF"、(10, 10, 10)
    :param bili_emoji_infos: bili的表情
    :param bili_at_infos: bili的at文字信息，显示蓝色
    :param calculate: 计算长度。True时只返回空白图，不用粘贴文字，加快速度。

    :return: 图片文件（RGBA）
    """

    if bili_at_infos is None:
        bili_at_infos = []
    else:
        bili_at_infos = json.loads(bili_at_infos)

    def get_font_render_w(text):
        if text == " ":
            return 20
        none = ["\n", ""]
        if text in none:
            return 1
        canvas = Image.new('RGB', (500, 500))
        draw = ImageDraw.Draw(canvas)
        draw.text((0, 0), text, font=font, fill=(255, 255, 255))
        bbox = canvas.getbbox()
        # 宽高
        # size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
        if bbox is None:
            return 0
        return bbox[2]

    def get_emoji(emoji):
        cachepath = basepath + "cache/emoji/"
        if not os.path.exists(cachepath):
            os.makedirs(cachepath)
        cachepath = cachepath + emoji + ".png"
        if not os.path.exists(cachepath):
            if use_api is True:
                url = apiurl + "/api/emoji?imageid=" + emoji
                try:
                    return_image = connect_api("image", url)
                    return_image.save(cachepath)
                except Exception as e:
                    logger.warning("api出错，请联系开发者")
                    # api出错时直接打印文字
                    return_image = Image.new("RGBA", (100, 100), color=(0, 0, 0, 0))
                    draw = ImageDraw.Draw(return_image)
                    draw.text((0, 0), emoji, fill="#000000", font=font)
                    return_image.paste(return_image, (0, 0), mask=return_image)
            else:
                # 不使用api，直接打印文字
                return_image = Image.new("RGBA", (100, 100), color=(0, 0, 0, 0))
                draw = ImageDraw.Draw(return_image)
                draw.text((0, 0), emoji, fill="#000000", font=font)
                return_image.paste(return_image, (0, 0), mask=return_image)
        else:
            return_image = Image.open(cachepath, mode="r")
        return return_image

    def is_emoji(emoji):
        if use_api is not True:
            return False
        try:
            conn = sqlite3.connect(get_file_path("emoji_1.db"))
            cursor = conn.cursor()
            cursor.execute('select * from emoji where emoji = "' + emoji + '"')
            data = cursor.fetchone()
            cursor.close()
            conn.close()
            if data is not None:
                return True
            else:
                return False
        except Exception as e:
            return False

    fortsize = size
    if use_api is True:
        if fontfile == "":
            fontfile = get_file_path("腾祥嘉丽中圆.ttf")
    else:
        fontfile = get_file_path("NotoSansSC[wght].ttf")
    font = ImageFont.truetype(font=fontfile, size=fortsize)

    # 计算图片尺寸
    print_x = 0
    print_y = 0
    jump_num = 0
    text_num = -1
    for text in texts:
        text_num += 1
        if jump_num > 0:
            jump_num -= 1
        else:
            if (textlen * fortsize) < print_x or text == "\n":
                print_x = 0
                print_y += 1.3 * fortsize
                if text == "\n":
                    continue
            biliemoji_name = None
            if bili_emoji_infos is not None:
                # 检测biliemoji
                if text == "[":
                    emoji_len = 0
                    while emoji_len < 50:
                        emoji_len += 1
                        emoji_end = text_num + emoji_len
                        if texts[emoji_end] == "[":
                            # 不是bili emoji，跳过
                            emoji_len = 60
                        elif texts[emoji_end] == "]":
                            biliemoji_name = texts[text_num:emoji_end + 1]
                            jump_num = emoji_len
                            emoji_len = 60
            if biliemoji_name is not None:
                for biliemoji_info in bili_emoji_infos:
                    emoji_name = biliemoji_info["emoji_name"]
                    if emoji_name == biliemoji_name:
                        print_x += fortsize
            else:
                if is_emoji(text):
                    print_x += fortsize
                elif text in ["\n", " "]:
                    if text == " ":
                        print_x += get_font_render_w(text) + 2
                else:
                    print_x += get_font_render_w(text) + 2

    x = int((textlen + 1.5) * size)
    y = int(print_y + 1.2 * size)

    image = Image.new("RGBA", size=(x, y), color=(0, 0, 0, 0))  # 生成透明图片
    draw_image = ImageDraw.Draw(image)

    # 绘制文字
    if calculate is False:
        print_x = 0
        print_y = 0
        jump_num = 0
        text_num = -1
        for text in texts:
            text_num += 1
            if jump_num > 0:
                jump_num -= 1
            else:
                if (textlen * fortsize) < print_x or text == "\n":
                    print_x = 0
                    print_y += 1.3 * fortsize
                    if text == "\n":
                        continue
                biliemoji_name = None
                if bili_emoji_infos is not None:
                    # 检测biliemoji
                    if text == "[":
                        emoji_len = 0
                        while emoji_len < 50:
                            emoji_len += 1
                            emoji_end = text_num + emoji_len
                            if texts[emoji_end] == "[":
                                # 不是bili emoji，跳过
                                emoji_len = 60
                            elif texts[emoji_end] == "]":
                                biliemoji_name = texts[text_num:emoji_end + 1]
                                jump_num = emoji_len
                                emoji_len = 60
                if biliemoji_name is not None:
                    for biliemoji_info in bili_emoji_infos:
                        emoji_name = biliemoji_info["emoji_name"]
                        if emoji_name == biliemoji_name:
                            emoji_url = biliemoji_info["url"]
                            try:
                                paste_image = connect_api("image", emoji_url)
                            except Exception as e:
                                paste_image = draw_text("获取图片出错", 50, 10)
                                logger.error(f"获取图片出错:{e}")
                            paste_image = paste_image.resize((int(fortsize * 1.2), int(fortsize * 1.2)))
                            image.paste(paste_image, (int(print_x), int(print_y)))
                            print_x += fortsize
                else:
                    if is_emoji(text):
                        paste_image = get_emoji(text)
                        paste_image = paste_image.resize((int(fortsize * 1.1), int(fortsize * 1.1)))
                        image.paste(paste_image, (int(print_x), int(print_y)), mask=paste_image)
                        print_x += fortsize
                    elif text in ["\n", " "]:
                        if text == " ":
                            print_x += get_font_render_w(text) + 2
                    else:
                        draw_at = False
                        for bili_at_info in bili_at_infos:
                            if bili_at_info["location"] <= text_num < (
                                    bili_at_info["location"] + bili_at_info["length"]):
                                draw_at = True
                                break
                        draw_image.text(xy=(int(print_x), int(print_y)),
                                        text=text,
                                        fill=text_color if draw_at is False else "#00aeec",
                                        font=font)
                        print_x += get_font_render_w(text) + 2
        # 把输出的图片裁剪为只有内容的部分
        bbox = image.getbbox()
        if bbox is None:
            box_image = Image.new("RGBA", (2, fortsize), (0, 0, 0, 0))
        else:
            box_image = Image.new("RGBA", (bbox[2] - bbox[0], bbox[3] - bbox[1]), (0, 0, 0, 0))
            box_image.paste(image, (0 - int(bbox[0]), 0 - int(bbox[1])), mask=image)
        image = box_image
    return image


def circle_corner(img, radii):
    """
    圆角处理
    :param img: 源图象。
    :param radii: 半径，如：30。
    :return: 返回一个圆角处理后的图象。
    """

    # 画圆（用于分离4个角）
    circle = Image.new('L', (radii * 2, radii * 2), 0)  # 创建一个黑色背景的画布
    draw = ImageDraw.Draw(circle)
    draw.ellipse((0, 0, radii * 2, radii * 2), fill=255)  # 画白色圆形

    # 原图
    img = img.convert("RGBA")
    w, h = img.size

    # 画4个角（将整圆分离为4个部分）
    alpha = Image.new('L', img.size, 255)
    alpha.paste(circle.crop((0, 0, radii, radii)), (0, 0))  # 左上角
    alpha.paste(circle.crop((radii, 0, radii * 2, radii)), (w - radii, 0))  # 右上角
    alpha.paste(circle.crop((radii, radii, radii * 2, radii * 2)), (w - radii, h - radii))  # 右下角
    alpha.paste(circle.crop((0, radii, radii, radii * 2)), (0, h - radii))  # 左下角
    # alpha.show()

    img.putalpha(alpha)  # 白色区域透明可见，黑色区域不可见
    return img


def new_background(image_x: int, image_y: int):
    """
    创建背景图
    :param image_x: 背景图宽 int
    :param image_y: 背景图长 int
    :return: 返回一张背景图 image

    """
    image_x = int(image_x)
    image_y = int(image_y)

    # 创建 背景_背景
    new_image = Image.new(mode='RGB', size=(image_x, image_y), color="#d7f2ff")

    # 创建 背景_描边
    image_x -= 56
    image_y -= 56
    image_paste = Image.new(mode='RGB', size=(image_x, image_y), color="#86d6ff")
    image_paste = circle_corner(image_paste, radii=25)
    paste_x = int(int(new_image.width - image_paste.width) / 2)
    paste_y = int(int(new_image.height - image_paste.height) / 2)
    new_image.paste(image_paste, (paste_x, paste_y), mask=image_paste)

    # 创建 背景_底色
    image_x -= 3
    image_y -= 3
    image_paste = Image.new(mode='RGB', size=(image_x, image_y), color="#eaf6fc")
    image_paste = circle_corner(image_paste, radii=25)
    paste_x = int(int(new_image.width - image_paste.width) / 2)
    paste_y = int(int(new_image.height - image_paste.height) / 2)
    new_image.paste(image_paste, (paste_x, paste_y), mask=image_paste)

    return new_image


def get_draw(data, only_info: bool = False):
    """
    绘制动态的主要函数
    :param data: 动态的json数据
    :param only_info: 只绘制对应的up信息，用于关注的时候确认是否输错UID
    :return: {
        "code": 状态，如果是0则为出错，正常为2,
        "draw_path": 绘制的动态存放路径,
        "message_title": 动态的类型,
        "message_url": 动态的UID,
        "message_body": 动态的内容,
        "message_images": 动态包含的图片
        }
    """

    def image_resize2(image, size: [int, int], overturn=False):
        """
        图像重缩放
        :param image: 要缩放的图像
        :param size: 缩放后的大小
        :param overturn: 如果是，图像放大覆盖缩放后尺寸，并裁剪两边或下边。否则缩小至可以放在缩放后的尺寸内
        :return: image
        """
        image_background = Image.new("RGBA", size=size, color=(0, 0, 0, 0))
        image_background = image_background.resize(size)
        w, h = image_background.size
        x, y = image.size
        if overturn:
            if w / h >= x / y:
                rex = w
                rey = int(rex * y / x)
                paste_image = image.resize((rex, rey))
                image_background.paste(paste_image, (0, 0))
            else:
                rey = h
                rex = int(rey * x / y)
                paste_image = image.resize((rex, rey))
                printx = int((w - rex) / 2)
                image_background.paste(paste_image, (printx, 0))
        else:
            if w / h >= x / y:
                rey = h
                rex = int(rey * x / y)
                paste_image = image.resize((rex, rey))
                printx = int((w - rex) / 2)
                printy = 0
                image_background.paste(paste_image, (printx, printy))
            else:
                rex = w
                rey = int(rex * y / x)
                paste_image = image.resize((rex, rey))
                printx = 0
                printy = int((h - rey) / 2)
                image_background.paste(paste_image, (printx, printy))

        return image_background

    date = str(time.strftime("%Y-%m-%d", time.localtime()))
    date_year = str(time.strftime("%Y", time.localtime()))
    date_month = str(time.strftime("%m", time.localtime()))
    date_day = str(time.strftime("%d", time.localtime()))
    timenow = str(time.strftime("%H-%M-%S", time.localtime()))

    cachepath = basepath + f"cache/draw/{date_year}/{date_month}/{date_day}/"
    if not os.path.exists(cachepath):
        os.makedirs(cachepath)
    addimage = ""
    run = True  # 代码折叠助手
    code = 0
    returnpath = ""
    dynamicid = str(data["desc"]["dynamic_id"])
    logger.debug(f"bili-push_draw_开始获取数据-{dynamicid}")
    uid = str(data["desc"]["uid"])
    biliname = str(data["desc"]["user_profile"]["info"]["uname"])
    biliface = str(data["desc"]["user_profile"]["info"]["face"])
    pendant = str(data["desc"]["user_profile"]["pendant"]["image"])
    dynamicid = str(data["desc"]["dynamic_id"])
    timestamp = str(data["desc"]["timestamp"])
    timestamp = int(timestamp)
    timestamp = time.localtime(timestamp)
    timestamp = time.strftime("%Y年%m月%d日 %H:%M:%S", timestamp)
    bilitype = data["desc"]["type"]
    bilidata = data["card"]
    bilidata = json.loads(bilidata)
    try:
        emoji_infos = data["display"]["emoji_info"]["emoji_details"]
    except Exception as e:
        emoji_infos = []
    fortsize = 30

    if use_api is True:
        fontfile = get_file_path("腾祥嘉丽中圆.ttf")
    else:
        fontfile = get_file_path("NotoSansSC[wght].ttf")
    font = ImageFont.truetype(font=fontfile, size=fortsize)

    try:
        # 初始化文字版动态
        message_title = ""
        message_body = ""
        message_url = "t.bi"  # Very Cool
        message_url += f"{pilipala}li.com/{dynamicid}"
        message_images = []

        # 绘制基础信息
        def draw_info():
            vipStatus = data["desc"]["user_profile"]["vip"]["vipStatus"]

            def draw_decorate_card():
                decorate_card = data["desc"]["user_profile"]["decorate_card"]["card_url"]
                card_type = data["desc"]["user_profile"]["decorate_card"]["card_type"]
                is_fan = data["desc"]["user_profile"]["decorate_card"]["fan"]["is_fan"]
                fan_number = data["desc"]["user_profile"]["decorate_card"]["fan"]["number"]
                fan_color = data["desc"]["user_profile"]["decorate_card"]["fan"]["color"]
                image = connect_api("image", decorate_card)
                w, h = image.size
                y = 87
                x = int(y * w / h)
                image = image.resize((x, y))
                if is_fan == 1:
                    draw = ImageDraw.Draw(image)
                    cache_fortsize = 36

                    if use_api is True:
                        fontfile = get_file_path("farout2.ttf")
                    else:
                        fontfile = get_file_path("NotoSansSC[wght].ttf")
                    font = ImageFont.truetype(font=fontfile, size=fortsize)

                    fan_number = str(fan_number)
                    while len(fan_number) < 6:
                        fan_number = "0" + fan_number
                    draw.text(xy=(90, 25), text=fan_number, fill=fan_color, font=font)
                else:
                    paste_image = image
                    image = Image.new("RGBA", (x + 50, y), (0, 0, 0, 0))
                    image.paste(paste_image, (50, 0), mask=paste_image)
                return image

            # 绘制头像名称等信息
            image = Image.new("RGBA", (900, 230), (0, 0, 0, 0))
            draw = ImageDraw.Draw(image)
            x = 74
            y = 76

            # 开始往图片添加内容
            # 添加头像底图
            imageround = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
            imageround = circle_corner(imageround, 100)
            imageround = imageround.resize((129, 129))
            image.paste(imageround, (73, 73), mask=imageround)
            # 添加头像
            if pendant == "":
                image_face = connect_api("image", biliface)
                image_face = image_face.resize((125, 125))
                imageround = imageround.resize((125, 125))
                image.paste(image_face, (75, 75), mask=imageround)

            # 添加装饰圈
            if pendant != "":
                image_face = connect_api("image", biliface)
                image_face = image_face.resize((96, 96))
                imageround = imageround.resize((96, 96))
                image.paste(image_face, (87, 91), mask=imageround)

                paste_image = connect_api("image", pendant)
                paste_image = paste_image.resize((175, 175))
                image.paste(paste_image, (46, 51), mask=paste_image)

            # 添加大会员标志
            if vipStatus:
                file_path = get_file_path("bili-vip-icon.png")
                paste_image = Image.open(file_path)
                paste_image = paste_image.resize((50, 50))
                imageround = imageround.resize((50, 50))
                image.paste(paste_image, (150, 150), mask=imageround)

            # 添加动态卡片
            if "decorate_card" in list(data["desc"]["user_profile"]):
                paste_image = draw_decorate_card()
                image.paste(paste_image, (580, 78), mask=paste_image)

            # 添加名字
            cache_font = ImageFont.truetype(font=fontfile, size=35)
            if vipStatus:
                fill = (255, 85, 140)
            else:
                fill = (0, 0, 0)
            draw.text(xy=(228, 90), text=biliname, fill=fill, font=cache_font)

            # 添加日期
            draw.text(xy=(230, 145), text=timestamp, fill=(100, 100, 100), font=font)

            return image

        # 绘制话题标签
        def draw_topic():

            paste_image = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
            return paste_image

        # ### 绘制动态 #####################
        # 绘制名片
        if only_info:
            try:
                brief_introduction = biliname = data["desc"]["card"]["official_verify"]["desc"]
            except Exception as e:
                brief_introduction = uid

            fortsize = 30
            font = ImageFont.truetype(font=fontfile, size=fortsize)

            draw_image = new_background(900, 400)
            draw = ImageDraw.Draw(draw_image)
            # 开始往图片添加内容
            # 添加用户信息
            image_info = draw_info()
            draw_image.paste(image_info, (0, 0), mask=image_info)

            # 添加简介
            x = 75
            y = 230
            paste_image = draw_text(brief_introduction,
                                    size=30,
                                    textlen=24)
            draw_image.paste(paste_image, (x, y), mask=paste_image)

            returnpath = cachepath + 'bili动态/'
            if not os.path.exists(returnpath):
                os.makedirs(returnpath)
            returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
            draw_image.save(returnpath)
            logger.debug("bili-push_draw_绘图成功")
            code = 2

        # 转发动态
        elif bilitype == 1:
            card_message = bilidata["item"]["content"]
            origin_type = bilidata["item"]["orig_type"]
            at_infos = bilidata["item"]["ctrl"] if "ctrl" in bilidata["item"] else None
            try:
                origin_emoji_infos = data["display"]["origin"]["emoji_info"]["emoji_details"]
            except Exception as e:
                origin_emoji_infos = []

            # 投稿视频
            if origin_type == 8:
                origin_biliname = bilidata["origin_user"]["info"]["uname"]
                origin_biliface = bilidata["origin_user"]["info"]["face"]
                origin_data = bilidata["origin"]
                origin_data = json.loads(origin_data)
                origin_timestamp = origin_data["ctime"]
                origin_timestamp = time.localtime(origin_timestamp)
                origin_timestamp = time.strftime("%Y年%m月%d日 %H:%M:%S", origin_timestamp)
                origin_title = origin_data["title"]
                origin_message = origin_data["desc"]
                origin_video_image = origin_data["pic"]
                logger.debug("bili-push_draw_18_开始拼接文字")
                if run:
                    message_title = biliname + "转发了视频"
                    message_body = card_message + "\n转发视频：\n" + origin_title + "\n" + origin_message
                    if len(message_body) > 80:
                        message_body = message_body[0:79] + "…"
                    message_images.append(origin_data["pic"])
                logger.debug("bili-push_draw_18_开始绘图")
                if run:
                    image_x = 900
                    image_y = 140  # add base y
                    image_y += 125 + 35  # add hear and space
                    # 添加文字长度
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    image_y += h
                    # 添加转发内容
                    origin_len_y = 120 + 90
                    # 添加转发的视频长度
                    origin_len_y += 220 + 20
                    # 将转发长度添加到总长度中
                    image_y += origin_len_y

                    # 开始绘制图像
                    image_x = int(image_x)
                    image_y = int(image_y)
                    draw_image = new_background(image_x, image_y)
                    draw = ImageDraw.Draw(draw_image)
                    # 开始往图片添加内容
                    # 添加用户信息
                    image_info = draw_info()
                    draw_image.paste(image_info, (0, 0), mask=image_info)
                    # 添加动态内容
                    x = 75
                    y = 230
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            bili_at_infos=at_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    w, h = paste_image.size
                    y += h + 20
                    x = 65
                    # 添加转发内容
                    # 添加转发消息框
                    paste_image = Image.new("RGB", (776, origin_len_y + 4), "#FFFFFF")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x - 2, y - 2), mask=paste_image)

                    # 添加转发消息底图
                    paste_image = Image.new("RGB", (772, origin_len_y), "#f8fbfd")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    # 添加转发头像
                    image_face = connect_api("image", origin_biliface)
                    image_face = image_face.resize((110, 110))
                    imageround = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
                    imageround = circle_corner(imageround, 100)
                    imageround = imageround.resize((114, 114))
                    draw_image.paste(imageround, (x + 48, y + 48), mask=imageround)
                    imageround = imageround.resize((110, 110))
                    draw_image.paste(image_face, (x + 50, y + 50), mask=imageround)

                    # 添加名字
                    cache_font = ImageFont.truetype(font=fontfile, size=30)
                    draw.text(xy=(x + 190, y + 70), text=origin_biliname, fill=(0, 0, 0), font=cache_font)

                    # 添加日期
                    cache_font = ImageFont.truetype(font=fontfile, size=26)
                    draw.text(xy=(x + 190, y + 120), text=origin_timestamp, fill=(100, 100, 100), font=cache_font)

                    # 添加转发的内容
                    x += 20
                    y += 190

                    # 添加视频框
                    paste_image = Image.new("RGB", (730, 220), "#FFFFFF")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    # 添加视频图像
                    paste_image = connect_api("image", origin_video_image)
                    paste_image = paste_image.resize((346, 216))
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x + 2, y + 2), mask=paste_image)
                    # 添加视频标题
                    x += 366
                    y += 20
                    if len(origin_title) >= 24:
                        origin_title = origin_title[0:23] + "……"
                    paste_image = draw_text(origin_title,
                                            size=27,
                                            textlen=12,
                                            bili_emoji_infos=emoji_infos)
                    draw_image.paste(paste_image, (x + 2, y + 2), mask=paste_image)

                    # 添加视频简介
                    y += 70
                    if len(origin_message) >= 42:
                        origin_message = origin_message[0:41] + "……"
                    paste_image = draw_text(origin_message,
                                            size=25,
                                            textlen=13,
                                            bili_emoji_infos=emoji_infos,
                                            text_color="#606060")
                    draw_image.paste(paste_image, (x + 2, y + 2), mask=paste_image)

                    returnpath = cachepath + 'bili动态/'
                    if not os.path.exists(returnpath):
                        os.makedirs(returnpath)
                    returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                    draw_image.save(returnpath)
                    logger.debug("bili-push_draw_绘图成功")
                    code = 2

            # 图文动态
            elif origin_type == 2:
                origin_biliname = bilidata["origin_user"]["info"]["uname"]
                origin_biliface = bilidata["origin_user"]["info"]["face"]
                origin_data = bilidata["origin"]
                origin_data = json.loads(origin_data)
                origin_timestamp = origin_data["item"]["upload_time"]
                origin_timestamp = time.localtime(origin_timestamp)
                origin_timestamp = time.strftime("%Y年%m月%d日 %H:%M:%S", origin_timestamp)
                origin_message = origin_data["item"]["description"]
                origin_images = origin_data["item"]["pictures"]
                images = []
                for origin_image in origin_images:
                    image_url = origin_image["img_src"]
                    images.append(image_url)
                try:
                    emoji_infos = data["display"]["emoji_info"]["emoji_details"]
                except Exception as e:
                    emoji_infos = []
                logger.debug("bili-push_draw_12_开始拼接文字")
                if run:
                    message_title = biliname + "转发了动态"
                    message_body = card_message + "\n转发动态：\n" + origin_data["item"]["description"]
                    if len(message_body) > 80:
                        message_body = message_body[0:79] + "…"
                    origin_images = origin_data["item"]["pictures"]
                    for origin_image in origin_images:
                        message_images.append(origin_image["img_src"])
                logger.debug("bili-push_draw_12_开始绘图")
                if run:
                    fortsize = 30
                    font = ImageFont.truetype(font=fontfile, size=fortsize)

                    image_x = 900
                    image_y = 140  # add base y
                    image_y += 125 + 65  # add hear and space
                    # 添加文字长度
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    image_y += h
                    # 添加转发内容
                    origin_len_y = 120 + 60
                    # 添加转发内容
                    paste_image = draw_text(origin_message,
                                            size=27,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    origin_len_y += h

                    # 添加图片长度
                    imagelen = len(images)
                    if imagelen == 1:
                        # 单图，宽718
                        addimage = connect_api("image", images[0])
                        w, h = addimage.size
                        if h / w >= 1.8:
                            x = 718
                            y = int(718 * h / w)
                            addimage = addimage.resize((x, y))
                            w = 718
                            h = 1292  # int(w * 1.8)
                        elif h / w <= 0.5:
                            y = 359
                            x = int(359 / h * w)
                            addimage = addimage.resize((x, y))
                            w = 718
                            h = 359
                        else:
                            y = int(718 * h / w)
                            x = 718
                            h = y
                            addimage = addimage.resize((x, y))
                        origin_len_y += h
                    elif imagelen == 2:
                        # 2图，图大小356
                        origin_len_y += 356 + 10
                    elif imagelen <= 4:
                        # 4图，图大小356
                        origin_len_y += 718 + 10
                    # elif imagelen <= 6:
                    else:
                        # 6图，图大小245
                        origin_len_y += 10
                    cache_imagelen = imagelen
                    while cache_imagelen >= 1:
                        cache_imagelen -= 3
                        origin_len_y += 235 + 5

                    origin_len_y = int(origin_len_y)
                    # 将转发长度添加到总长度中
                    image_y += origin_len_y

                    image_x = int(image_x)
                    image_y = int(image_y)
                    draw_image = new_background(image_x, image_y)
                    draw = ImageDraw.Draw(draw_image)

                    # 添加用户信息
                    image_info = draw_info()
                    draw_image.paste(image_info, (0, 0), mask=image_info)

                    # 添加动态内容
                    x = 75
                    y = 230
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            bili_at_infos=at_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    w, h = paste_image.size
                    y += h + 20
                    x = 65
                    # 添加转发内容
                    # 添加转发消息框
                    paste_image = Image.new("RGB", (776, origin_len_y + 4), "#FFFFFF")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x - 2, y - 2), mask=paste_image)

                    # 添加转发消息底图
                    paste_image = Image.new("RGB", (772, origin_len_y), "#f8fbfd")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    # 添加转发头像
                    image_face = connect_api("image", origin_biliface)
                    image_face = image_face.resize((110, 110))
                    imageround = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
                    imageround = circle_corner(imageround, 100)
                    imageround = imageround.resize((114, 114))
                    draw_image.paste(imageround, (x + 48, y + 48), mask=imageround)
                    imageround = imageround.resize((110, 110))
                    draw_image.paste(image_face, (x + 50, y + 50), mask=imageround)

                    # 添加名字
                    cache_font = ImageFont.truetype(font=fontfile, size=30)
                    draw.text(xy=(x + 190, y + 70), text=origin_biliname, fill=(0, 0, 0), font=cache_font)

                    # 添加日期
                    cache_font = ImageFont.truetype(font=fontfile, size=26)
                    draw.text(xy=(x + 190, y + 120), text=origin_timestamp, fill=(100, 100, 100), font=cache_font)

                    # 添加转发的内容
                    x += 35
                    y += 190
                    paste_image = draw_text(origin_message,
                                            size=28,
                                            textlen=22,
                                            bili_emoji_infos=emoji_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    w, h = paste_image.size
                    x -= 10
                    y += h

                    print_y = y
                    print_x = x

                    # 添加图片
                    if imagelen == 1:
                        paste_image = addimage
                        paste_image = circle_corner(paste_image, 15)
                        draw_image.paste(paste_image, (x, y), mask=paste_image)
                    elif imagelen <= 4:
                        # 2图，图大小356
                        print_y = 0
                        print_x = -1
                        for image in images:
                            print_x += 1
                            if print_x >= 2:
                                print_x = 0
                                print_y += 1
                            paste_image = connect_api("image", image)
                            paste_image = image_resize2(image=paste_image, size=(356, 356),
                                                        overturn=True)
                            paste_image = circle_corner(paste_image, 15)
                            draw_image.paste(paste_image, (int(x + print_x * (356 + 5)), int(y + print_y * (356 + 5))),
                                             mask=paste_image)
                    else:
                        # 6图，图大小235
                        image_y += 707 + 15
                        num = -1
                        for image in images:
                            num += 1
                            if num >= 3:
                                num = 0
                                print_x = x
                                print_y += 235 + 5
                            paste_image = connect_api("image", image)
                            paste_image = image_resize2(image=paste_image, size=(235, 235), overturn=True)
                            paste_image = circle_corner(paste_image, 15)
                            draw_image.paste(paste_image, (int(print_x), int(print_y)), mask=paste_image)
                            print_x += 235 + 5

                    returnpath = cachepath + 'bili动态/'
                    if not os.path.exists(returnpath):
                        os.makedirs(returnpath)
                    returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                    draw_image.save(returnpath)
                    logger.debug("bili-push_draw_绘图成功")
                    code = 2

            # 文字动态
            elif origin_type == 4:
                origin_biliname = bilidata["origin_user"]["info"]["uname"]
                origin_biliface = bilidata["origin_user"]["info"]["face"]
                origin_data = bilidata["origin"]
                origin_data = json.loads(origin_data)
                origin_timestamp = origin_data["item"]["timestamp"]
                origin_timestamp = time.localtime(origin_timestamp)
                origin_timestamp = time.strftime("%Y年%m月%d日 %H:%M:%S", origin_timestamp)
                origin_message = origin_data["item"]["content"]
                logger.debug("bili-push_draw_14_开始拼接文字")
                if run:
                    message_title = biliname + "转发了动态"
                    message_body = card_message + "\n转发动态：\n" + origin_data["item"]["content"]
                    if len(message_body) > 80:
                        message_body = message_body[0:79] + "…"
                logger.debug("bili-push_draw_14_开始绘图")
                if run:
                    image_x = 900
                    image_y = 140  # add base y
                    image_y += 125 + 35  # add hear and space
                    # 添加文字长度
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    image_y += h
                    # 添加转发内容
                    origin_len_y = 120 + 90
                    # add message
                    paste_image = draw_text(origin_message,
                                            size=27,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    origin_len_y += h
                    # 将转发长度添加到总长度中
                    image_y += origin_len_y

                    image_x = int(image_x)
                    image_y = int(image_y)
                    draw_image = new_background(image_x, image_y)
                    draw = ImageDraw.Draw(draw_image)
                    # 开始往图片添加内容
                    # 添加用户信息
                    image_info = draw_info()
                    draw_image.paste(image_info, (0, 0), mask=image_info)
                    # 添加动态内容
                    x = 75
                    y = 230
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            bili_at_infos=at_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    w, h = paste_image.size

                    y = y + h + 20
                    x = 65
                    # 添加转发内容
                    # 添加转发消息框
                    paste_image = Image.new("RGB", (776, origin_len_y + 4), "#FFFFFF")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x - 2, y - 2), mask=paste_image)

                    # 添加转发消息底图
                    paste_image = Image.new("RGB", (772, origin_len_y), "#f8fbfd")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    # 添加转发头像
                    image_face = connect_api("image", origin_biliface)
                    image_face = image_face.resize((110, 110))
                    imageround = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
                    imageround = circle_corner(imageround, 100)
                    imageround = imageround.resize((114, 114))
                    draw_image.paste(imageround, (x + 48, y + 48), mask=imageround)
                    imageround = imageround.resize((110, 110))
                    draw_image.paste(image_face, (x + 50, y + 50), mask=imageround)

                    # 添加名字
                    cache_font = ImageFont.truetype(font=fontfile, size=30)
                    draw.text(xy=(x + 190, y + 70), text=origin_biliname, fill=(0, 0, 0), font=cache_font)

                    # 添加日期
                    cache_font = ImageFont.truetype(font=fontfile, size=26)
                    draw.text(xy=(x + 190, y + 120), text=origin_timestamp, fill=(100, 100, 100), font=cache_font)

                    # 添加转发的内容
                    x = x + 75
                    y = y + 190
                    paste_image = draw_text(origin_message,
                                            size=28,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    returnpath = cachepath + 'bili动态/'
                    if not os.path.exists(returnpath):
                        os.makedirs(returnpath)
                    returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                    draw_image.save(returnpath)
                    logger.debug("bili-push_draw_绘图成功")
                    code = 2

            # 文章动态
            elif origin_type == 64:
                origin_biliname = bilidata["origin_user"]["info"]["uname"]
                origin_biliface = bilidata["origin_user"]["info"]["face"]
                origin_data = bilidata["origin"]
                origin_data = json.loads(origin_data)
                origin_timestamp = origin_data["publish_time"]
                origin_timestamp = time.localtime(origin_timestamp)
                origin_timestamp = time.strftime("%Y年%m月%d日 %H:%M:%S", origin_timestamp)
                origin_title = origin_data["title"]
                origin_message = origin_data["summary"]
                origin_image = origin_data["image_urls"][0]
                logger.debug("bili-push_开始拼接文字")
                if run:
                    message_title = biliname + "转发了文章"
                    message_body = card_message + "\n转发文章：\n" + origin_data["title"] + "\n" + origin_message
                    if len(message_body) > 80:
                        message_body = message_body[0:79] + "…"
                logger.debug("bili-push_开始绘图")
                if run:
                    image_x = 900
                    image_y = 140  # add base y
                    image_y += 125 + 35  # add hear and space
                    # 添加文字长度
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    image_y += h
                    # 添加转发内容
                    origin_len_y = 120 + 90
                    # 添加转发的文章长度
                    origin_len_y += 350 + 20
                    # 将转发长度添加到总长度中
                    image_y += origin_len_y

                    # 开始绘制图像
                    image_x = int(image_x)
                    image_y = int(image_y)
                    draw_image = new_background(image_x, image_y)
                    draw = ImageDraw.Draw(draw_image)
                    # 开始往图片添加内容
                    # 添加用户信息
                    image_info = draw_info()
                    draw_image.paste(image_info, (0, 0), mask=image_info)
                    # 添加动态内容
                    x = 75
                    y = 230
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            bili_at_infos=at_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    w, h = paste_image.size
                    y += h + 20
                    x = 65
                    # 添加转发内容
                    # 添加转发消息框
                    paste_image = Image.new("RGB", (776, origin_len_y + 4), "#FFFFFF")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x - 2, y - 2), mask=paste_image)

                    # 添加转发消息底图
                    paste_image = Image.new("RGB", (772, origin_len_y), "#f8fbfd")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    # 添加转发头像
                    image_face = connect_api("image", origin_biliface)
                    image_face = image_face.resize((110, 110))
                    imageround = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
                    imageround = circle_corner(imageround, 100)
                    imageround = imageround.resize((114, 114))
                    draw_image.paste(imageround, (x + 48, y + 48), mask=imageround)
                    imageround = imageround.resize((110, 110))
                    draw_image.paste(image_face, (x + 50, y + 50), mask=imageround)

                    # 添加名字
                    cache_font = ImageFont.truetype(font=fontfile, size=30)
                    draw.text(xy=(x + 190, y + 70), text=origin_biliname, fill=(0, 0, 0), font=cache_font)

                    # 添加日期
                    cache_font = ImageFont.truetype(font=fontfile, size=26)
                    draw.text(xy=(x + 190, y + 120), text=origin_timestamp, fill=(100, 100, 100), font=cache_font)

                    # 添加转发的内容
                    x += 20
                    y += 190

                    # 添加文章框
                    paste_image = Image.new("RGB", (730, 350), "#FFFFFF")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    # 添加文章图像
                    paste_image = connect_api("image", origin_image)
                    paste_image = paste_image.resize((726, 216))
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x + 2, y + 2), mask=paste_image)
                    # 添加文章标题
                    y += 220

                    if len(origin_title) > 25:
                        origin_title = origin_title[0:24] + "……"
                    paste_image = draw_text(origin_title,
                                            size=35,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    # 添加文章简介
                    y += 45
                    if len(origin_message) > 70:
                        origin_message = origin_message[0:69] + "……"
                    paste_image = draw_text(origin_message,
                                            size=27,
                                            textlen=23,
                                            bili_emoji_infos=emoji_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    returnpath = cachepath + 'bili动态/'
                    if not os.path.exists(returnpath):
                        os.makedirs(returnpath)
                    returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                    draw_image.save(returnpath)
                    logger.debug("bili-push_绘图成功")
                    code = 2

            # 已下播的直播间动态
            elif origin_type == 1024:
                origin_message = "直播已结束"
                logger.debug("bili-push_开始拼接文字")
                if run:
                    message_title = biliname + "转发了直播"
                    message_body = card_message + "\n转发直播：\n" + origin_message
                    if len(message_body) > 80:
                        message_body = message_body[0:79] + "…"
                logger.debug("bili-push_开始绘图")
                if run:
                    image_x = 900
                    image_y = 140  # add base y
                    image_y += 125 + 35  # add hear and space
                    # 添加文字长度
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    image_y += h
                    # 添加转发内容
                    origin_len_y = 90
                    # add message
                    paste_image = draw_text(origin_message,
                                            size=27,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    origin_len_y += h
                    # 将转发长度添加到总长度中
                    image_y += origin_len_y

                    image_x = int(image_x)
                    image_y = int(image_y)
                    draw_image = new_background(image_x, image_y)
                    draw = ImageDraw.Draw(draw_image)
                    # 开始往图片添加内容
                    # 添加用户信息
                    image_info = draw_info()
                    draw_image.paste(image_info, (0, 0), mask=image_info)
                    # 添加动态内容
                    x = 75
                    y = 230
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            bili_at_infos=at_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    w, h = paste_image.size

                    y = y + h + 20
                    x = 65
                    # 添加转发内容
                    # 添加转发消息框
                    paste_image = Image.new("RGB", (776, origin_len_y + 4), "#FFFFFF")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x - 2, y - 2), mask=paste_image)

                    # 添加转发消息底图
                    paste_image = Image.new("RGB", (772, origin_len_y), "#f8fbfd")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    # 添加转发的内容
                    x += 40
                    y += 40
                    paste_image = draw_text(origin_message,
                                            size=28,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    returnpath = cachepath + 'bili动态/'
                    if not os.path.exists(returnpath):
                        os.makedirs(returnpath)
                    returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                    draw_image.save(returnpath)
                    logger.debug("bili-push_绘图成功")
                    code = 2

            # 正在直播的直播间动态
            elif origin_type == 4308:
                origin_biliname = bilidata["origin_user"]["info"]["uname"]
                origin_biliface = bilidata["origin_user"]["info"]["face"]
                origin_data = bilidata["origin"]
                origin_data = json.loads(origin_data)
                origin_title = origin_data["live_play_info"]["title"]
                origin_image = origin_data["live_play_info"]["cover"]
                logger.debug("bili-push_开始拼接文字")
                if run:
                    message_title = biliname + "转发了直播"
                    message_body = card_message + "\n转发直播：\n" + origin_title
                    if len(message_body) > 80:
                        message_body = message_body[0:79] + "…"
                logger.debug("bili-push_开始绘图")
                if run:
                    image_x = 900
                    image_y = 140  # add base y
                    image_y += 125 + 35  # add hear and space
                    # 添加文字长度
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    image_y += h
                    # 添加转发内容
                    origin_len_y = 403 + 90
                    # 添加内容长度
                    paste_image = draw_text(origin_title,
                                            size=27,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            calculate=True)
                    w, h = paste_image.size
                    origin_len_y += h
                    # 将转发长度添加到总长度中
                    image_y += origin_len_y

                    image_x = int(image_x)
                    image_y = int(image_y)
                    draw_image = new_background(image_x, image_y)
                    draw = ImageDraw.Draw(draw_image)
                    # 开始往图片添加内容
                    # 添加用户信息
                    image_info = draw_info()
                    draw_image.paste(image_info, (0, 0), mask=image_info)
                    # 添加动态内容
                    x = 75
                    y = 230
                    paste_image = draw_text(card_message,
                                            size=30,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos,
                                            bili_at_infos=at_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)
                    w, h = paste_image.size

                    y = y + h + 20
                    x = 65
                    # 添加转发内容
                    # 添加转发消息框
                    paste_image = Image.new("RGB", (776, origin_len_y + 4), "#FFFFFF")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x - 2, y - 2), mask=paste_image)

                    # 添加转发消息底图
                    paste_image = Image.new("RGB", (772, origin_len_y), "#f8fbfd")
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    # 添加直播封面
                    paste_image = connect_api("image", origin_image)
                    paste_image = paste_image.resize((718, 403))
                    paste_image = circle_corner(paste_image, 15)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    # 添加转发的内容
                    x += 20
                    y += 430
                    paste_image = draw_text(origin_title,
                                            size=28,
                                            textlen=24,
                                            bili_emoji_infos=emoji_infos)
                    draw_image.paste(paste_image, (x, y), mask=paste_image)

                    returnpath = cachepath + 'bili动态/'
                    if not os.path.exists(returnpath):
                        os.makedirs(returnpath)
                    returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                    draw_image.save(returnpath)
                    logger.debug("bili-push_绘图成功")
                    code = 2

        # 图文动态
        elif bilitype == 2:
            card_message = bilidata["item"]["description"]
            card_images = bilidata["item"]["pictures"]
            at_infos = bilidata["item"]["at_control"] if "at_control" in bilidata["item"] else None
            images = []
            for card_image in card_images:
                image_url = card_image["img_src"]
                images.append(image_url)
            try:
                emoji_infos = data["display"]["emoji_info"]["emoji_details"]
            except Exception as e:
                emoji_infos = []
            logger.debug("bili-push_开始拼接文字")
            if run:
                message_title = biliname + "发布了动态"
                message_body = card_message
                if len(message_body) > 80:
                    message_body = message_body[0:79] + "……"
                message_images = images
            logger.debug("bili-push_开始绘图")
            if run:  # 代码折叠
                # 计算图片长度
                image_x = 900
                image_y = 140  # add base y
                image_y += 125 + 35  # add hear and space
                # 添加文字长度
                paste_image = draw_text(card_message,
                                        size=30,
                                        textlen=24,
                                        bili_emoji_infos=emoji_infos,
                                        calculate=True)
                w, h = paste_image.size
                image_y += h
                # 添加图片长度
                imagelen = len(images)
                if imagelen == 1:
                    addimage = connect_api("image", images[0])
                    w, h = addimage.size
                    if h / w >= 1.8:
                        x = 770
                        y = int(770 * h / w)
                        addimage = addimage.resize((x, y))
                        w = 770
                        h = int(w * 1.8)
                        addimage = image_resize2(addimage, (w, h), overturn=True)
                    elif h / w <= 0.5:
                        y = 385
                        x = int(385 / h * w)
                        addimage = addimage.resize((x, y))
                        w = 770
                        h = 385
                        addimage = image_resize2(addimage, (w, h), overturn=True)
                    else:
                        y = int(770 * h / w)
                        x = 770
                        addimage = addimage.resize((x, y))
                        addimage = image_resize2(addimage, (x, y), overturn=True)
                        h = y
                    image_y += h
                elif imagelen == 2:
                    # 2图，图大小382
                    image_y += 382 + 10
                elif imagelen <= 4:
                    # 4图，图大小382
                    image_y += 764 + 15
                # elif imagelen <= 6:
                else:
                    # 6图，图大小253
                    image_y += 10
                    while imagelen >= 1:
                        imagelen -= 3
                        image_y += 253 + 5

                image_x = int(image_x)
                image_y = int(image_y)
                draw_image = new_background(image_x, image_y)
                draw = ImageDraw.Draw(draw_image)
                # 开始往图片添加内容
                # 添加用户信息
                image_info = draw_info()
                draw_image.paste(image_info, (0, 0), mask=image_info)

                # 添加动态内容
                x = 75
                y = 230
                paste_image = draw_text(card_message,
                                        size=30,
                                        textlen=24,
                                        bili_emoji_infos=emoji_infos,
                                        bili_at_infos=at_infos)
                draw_image.paste(paste_image, (x, y), mask=paste_image)
                w, h = paste_image.size

                x = 65
                y = 230 + h + 20

                print_x = -1
                print_y = 0

                imagelen = len(images)
                if imagelen == 1:
                    paste_image = circle_corner(addimage, 15)
                    draw_image.paste(paste_image, (int(x), int(y)), mask=paste_image)
                elif imagelen <= 4:
                    # 2图，图大小382
                    for image in images:
                        print_x += 1
                        if print_x >= 2:
                            print_x = 0
                            print_y += 1
                        paste_image = connect_api("image", image)
                        paste_image = image_resize2(image=paste_image, size=(382, 382), overturn=True)
                        paste_image = circle_corner(paste_image, 15)
                        draw_image.paste(paste_image, (int(x + print_x * (382 + 5)), int(y + print_y * (382 + 5))),
                                         mask=paste_image)
                # elif imagelen <= 6:
                else:
                    # 6图，图大小253
                    for image in images:
                        print_x += 1
                        if print_x >= 3:
                            print_x = 0
                            print_y += 1

                        paste_image = connect_api("image", image)
                        paste_image = image_resize2(image=paste_image, size=(253, 253), overturn=True)
                        paste_image = circle_corner(paste_image, 15)
                        draw_image.paste(paste_image, (int(x + print_x * (253 + 5)), int(y + print_y * (253 + 5))),
                                         mask=paste_image)

                returnpath = cachepath + 'bili动态/'
                if not os.path.exists(returnpath):
                    os.makedirs(returnpath)
                returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                draw_image.save(returnpath)
                logger.debug("bili-push_draw_绘图成功")
                code = 2

        # 文字动态
        elif bilitype == 4:
            card_message = bilidata["item"]["content"]
            at_infos = bilidata["item"]["ctrl"] if "ctrl" in bilidata["item"] else None
            try:
                emoji_infos = data["display"]["emoji_info"]["emoji_details"]
            except Exception as e:
                emoji_infos = []
            logger.debug("bili-push_开始拼接文字")
            if run:
                message_title = biliname + "发布了动态"
                message_body = card_message
                if len(message_body) > 80:
                    message_body = message_body[0:79] + "……"
            logger.debug("bili-push_开始绘图")
            if run:
                fortsize = 30
                font = ImageFont.truetype(font=fontfile, size=fortsize)

                # 计算图片长度
                image_x = 900
                image_y = 140  # add base y
                image_y += 125 + 35  # add hear and space
                paste_image = draw_text(card_message,
                                        size=30,
                                        textlen=24,
                                        bili_emoji_infos=emoji_infos,
                                        calculate=True)
                w, h = paste_image.size
                image_y += h

                image_x = int(image_x)
                image_y = int(image_y)
                draw_image = new_background(image_x, image_y)
                draw = ImageDraw.Draw(draw_image)
                # 开始往图片添加内容
                # 添加用户信息
                image_info = draw_info()
                draw_image.paste(image_info, (0, 0), mask=image_info)

                # 添加动态内容
                x = 75
                y = 230
                paste_image = draw_text(card_message,
                                        size=30,
                                        textlen=24,
                                        bili_emoji_infos=emoji_infos,
                                        bili_at_infos=at_infos)
                draw_image.paste(paste_image, (x, y), mask=paste_image)

                returnpath = cachepath + 'bili动态/'
                if not os.path.exists(returnpath):
                    os.makedirs(returnpath)
                returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                draw_image.save(returnpath)
                logger.debug("bili-push_draw_绘图成功")
                code = 2

        # 投稿视频
        elif bilitype == 8:
            card_message = bilidata["dynamic"]
            card_title = bilidata["title"]
            card_vmessage = bilidata["desc"]
            card_image = bilidata["pic"]
            try:
                emoji_infos = data["display"]["emoji_info"]["emoji_details"]
            except Exception as e:
                emoji_infos = []
            logger.debug("bili-push_开始拼接文字")
            if run:
                message_title = biliname + "投稿了视频"
                message_body = card_message
                if len(message_body) > 80:
                    message_body = message_body[0:79] + "……"
                message_images = [card_image]
            logger.debug("bili-push_开始绘图")
            if run:
                # 开始绘图
                image_x = 900
                image_y = 500
                # 添加文字长度
                paste_image = draw_text(card_message,
                                        size=30,
                                        textlen=24,
                                        bili_emoji_infos=emoji_infos,
                                        calculate=True)
                w, h = paste_image.size
                image_y += h

                draw_image = new_background(image_x, image_y)
                draw = ImageDraw.Draw(draw_image)

                # 开始往图片添加内容
                # 添加用户信息
                image_info = draw_info()
                draw_image.paste(image_info, (0, 0), mask=image_info)

                # 添加动态内容
                paste_image = draw_text(card_message,
                                        size=30,
                                        textlen=24,
                                        bili_emoji_infos=emoji_infos)
                draw_image.paste(paste_image, (75, 230), mask=paste_image)
                w, h = paste_image.size
                y = 240 + h + 20
                x = 65
                # 添加视频消息边沿
                paste_image = Image.new("RGB", (776, 204), "#FFFFFF")
                paste_image = circle_corner(paste_image, 15)
                draw_image.paste(paste_image, (x - 2, y - 2), mask=paste_image)
                # 添加视频消息框
                paste_image = Image.new("RGB", (772, 200), "#f8fbfd")
                paste_image = circle_corner(paste_image, 15)
                draw_image.paste(paste_image, (x, y), mask=paste_image)
                # 添加视频图像
                x += 2
                y += 2
                paste_image = connect_api("image", card_image)
                paste_image = image_resize2(paste_image, (313, 196))
                paste_image = circle_corner(paste_image, 15)
                draw_image.paste(paste_image, (x, y), mask=paste_image)
                # 添加视频标题
                x += 313 + 15
                y += 15
                if len(card_title) > 26:
                    card_title = card_title[0:26] + "…"
                paste_image = draw_text(card_title,
                                        size=27,
                                        textlen=16,
                                        bili_emoji_infos=emoji_infos,
                                        calculate=False)
                draw_image.paste(paste_image, (x, y), mask=paste_image)
                w, h = paste_image.size

                # 添加视频简介
                y += 100
                if len(card_vmessage) > 26:
                    card_vmessage = card_vmessage[0:26] + "…"

                paste_image = draw_text(card_vmessage,
                                        size=25,
                                        textlen=17,
                                        text_color="#646464",
                                        bili_emoji_infos=emoji_infos,
                                        calculate=False)
                draw_image.paste(paste_image, (x, y), mask=paste_image)
                w, h = paste_image.size

                returnpath = cachepath + 'bili动态/'
                if not os.path.exists(returnpath):
                    os.makedirs(returnpath)
                returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                draw_image.save(returnpath)
                logger.debug("bili-push_draw_绘图成功")
                code = 2

        # 投稿文章
        elif bilitype == 64:
            card_title = bilidata["title"]
            card_message = bilidata["summary"]
            card_image = bilidata["image_urls"][0]
            try:
                emoji_infos = data["display"]["emoji_info"]["emoji_details"]
            except Exception as e:
                emoji_infos = []
            logger.debug("bili-push_开始拼接文字")
            if run:
                message_title = biliname + "投稿了文章"
                message_body = card_message
                if len(message_body) > 80:
                    message_body = message_body[0:79] + "……"
                message_images = [card_image]
            logger.debug("bili-push_开始绘图")
            if run:
                # 开始绘图
                image_x = 900
                image_y = 700
                draw_image = new_background(image_x, image_y)
                draw = ImageDraw.Draw(draw_image)

                # 开始往图片添加内容
                # 添加用户信息
                image_info = draw_info()
                draw_image.paste(image_info, (0, 0), mask=image_info)

                x = 75
                y = 246
                # 添加文章消息边沿
                paste_image = Image.new("RGB", (776, 404), "#FFFFFF")
                paste_image = circle_corner(paste_image, 15)
                draw_image.paste(paste_image, (x - 2, y - 2), mask=paste_image)
                # 添加文章消息框
                paste_image = Image.new("RGB", (772, 400), "#f8fbfd")
                paste_image = circle_corner(paste_image, 15)
                draw_image.paste(paste_image, (x, y), mask=paste_image)
                # 添加文章图像
                x += 2
                y += 2
                paste_image = connect_api("image", card_image)
                paste_image = image_resize2(paste_image, (768, 225))
                paste_image = circle_corner(paste_image, 15)
                draw_image.paste(paste_image, (x, y), mask=paste_image)

                # 添加文章标题
                y += 230
                if len(card_title) > 53:
                    card_title = card_title[0:52] + "…"
                paste_image = draw_text(
                    texts=card_title,
                    size=27,
                    textlen=28,
                    bili_emoji_infos=emoji_infos
                )
                draw_image.paste(paste_image, (x, y), mask=paste_image)

                # 添加文章内容
                y += int(2.4 * fortsize)
                if len(card_message) > 79:
                    card_message = card_message[0:78] + "…"
                paste_image = draw_text(
                    texts=card_message,
                    size=27,
                    textlen=28,
                    text_color="#606060",
                    bili_emoji_infos=emoji_infos
                )
                draw_image.paste(paste_image, (x, y), mask=paste_image)

                returnpath = cachepath + 'bili动态/'
                if not os.path.exists(returnpath):
                    os.makedirs(returnpath)
                returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                draw_image.save(returnpath)
                logger.debug("bili-push_draw_绘图成功")
                code = 2
        else:
            logger.error("不支持的动态类型")
            if run:
                message_title = biliname + "发布了动态"
                message_body = "[不支持的动态类型]"
                if len(message_body) > 80:
                    message_body = message_body[0:79] + "……"
            logger.debug("bili-push_开始绘图")
            if run:
                logger.debug("bili-push_开始绘图")
                fortsize = 30
                font = ImageFont.truetype(font=fontfile, size=fortsize)

                # 计算图片长度
                image_x = 900
                image_y = 140  # add base y
                image_y += 125 + 35  # add hear and space
                paste_image = draw_text("暂不支持的动态类型",
                                        size=30,
                                        textlen=24,
                                        bili_emoji_infos=emoji_infos,
                                        calculate=True)
                w, h = paste_image.size
                image_y += h

                image_x = int(image_x)
                image_y = int(image_y)
                draw_image = new_background(image_x, image_y)
                draw = ImageDraw.Draw(draw_image)
                # 开始往图片添加内容
                # 添加用户信息
                image_info = draw_info()
                draw_image.paste(image_info, (0, 0), mask=image_info)
                # 添加动态内容
                x = 75
                y = 230
                paste_image = draw_text("[不支持动态类型]",
                                        size=30,
                                        textlen=24,
                                        bili_emoji_infos=emoji_infos)
                draw_image.paste(paste_image, (x, y), mask=paste_image)

                returnpath = cachepath + 'bili动态/'
                if not os.path.exists(returnpath):
                    os.makedirs(returnpath)
                returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                draw_image.save(returnpath)
                logger.debug("bili-push_draw_绘图成功")
                code = 2

    except Exception as e:
        logger.error(f"获取消息出错，请讲此消息反馈给开发者。动态id：{dynamicid}")
        message_title = ""
        message_body = ""
        message_url = ""
        message_images = []
        code = 0

    logger.debug("bili-push_draw_结束绘制")
    return {
        "code": code,
        "draw_path": returnpath,
        "message_title": message_title,
        "message_url": message_url,
        "message_body": message_body,
        "message_images": message_images
        }


get_new = on_command("最新动态", aliases={'添加订阅', '删除订阅', '查看订阅', '帮助'}, block=False)


@get_new.handle()
async def bili_push_command(bot: Bot, messageevent: MessageEvent):
    logger.info(f"bili_push_command_{plugin_version}")
    botid = str(bot.self_id)
    bot_type = nonebot.get_bot(botid).type
    if bot_type != "OneBot V11":
        logger.error("暂不支持的适配器")
        await get_new.finish(MessageSegment.text("暂不支持的适配器"))
    returnpath = "None"
    message = " "
    code = 0
    qq = messageevent.get_user_id()
    if isinstance(messageevent, GroupMessageEvent):
        # 群消息才有群号
        groupcode = messageevent.group_id
        groupcode = str(groupcode)
    else:
        # 这是用户qq号
        groupcode = messageevent.get_user_id()
        groupcode = "p" + str(groupcode)
    groupcode = "g" + groupcode
    msg = messageevent.get_message()
    msg = re.sub(u"\\[.*?]", "", str(msg))
    msg = msg.replace("'", "“")
    msg = msg.replace('"', "“")
    msg = msg.replace("(", "（")
    msg = msg.replace(")", "）")

    commands = []
    if ' ' in msg:
        messages = msg.split(' ', 1)
        for command in messages:
            commands.append(command)
    else:
        commands.append(msg)
    command = str(commands[0])
    for command_start in plugin_config("group_command_starts", groupcode):
        if commands != "":
            if command.startswith(command_start):
                command = command.removeprefix(command_start)
    command = command.removeprefix("/")
    if len(commands) >= 2:
        command2 = commands[1]
    else:
        command2 = ''

    date_year = str(time.strftime("%Y", time.localtime()))
    date_month = str(time.strftime("%m", time.localtime()))
    date_day = str(time.strftime("%d", time.localtime()))
    cachepath = f"{basepath}cache/draw/{date_year}/{date_month}/{date_day}/"

    # 新建数据库
    # 读取数据库列表
    conn = sqlite3.connect(livedb)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
    datas = cursor.fetchall()
    # 数据库列表转为序列
    tables = []
    for data in datas:
        if data[1] != "sqlite_sequence":
            tables.append(data[1])
    # 检查是否创建订阅数据库3
    if "subscriptionlist3" not in tables:
        # 如未创建，则创建
        cursor.execute('create table subscriptionlist3(id INTEGER primary key AUTOINCREMENT, '
                       'groupcode varchar(10), uid int(10), liveid int(10))')
        # 判断是否存在旧数据库
        if "subscriptionlist2" in tables:
            # 如果是，则存到数据库3
            cursor.execute("SELECT * FROM subscriptionlist2")
            datas = cursor.fetchall()
            for data in datas:
                # 自动获取房间号
                # url = ""
                liveid = 0
                cursor.execute(f'replace into subscriptionlist3 ("groupcode","uid","liveid") '
                               f'values("{data[1]}",{data[2]},{liveid})')
        elif "subscriptionlist" in tables:
            # 如果是，则存到数据库3
            cursor.execute("SELECT * FROM subscriptionlist")
            datas = cursor.fetchall()
            for data in datas:
                # 自动获取房间号
                # url = ""
                liveid = 0
                cursor.execute(f'replace into subscriptionlist3 ("groupcode","uid","liveid") '
                               f'values("{data[1]}",{data[2]},{liveid})')
    if "livelist4" not in tables:
        # 如未创建，则创建
        cursor.execute('create table livelist4(uid varchar(10) primary key, state varchar(10), draw varchar(10), '
                       'username varchar(10), message_title varchar(10), room_id varchar(10), image varchar(10))')
        if "livelist3" in tables:
            cursor.execute("SELECT * FROM livelist3")
            datas = cursor.fetchall()
            for data in datas:
                # 写入数据
                cursor.execute(
                    f'replace into livelist4 (uid, state, draw, username, message_title, room_id, image) '
                    f'values'
                    f'("{data[1]}","{data[2]}","{data[3]}","{data[4]}","{data[5]}","{data[6]}","none")')
    if "wait_push2" not in tables:
        cursor.execute(
            "create table 'wait_push2' (dynamicid int(10) primary key, uid varchar(10), "
            "draw_path varchar(20), message_title varchar(20), message_url varchar(20), "
            "message_body varchar(20), message_images varchar(20))")
    cursor.close()
    conn.commit()
    conn.close()

    if command == "最新动态":
        logger.debug("command:查询最新动态")
        code = 0

        # 判断command2是否为纯数字或l开头的数字
        if "UID:" in command2:
            command2 = command2.removeprefix("UID:")
        if command2.startswith("L"):
            command2 = command2.replace("L", "l")
        if command2.startswith("l"):
            command2_cache = command2.removeprefix("l")
        else:
            command2_cache = command2
        try:
            command2_cache = int(command2_cache)
            if command2.startswith("l"):
                command2 = f"l{command2_cache}"
            else:
                command2 = str(command2_cache)
        except Exception as e:
            command2 = ""
        if command2 == "":
            code = 1
            message = "请添加uid或房间id来添加订阅"
        else:
            uid = command2
            logger.debug(f"开始获取信息-{uid}")
            url = "https://api.vc.b"
            url += f"i{pilipala}li.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid}"
            returnjson = connect_api("json", url)
            if returnjson["code"] == 0:
                logger.debug('获取动态图片并发送')
                # 获取动态图片并发送
                draw_info = get_draw(returnjson["data"]["cards"][0])
                return_code = draw_info["code"]
                if return_code == 0:
                    code = 1
                    message = "不支持动态类型"
                else:
                    dynamicid = str(returnjson["data"]["cards"][0]["desc"]["dynamic_id"])
                    returnpath = draw_info["draw_path"]

                    message_title = draw_info["message_title"]
                    message_url = draw_info["message_url"]
                    message_body = draw_info["message_body"]
                    message_images = draw_info["message_images"]

                    num = 10
                    cache_push_style = plugin_config("bilipush_push_style", groupcode)
                    msg = MessageSegment.text("")
                    while num > 0:
                        num -= 1
                        if cache_push_style.startswith("[绘图]"):
                            file = open(returnpath, 'br')
                            io_file = io.BytesIO(file.read())
                            cache_msg = MessageSegment.image(io_file)
                            msg += cache_msg
                            cache_push_style = cache_push_style.removeprefix("[绘图]")
                        elif cache_push_style.startswith("[标题]"):
                            cache_msg = MessageSegment.text(message_title)
                            msg += cache_msg
                            cache_push_style = cache_push_style.removeprefix("[标题]")
                        elif cache_push_style.startswith("[链接]"):
                            cache_msg = MessageSegment.text(message_url)
                            msg += cache_msg
                            cache_push_style = cache_push_style.removeprefix("[链接]")
                        elif cache_push_style.startswith("[内容]"):
                            cache_msg = MessageSegment.text(message_body)
                            msg += cache_msg
                            cache_push_style = cache_push_style.removeprefix("[内容]")
                        elif cache_push_style.startswith("[图片]"):
                            num = 0
                            for url in message_images:
                                num += 1
                                image = connect_api("image", url)
                                image_path = f"{cachepath}{dynamicid}/"
                                if not os.path.exists(image_path):
                                    os.makedirs(image_path)
                                image_path += f"{num}.png"
                                image.save(image_path)
                                file = open(returnpath, 'br')
                                io_file = io.BytesIO(file.read())
                                cache_msg = MessageSegment.image(io_file)
                                msg += cache_msg
                            cache_push_style = cache_push_style.removeprefix("[图片]")
                        elif cache_push_style == "":
                            num = 0
                        else:
                            logger.error("读取动态推送样式出错，请检查配置是否正确")
                    code = 4
            else:
                logger.debug('returncode!=0')
                code = 1
                message = "获取动态失败"
    elif command == "添加订阅":
        if qq in plugin_config("admin", groupcode):
            logger.debug("command:添加订阅")
            code = 0

            # 判断command2是否为纯数字或l开头的数字
            if "UID:" in command2:
                command2 = command2.removeprefix("UID:")
            if command2.startswith("L"):
                command2 = command2.replace("L", "l")
            if command2.startswith("l"):
                command2_cache = command2.removeprefix("l")
            else:
                command2_cache = command2
            try:
                command2_cache = int(command2_cache)
                if command2.startswith("l"):
                    command2 = f"l{command2_cache}"
                else:
                    command2 = str(command2_cache)
            except Exception as e:
                command2 = ""
            if command2 == "":
                code = 1
                message = "请添加uid或房间id来添加订阅"
            else:
                if command2.startswith("l"):
                    liveid = command2[1:]
                    url = "https://api.live.b"
                    url += f"i{pilipala}li.com/room/v1/Room/get_info?id={liveid}"
                    json_data = connect_api("json", url)
                    if json_data["code"] != 0:
                        logger.error(f"直播api出错请将此消息反馈给开发者，liveid={liveid},msg={json_data['message']}")
                        uid = 0
                    else:
                        livedata = json_data["data"]
                        uid = livedata["uid"]
                else:
                    liveid = 0
                    uid = command2

                conn = sqlite3.connect(livedb)
                cursor = conn.cursor()
                if command2.startswith("l"):
                    cursor.execute(
                        f"SELECT * FROM subscriptionlist3 WHERE liveid = {command2[1:]} AND groupcode = '{groupcode}'")
                else:
                    cursor.execute(
                        f"SELECT * FROM subscriptionlist3 WHERE uid = {command2} AND groupcode = '{groupcode}'")
                subscription = cursor.fetchone()
                cursor.close()
                conn.commit()
                conn.close()

                if uid == 0:
                    code = 1
                    message = "订阅失败，请检查错误日志"
                elif subscription is not None and subscription[3] is None:
                    # 写入数据
                    conn = sqlite3.connect(livedb)
                    cursor = conn.cursor()
                    cursor.execute(f"replace into subscriptionlist3 ('groupcode','uid','liveid') "
                                   f"values('{groupcode}','{uid}','{liveid}')")
                    cursor.close()
                    conn.commit()
                    conn.close()

                    code = 1
                    message = "添加直播、动态间订阅成功"
                elif subscription is None:
                    logger.debug("无订阅，添加订阅")

                    # 写入数据
                    conn = sqlite3.connect(livedb)
                    cursor = conn.cursor()
                    cursor.execute(f"replace into subscriptionlist3 ('groupcode','uid','liveid') "
                                   f"values('{groupcode}','{uid}','{liveid}')")
                    cursor.close()
                    conn.commit()
                    conn.close()

                    # 将历史动态存到数据库中
                    logger.debug('关注成功，将历史动态存到数据库中')
                    url = "https://api.vc.b"
                    url += f"i{pilipala}li.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid}"
                    returnjson = connect_api("json", url)
                    returncode = returnjson["code"]
                    if returncode == 0:
                        logger.debug('获取动态图片并发送')
                        if returnjson["data"]["has_more"] == 1:
                            return_datas = returnjson["data"]["cards"]

                            conn = sqlite3.connect(livedb)
                            cursor = conn.cursor()
                            cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
                            datas = cursor.fetchall()
                            tables = []
                            for data in datas:
                                if data[1] != "sqlite_sequence":
                                    tables.append(data[1])
                            if groupcode not in tables:
                                cursor.execute(f'create table {groupcode}'
                                               f'(dynamicid int(10) primary key, uid varchar(10))')
                            # 将新动态保存到数据库中
                            for return_data in return_datas:
                                dynamicid = str(return_data["desc"]["dynamic_id"])
                                cursor.execute(f"replace into {groupcode}(dynamicid,uid) values('{dynamicid}','{uid}')")
                            # 检查数据库中是否有旧动态，更新到群已推送列表中
                            cursor.execute(f"SELECT * FROM wait_push2 WHERE uid='{uid}'")
                            datas = cursor.fetchall()
                            if datas:
                                for data in datas:
                                    cursor.execute(
                                        f"replace into {groupcode}(dynamicid,uid) values('{data[0]}','{data[1]}')")
                            cursor.close()
                            conn.commit()
                            conn.close()

                            drawimage = get_draw(return_datas[0], only_info=True)
                            if drawimage["code"] != 0:
                                returnpath = drawimage["draw_path"]
                                if command2.startswith("l"):
                                    message = "添加直播、动态订阅成功"
                                else:
                                    message = "添加动态订阅成功\n如需订阅直播间，请发送“/添加订阅 L”+直播间号\n例：“/添加订阅 L1234”"
                                code = 3
                            else:
                                code = 1
                                message = "添加订阅成功"
                        else:
                            code = 1
                            message = "添加订阅成功。\n该up主未发布任何动态，请确认是否填写了正确的uid"
                    else:
                        code = 1
                        message = "获取动态内容出错，请检查uid是否正确"
                else:
                    code = 1
                    message = "该up主已存在数据库中"
        else:
            code = 1
            message = "您无权限操作哦"
    elif command == "删除订阅":
        if qq in plugin_config("admin", groupcode):
            logger.debug("command:删除订阅")
            code = 0

            # 判断command2是否为纯数字或l开头的数字
            if "UID:" in command2:
                command2 = command2.removeprefix("UID:")
            if command2.startswith("L"):
                command2 = command2.replace("L", "l")
            if command2.startswith("l"):
                command2_cache = command2.removeprefix("l")
            else:
                command2_cache = command2
            try:
                command2_cache = int(command2_cache)
                if command2.startswith("l"):
                    command2 = f"l{command2_cache}"
                else:
                    command2 = str(command2_cache)
            except Exception as e:
                command2 = ""
            if command2 == "":
                code = 1
                message = "请添加uid或房间id来添加订阅"
            else:
                conn = sqlite3.connect(livedb)
                cursor = conn.cursor()
                if command2.startswith("l"):
                    cursor.execute(
                        f"SELECT * FROM subscriptionlist3 WHERE liveid = {command2[1:]} AND groupcode = '{groupcode}'")
                else:
                    cursor.execute(
                        f"SELECT * FROM subscriptionlist3 WHERE uid = {command2} AND groupcode = '{groupcode}'")
                subscription = cursor.fetchone()
                cursor.close()
                conn.commit()
                conn.close()

                if subscription is None:
                    code = 1
                    message = "未订阅该up主"
                else:
                    subid = str(subscription[0])
                    conn = sqlite3.connect(livedb)
                    cursor = conn.cursor()
                    cursor.execute(f"delete from subscriptionlist3 where id = {subid}")
                    conn.commit()
                    cursor.close()
                    conn.close()
                    code = 1
                    message = "删除订阅成功"
        else:
            code = 1
            message = "您无权限操作哦"
    elif command == "查看订阅":

        conn = sqlite3.connect(livedb)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM subscriptionlist3 WHERE groupcode = '" + groupcode + "'")
        subscriptions = cursor.fetchall()
        cursor.close()
        conn.commit()
        conn.close()
        if not subscriptions:
            code = 1
            message = "该群无订阅"
        else:
            code = 1
            message = "订阅列表：\n"
            for subscription in subscriptions:
                uid = str(subscription[2])
                message += "UID:" + uid + "\n"
    elif command == "帮助":
        code = 1
        message = "Bili_Push：\n/添加订阅\n/删除订阅\n/查看订阅\n/最新动态"

    # 消息处理完毕，返回发送的消息
    if code == 1:
        msg = MessageSegment.text(message)
        await get_new.finish(msg)
    elif code == 2:
        file = open(returnpath, 'br')
        io_file = io.BytesIO(file.read())
        msg = MessageSegment.image(io_file)
        await get_new.finish(msg)
    elif code == 3:
        file = open(returnpath, 'br')
        io_file = io.BytesIO(file.read())
        msg1 = MessageSegment.image(io_file)
        msg2 = MessageSegment.text(message)
        msg = msg1 + msg2
        await get_new.finish(msg)
    elif code == 4:
        await get_new.finish(msg)
    else:
        await get_new.finish()


minute = "*/" + waittime


@scheduler.scheduled_job("cron", minute=minute, id="job_0")
async def run_bili_push():
    logger.debug(f"bili_push_autorun_{plugin_version}")
    # ############开始自动运行插件############
    now_maximum_send = maximum_send
    date = str(time.strftime("%Y-%m-%d", time.localtime()))
    date_year = str(time.strftime("%Y", time.localtime()))
    date_month = str(time.strftime("%m", time.localtime()))
    date_day = str(time.strftime("%d", time.localtime()))
    timenow = str(time.strftime("%H-%M-%S", time.localtime()))
    cachepath = basepath + f"cache/draw/{date_year}/{date_month}/{date_day}/"
    message = "none"

    botids = list(nonebot.get_bots())
    for botid in botids:
        bot_type = nonebot.get_bot(botid).type
        if bot_type != "OneBot V11":
            logger.debug("暂不支持的适配器类型")
            continue
        botid = str(botid)

        # 获取成员名单与频道名单
        friendlist = []
        grouplist = []
        friends = await nonebot.get_bot(botid).get_friend_list()
        for friendinfo in friends:
            friendlist.append(str(friendinfo["user_id"]))

        groups = await nonebot.get_bot(botid).get_group_list()
        for memberinfo in groups:
            grouplist.append(str(memberinfo["group_id"]))

        # 新建数据库
        # 读取数据库列表
        conn = sqlite3.connect(livedb)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
        datas = cursor.fetchall()
        # 数据库列表转为序列
        tables = []
        for data in datas:
            if data[1] != "sqlite_sequence":
                tables.append(data[1])
        # 检查是否创建数据库
        if "subscriptionlist3" not in tables:
            # 如未创建，则创建
            cursor.execute('create table subscriptionlist3(id INTEGER primary key AUTOINCREMENT, '
                           'groupcode varchar(10), uid int(10), liveid int(10))')
            # 判断是否存在旧数据库
            if "subscriptionlist2" in tables:
                # 如果是，则存到数据库3
                cursor.execute("SELECT * FROM subscriptionlist2")
                datas = cursor.fetchall()
                for data in datas:
                    # 自动获取房间号
                    # url = ""
                    liveid = 0
                    cursor.execute(f'replace into subscriptionlist3 ("groupcode","uid","liveid") '
                                   f'values("{data[1]}",{data[2]},{liveid})')
            elif "subscriptionlist" in tables:
                # 如果是，则存到数据库3
                cursor.execute("SELECT * FROM subscriptionlist")
                datas = cursor.fetchall()
                for data in datas:
                    # 自动获取房间号
                    # url = ""
                    liveid = 0
                    cursor.execute(f'replace into subscriptionlist3 ("groupcode","uid","liveid") '
                                   f'values("{data[1]}",{data[2]},{liveid})')
        if "livelist4" not in tables:
            # 如未创建，则创建
            cursor.execute('create table livelist4(uid varchar(10) primary key, state varchar(10), draw varchar(10), '
                           'username varchar(10), message_title varchar(10), room_id varchar(10), image varchar(10))')
            if "livelist3" in tables:
                cursor.execute("SELECT * FROM livelist3")
                datas = cursor.fetchall()
                for data in datas:
                    # 写入数据
                    cursor.execute(
                        f'replace into livelist4 (uid, state, draw, username, message_title, room_id, image) '
                        f'values'
                        f'("{data[1]}","{data[2]}","{data[3]}","{data[4]}","{data[5]}","{data[6]}","none")')
        if "wait_push2" not in tables:
            cursor.execute(
                "create table 'wait_push2' (dynamicid int(10) primary key, uid varchar(10), "
                "draw_path varchar(20), message_title varchar(20), message_url varchar(20), "
                "message_body varchar(20), message_images varchar(20))")
        cursor.close()
        conn.commit()
        conn.close()

        # ############获取动态############
        run = True  # 代码折叠
        if run:
            logger.debug('---获取更新的动态')

            conn = sqlite3.connect(livedb)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptionlist3")
            subscriptions = cursor.fetchall()
            cursor.close()
            conn.commit()
            conn.close()

            if not subscriptions:
                logger.debug("无订阅")
            else:
                subscriptionlist = []
                for subscription in subscriptions:
                    uid = str(subscription[2])
                    groupcode = subscription[1]
                    if groupcode.startswith("gp"):
                        if groupcode[2:] in friendlist:
                            if uid not in subscriptionlist:
                                subscriptionlist.append(uid)
                    else:
                        if groupcode[1:] in grouplist:
                            if uid not in subscriptionlist:
                                subscriptionlist.append(uid)

                for uid in subscriptionlist:
                    logger.debug(f"开始获取信息-{uid}")
                    url = ('https://api.vc.b'
                           f'i{pilipala}li.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid=') + uid
                    returnjson = connect_api("json", url)
                    if returnjson["code"] != 0:
                        logger.error("bapi连接出错，请检查订阅uid是否正确")
                    else:
                        return_datas = returnjson["data"]
                        if return_datas["has_more"] == 0:
                            logger.debug("该up主无动态")
                        else:
                            return_datas = return_datas["cards"]
                            logger.debug('获取up主动态列表成功')
                            # 比较已保存内容
                            conn = sqlite3.connect(livedb)
                            cursor = conn.cursor()
                            for return_data in return_datas:
                                dynamicid = str(return_data["desc"]["dynamic_id"])
                                cursor.execute("SELECT * FROM 'wait_push2' WHERE dynamicid = '" + dynamicid + "'")
                                data = cursor.fetchone()
                                if data is None:
                                    dyma_data = return_data["desc"]["timestamp"]
                                    now = int(time.time())
                                    time_distance = now - dyma_data
                                    # 不推送24小时以前的动态
                                    # 1天：86400
                                    # 啊？我之前怎么把86400秒当成3天啊？还一直没发现
                                    if time_distance < 86400:
                                        return_draw = get_draw(return_data)
                                        if return_draw["code"] == 0:
                                            logger.debug("不支持类型")
                                        else:
                                            draw_path = return_draw["draw_path"]
                                            message_title = return_draw["message_title"]
                                            message_url = return_draw["message_url"]
                                            message_body = return_draw["message_body"]
                                            message_images = str({"images": return_draw["message_images"]})

                                            message_body = message_body.replace("'", '"')

                                            cursor.execute(
                                                f"replace into wait_push2(dynamicid,uid,draw_path,message_title,"
                                                f'message_url,message_body,message_images) values("{dynamicid}","{uid}",'
                                                f'"{draw_path}","{message_title}","{message_url}",' + f"'{message_body}'"
                                                                                                      f',"{message_images}")')
                            cursor.close()
                            conn.commit()
                            conn.close()

        # ############获取直播状态############
        run = True  # 代码折叠
        if run:
            logger.info("获取更新的直播")

            if use_api is True:
                fontfile = get_file_path("腾祥嘉丽中圆.ttf")
            else:
                fontfile = get_file_path("NotoSansSC[wght].ttf")
            fortsize = 30
            font = ImageFont.truetype(font=fontfile, size=fortsize)
            logger.debug("获取订阅列表")

            conn = sqlite3.connect(livedb)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptionlist3")
            subscriptions = cursor.fetchall()
            cursor.close()
            conn.commit()
            conn.close()

            if not subscriptions:
                logger.debug("无订阅")
            else:
                subscriptionlist = []
                if beta_test:
                    print(f"debug:pass list: {subscriptionlist}")
                for subscription in subscriptions:
                    liveid = int(subscription[3])
                    if liveid == 0:
                        # 未获取房间号，开始获取房间号
                        if beta_test:
                            print(f"debug:pass uid: {subscription[2]}")
                    if liveid != 0:
                        subscriptionlist.append(str(liveid))
                if subscriptionlist:
                    for liveid in subscriptionlist:
                        url = "https://api.live.bi"
                        url += f"{pilipala}li.com/room/v1/Room/get_info?id={liveid}"
                        json_data = connect_api("json", url)
                        if json_data["code"] != 0:
                            logger.error("直播api出错请将此消息反馈给开发者，sub[0]=" + str(subscriptionlist[0]) +
                                         ",msg=" + json_data["message"])
                        else:
                            livedata = json_data["data"]
                            uid = livedata["uid"]
                            logger.debug(f"bili_live_开始获取消息:{uid}")

                            url = (f"https://api.v"
                                   f"c.bi{pilipala}li.co"
                                   f"m/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid}")
                            json_data = connect_api("json", url)
                            if json_data["code"] != 0:
                                logger.error("bapi连接出错")
                                return_data = {"user_profile": {"info": {"uname": "name", "face": "None"}}}
                            elif json_data["data"]["has_more"] == 0:
                                logger.debug("up未发动态")
                                return_data = {"user_profile": {"info": {"uname": "name", "face": "None"}}}
                            else:
                                return_data = json_data["data"]["cards"][0]["desc"]

                            conn = sqlite3.connect(livedb)
                            cursor = conn.cursor()
                            live_status = str(livedata["live_status"])
                            cursor.execute(f"SELECT * FROM livelist4 WHERE uid='{uid}'")
                            data_db = cursor.fetchone()
                            if data_db is None or live_status != str(data_db[1]):
                                uname = return_data["user_profile"]["info"]["uname"]
                                face = return_data["user_profile"]["info"]["face"]
                                cover_from_user = livedata["user_cover"]
                                keyframe = livedata["keyframe"]
                                live_title = livedata["title"]
                                room_id = livedata["room_id"]

                                live_time = livedata["live_time"]
                                # 无需转换
                                # live_time = time.localtime(live_time)
                                # live_time = time.strftime("%Y年%m月%d日 %H:%M:%S", live_time)

                                # online = livedata["online"]

                                if live_status == "1":
                                    logger.debug("live开始绘图")
                                    draw_image = new_background(900, 800)
                                    draw = ImageDraw.Draw(draw_image)

                                    # 开始往图片添加内容
                                    # 添加头像
                                    image_face = connect_api("image", face)
                                    image_face = image_face.resize((125, 125))
                                    imageround = Image.new("RGBA", (200, 200), (255, 255, 255, 0))
                                    imageround = circle_corner(imageround, 100)
                                    imageround = imageround.resize((129, 129))
                                    draw_image.paste(imageround, (73, 73), mask=imageround)
                                    imageround = imageround.resize((125, 125))
                                    draw_image.paste(image_face, (75, 75), mask=imageround)

                                    # 添加名字
                                    cache_font = ImageFont.truetype(font=fontfile, size=35)
                                    draw.text(xy=(230, 85), text=uname, fill=(0, 0, 0), font=cache_font)

                                    # 添加日期
                                    draw.text(xy=(230, 145), text=live_time, fill=(100, 100, 100), font=font)

                                    # 添加状态
                                    draw.text(xy=(75, 230), text="正在直播", fill=(0, 0, 0), font=font)

                                    # 添加标题
                                    draw.text(xy=(75, 270), text=live_title, fill=(0, 0, 0), font=font)

                                    # 添加封面
                                    cover_path = "none"
                                    if cover_from_user != "":
                                        paste_image = connect_api("image", cover_from_user)
                                        cover_path = basepath + '/cache/bili动态/'
                                        if not os.path.exists(cover_path):
                                            os.makedirs(cover_path)
                                        cover_path = (f"{cover_path}{date}_{timenow}_cover_"
                                                      f"{random.randint(1000, 9999)}.png")
                                        paste_image.save(cover_path)
                                        paste_image = paste_image.resize((772, 434))
                                        paste_image = circle_corner(paste_image, 15)
                                        draw_image.paste(paste_image, (75, 330))
                                    else:
                                        if keyframe != "":
                                            paste_image = connect_api("image", keyframe)
                                            cover_path = basepath + '/cache/bili动态/'
                                            if not os.path.exists(cover_path):
                                                os.makedirs(cover_path)
                                            cover_path = (f"{cover_path}{date}_{timenow}_cover_"
                                                          f"{random.randint(1000, 9999)}.png")
                                            paste_image.save(cover_path)
                                            paste_image = paste_image.resize((772, 434))
                                            paste_image = circle_corner(paste_image, 15)
                                            draw_image.paste(paste_image, (75, 330))

                                    returnpath = basepath + '/cache/bili动态/'
                                    if not os.path.exists(returnpath):
                                        os.makedirs(returnpath)
                                    returnpath = f"{returnpath}{date}_{timenow}_{random.randint(1000, 9999)}.png"
                                    draw_image.save(returnpath)

                                    # 写入数据
                                    cursor.execute(
                                        f'replace into livelist4 '
                                        f'(uid, state, draw, username, message_title, room_id, image)'
                                        f' values("{uid}","{live_status}","{returnpath}","{uname}","{live_title}",'
                                        f'"{room_id}","{cover_path}")')

                                elif live_status == "0":
                                    message = uname + "已下播"
                                    # 写入数据
                                    cursor.execute(
                                        f'replace into livelist4 ('
                                        f'uid, state, draw, username, message_title, room_id, image) values("{uid}",'
                                        f'"{live_status}","none","{uname}","{live_title}","{room_id}","none")')
                            cursor.close()
                            conn.commit()
                            conn.close()

        # ############推送直播状态############
        run = True  # 代码折叠
        if run:
            logger.info("推送直播")
            conn = sqlite3.connect(livedb)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptionlist3")
            subscriptions = cursor.fetchall()
            cursor.close()
            conn.commit()
            conn.close()

            if not subscriptions:
                logger.debug("无订阅")
            else:
                for subscription in subscriptions:
                    groupcode = subscription[1]
                    uid = str(subscription[2])
                    # 判断是否本bot以及是否主bot
                    send = True
                    if plugin_config("bilipush_botswift", groupcode):
                        # 读取主bot
                        send = False

                        conn = sqlite3.connect(heartdb)
                        cursor = conn.cursor()
                        # 数据库列表转为序列
                        cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
                        datas = cursor.fetchall()
                        tables = []
                        for data in datas:
                            if data[1] != "sqlite_sequence":
                                tables.append(data[1])
                        if groupcode not in tables:
                            cursor.execute(
                                f'create table {groupcode}(botid VARCHAR(10) primary key, permission VARCHAR(20))')
                        if "heart" not in tables:
                            cursor.execute(
                                'create table heart(botid VARCHAR(10) primary key, breattime VARCHAR(10), '
                                'number VARCHAR(10))')
                        cursor.execute(f'SELECT * FROM {groupcode} WHERE permission = "10"')
                        group_data = cursor.fetchone()
                        cursor.close()
                        conn.commit()
                        conn.close()

                        if group_data is None:
                            conn = sqlite3.connect(heartdb)
                            cursor = conn.cursor()
                            cursor.execute(f'replace into {groupcode}(botid,permission) values("{botid}","10")')
                            cursor.close()
                            conn.commit()
                            conn.close()

                            send = True
                        else:
                            if group_data[0] == botid:
                                send = True
                            else:
                                conn = sqlite3.connect(heartdb)
                                cursor = conn.cursor()
                                cursor.execute('select * from heart where botid = ' + str(group_data[0]))
                                data = cursor.fetchone()
                                cursor.close()
                                conn.close()

                                if data is not None:
                                    if int(data[2]) >= 5:
                                        send = True

                                conn = sqlite3.connect(heartdb)
                                cursor = conn.cursor()
                                cursor.execute('SELECT * FROM ' + groupcode + ' WHERE permission = "5"')
                                data = cursor.fetchone()
                                cursor.close()
                                conn.close()
                                if data is None:
                                    conn = sqlite3.connect(heartdb)
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        'replace into ' + groupcode + '(botid,permission) values("' + botid + '","5")')
                                    cursor.close()
                                    conn.commit()
                                    conn.close()
                        if send is False:
                            logger.debug("该订阅由另一个bot进行推送，本bot将不发送消息")

                    # 检查是否是好友、是否入群
                    if groupcode.startswith("gp"):
                        if groupcode[2:] not in friendlist:
                            send = False
                    else:
                        if groupcode[1:] not in grouplist:
                            send = False

                    # 检查是否不推送动态或直播
                    if uid in plugin_config("ignore_live_list", groupcode):
                        send = False

                    if send is True:
                        # 缓存文件，存储待发送动态 如果文件不存在，会自动在当前目录中创建
                        conn = sqlite3.connect(livedb)
                        cursor = conn.cursor()
                        # 数据库列表转为序列
                        cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
                        datas = cursor.fetchall()
                        tables = []
                        for data in datas:
                            if data[1] != "sqlite_sequence":
                                tables.append(data[1])
                        if groupcode not in tables:
                            cursor.execute(f"create table {groupcode} (dynamicid int(10) primary key, uid varchar(10))")
                        # 获取已推送的状态
                        cursor.execute(f"SELECT * FROM {groupcode} WHERE dynamicid = 'live{uid}'")
                        pushed_datas = cursor.fetchone()
                        # 获取最新动态
                        cursor.execute(f"SELECT * FROM 'livelist4' WHERE uid = '{uid}'")
                        datas = cursor.fetchone()
                        cursor.close()
                        conn.commit()
                        conn.close()

                        if datas is not None:
                            state = datas[1]
                            if pushed_datas is None:
                                new_push = True
                                pushed_state = "none"
                            else:
                                new_push = False
                                pushed_state = pushed_datas[1]
                            if state != pushed_state:
                                # 推送直播消息，并保存为已推送
                                conn = sqlite3.connect(livedb)
                                cursor = conn.cursor()
                                cursor.execute("SELECT * FROM 'livelist4' WHERE uid = " + uid)
                                data = cursor.fetchone()
                                cursor.close()
                                conn.commit()
                                conn.close()

                                if data is not None:
                                    state = data[1]
                                    returnpath = data[2]
                                    biliname = data[3]
                                    message_title = data[4]
                                    room_id = data[5]
                                    message_url = f"live.bi{pilipala}li.com/{room_id}"

                                    # 0下播 1直播 2轮播
                                    if state == "1":
                                        num = 10
                                        cache_push_style = plugin_config("bilipush_push_style", groupcode)
                                        msg = MessageSegment.text("")
                                        while num > 0:
                                            num -= 1
                                            if cache_push_style.startswith("[绘图]"):
                                                file = open(returnpath, 'br')
                                                io_file = io.BytesIO(file.read())
                                                cache_msg = MessageSegment.image(io_file)
                                                msg += cache_msg
                                                cache_push_style = cache_push_style.removeprefix("[绘图]")
                                            elif cache_push_style.startswith("[标题]"):
                                                text = biliname + "正在直播："
                                                cache_msg = MessageSegment.text(text)
                                                msg += cache_msg
                                                cache_push_style = cache_push_style.removeprefix("[标题]")
                                            elif cache_push_style.startswith("[链接]"):
                                                cache_msg = MessageSegment.text(message_url)
                                                msg += cache_msg
                                                cache_push_style = cache_push_style.removeprefix("[链接]")
                                            elif cache_push_style.startswith("[内容]"):
                                                cache_msg = MessageSegment.text(message_title)
                                                msg += cache_msg
                                                cache_push_style = cache_push_style.removeprefix("[内容]")
                                            elif cache_push_style.startswith("[图片]"):
                                                # 无图片，待前面增加代码记录图片内容
                                                cache_push_style = cache_push_style.removeprefix("[图片]")
                                            elif cache_push_style == "":
                                                num = 0
                                            else:
                                                logger.error("读取动态推送样式出错，请检查配置是否正确")
                                    else:
                                        msg = MessageSegment.text(biliname + "已下播")

                                    # 检测是否需要at全体成员
                                    if plugin_config("at_all", groupcode) is True and "p" not in groupcode:
                                        can_at_all = int((await nonebot.get_bot(botid).get_group_at_all_remain(
                                            group_id=int(groupcode[1:])))["remain_at_all_count_for_uin"])
                                        if can_at_all > 0:
                                            pass
                                            # 代码需要验证
                                            # msg = MessageSegment.at("all") + msg

                                    stime = random.randint(1, 200) / 10 + sleeptime

                                    if now_maximum_send > 0:
                                        if "p" in groupcode:
                                            send_qq = groupcode.removeprefix("gp")
                                            if send_qq in friendlist:
                                                # bot已添加好友，发送消息
                                                try:
                                                    if new_push is not True:
                                                        now_maximum_send -= 1
                                                        await nonebot.get_bot(botid).send_private_msg(user_id=send_qq,
                                                                                                      message=msg)
                                                        logger.debug("发送私聊成功")
                                                        await asyncio.sleep(stime)
                                                    if new_push is True and state != "0":  # 第一次推送且是下播时不推送
                                                        now_maximum_send -= 1
                                                        await nonebot.get_bot(botid).send_private_msg(user_id=send_qq,
                                                                                                      message=msg)
                                                        logger.debug("发送私聊成功")
                                                        await asyncio.sleep(stime)
                                                    conn = sqlite3.connect(livedb)
                                                    cursor = conn.cursor()
                                                    cursor.execute(
                                                        "replace into 'gp" + send_qq + "'(dynamicid,uid) "
                                                                                       "values('live" + uid + "','" + state + "')")
                                                    cursor.close()
                                                    conn.commit()
                                                    conn.close()

                                                except Exception as e:
                                                    logger.error(
                                                        f'私聊内容发送失败：send_qq：{send_qq},message:{message},'
                                                        f'retrnpath:{returnpath}')
                                            else:
                                                logger.debug("bot未入群")
                                        else:
                                            send_groupcode = groupcode.removeprefix("g")
                                            if send_groupcode in grouplist:
                                                # bot已添加好友，发送消息
                                                try:
                                                    if new_push is not True:  # 第一次推送且是下播时不推送
                                                        now_maximum_send -= 1
                                                        await nonebot.get_bot(botid).send_group_msg(
                                                            group_id=send_groupcode,
                                                            message=msg)
                                                        logger.debug("发送群聊成功")
                                                        await asyncio.sleep(stime)
                                                    if new_push is True and state != "0":  # 第一次推送且是下播时不推送
                                                        now_maximum_send -= 1
                                                        await nonebot.get_bot(botid).send_group_msg(
                                                            group_id=send_groupcode,
                                                            message=msg)
                                                        logger.debug("发送群聊成功")
                                                        await asyncio.sleep(stime)
                                                    conn = sqlite3.connect(livedb)
                                                    cursor = conn.cursor()
                                                    cursor.execute(
                                                        "replace into 'g" + send_groupcode + "'(dynamicid,uid) " +
                                                        "values('live" + uid + "','" + state + "')")
                                                    cursor.close()
                                                    conn.commit()
                                                    conn.close()
                                                except Exception as e:
                                                    logger.error(
                                                        f"群聊内容发送失败：groupcode：{send_groupcode},message:{message}"
                                                        f",retrnpath:{returnpath}")
                                            else:
                                                logger.debug("bot未入群")

        # ############推送动态############
        run = True  # 代码折叠
        if run:
            logger.info("推送动态")
            conn = sqlite3.connect(livedb)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptionlist3")
            subscriptions = cursor.fetchall()
            cursor.close()
            conn.commit()
            conn.close()

            if not subscriptions:
                logger.debug("无订阅")
            else:
                for subscription in subscriptions:
                    groupcode = subscription[1]
                    uid = str(subscription[2])
                    # 判断是否本bot以及是否主bot
                    send = True
                    if plugin_config("bilipush_botswift", groupcode):
                        # 读取主bot
                        send = False

                        conn = sqlite3.connect(heartdb)
                        cursor = conn.cursor()
                        # 数据库列表转为序列
                        cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
                        datas = cursor.fetchall()
                        tables = []
                        for data in datas:
                            if data[1] != "sqlite_sequence":
                                tables.append(data[1])
                        if groupcode not in tables:
                            cursor.execute(
                                f'create table {groupcode}(botid VARCHAR(10) primary key, permission VARCHAR(20))')
                        if "heart" not in tables:
                            cursor.execute(
                                'create table heart(botid VARCHAR(10) primary key, breattime VARCHAR(10), '
                                'number VARCHAR(10))')
                        cursor.execute(f'SELECT * FROM {groupcode} WHERE permission = "10"')
                        group_data = cursor.fetchone()
                        cursor.close()
                        conn.commit()
                        conn.close()

                        if group_data is None:
                            conn = sqlite3.connect(heartdb)
                            cursor = conn.cursor()
                            cursor.execute(f'replace into {groupcode}(botid,permission) values("{botid}","10")')
                            cursor.close()
                            conn.commit()
                            conn.close()

                            send = True
                        else:
                            if group_data[0] == botid:
                                send = True
                            else:
                                conn = sqlite3.connect(heartdb)
                                cursor = conn.cursor()
                                cursor.execute('select * from heart where botid = ' + str(group_data[0]))
                                data = cursor.fetchone()
                                cursor.close()
                                conn.close()

                                if data is not None:
                                    if int(data[2]) >= 5:
                                        send = True

                                conn = sqlite3.connect(heartdb)
                                cursor = conn.cursor()
                                cursor.execute('SELECT * FROM ' + groupcode + ' WHERE permission = "5"')
                                data = cursor.fetchone()
                                cursor.close()
                                conn.close()
                                if data is None:
                                    conn = sqlite3.connect(heartdb)
                                    cursor = conn.cursor()
                                    cursor.execute(
                                        'replace into ' + groupcode + '(botid,permission) values("' + botid + '","5")')
                                    cursor.close()
                                    conn.commit()
                                    conn.close()

                    # 检查是否是好友、是否入群
                    if groupcode.startswith("gp"):
                        if groupcode[2:] not in friendlist:
                            send = False
                    else:
                        if groupcode[1:] not in grouplist:
                            send = False

                    # 检查是否不推送动态或直播
                    if uid in plugin_config("ignore_dynamic_list", groupcode):
                        send = False

                    if send:
                        conn = sqlite3.connect(livedb)
                        cursor = conn.cursor()

                        cursor.execute("SELECT * FROM sqlite_master WHERE type='table'")
                        datas = cursor.fetchall()
                        # 数据库列表转为序列
                        tables = []
                        for data in datas:
                            if data[1] != "sqlite_sequence":
                                tables.append(data[1])
                        if groupcode not in tables:
                            cursor.execute(f"create table {groupcode} (dynamicid int(10) primary key, uid varchar(10))")
                        # 获取已推送的动态列表
                        cursor.execute("SELECT * FROM " + groupcode + " WHERE uid = " + uid)
                        pushed_datas = cursor.fetchall()
                        # 获取新动态列表
                        cursor.execute("SELECT * FROM 'wait_push2' WHERE uid = '" + uid + "'")
                        datas = cursor.fetchall()
                        cursor.close()
                        conn.commit()
                        conn.close()

                        # 计算未推送动态列表
                        dynamicids = []
                        for data in pushed_datas:
                            dynamicids.append(str(data[0]))

                        new_dynamicids = []
                        for data in datas:
                            new_dynamicids.append(str(data[0]))

                        pushlist = []
                        if not dynamicids:
                            conn = sqlite3.connect(livedb)
                            cursor = conn.cursor()
                            for data in datas:
                                cursor.execute(
                                    "replace into " + groupcode + "(dynamicid,uid) values(" +
                                    str(data[0]) + "," + str(data[1]) + ")")
                            cursor.close()
                            conn.commit()
                            conn.close()
                            if new_dynamicids:
                                pushlist.append(new_dynamicids[0])

                        elif dynamicids:

                            # 计算出未推送的动态
                            for new_dynamicid in new_dynamicids:
                                if new_dynamicid not in dynamicids:
                                    if len(pushlist) <= 2:  # 限制单次发送条数
                                        pushlist.append(new_dynamicid)
                        logger.debug("未推送的动态" + str(pushlist))

                        # 分别发送图片，并保存为已推送
                        for dynamicid in pushlist:
                            conn = sqlite3.connect(livedb)
                            cursor = conn.cursor()
                            cursor.execute(f"SELECT * FROM 'wait_push2' WHERE dynamicid = {dynamicid}")
                            data = cursor.fetchone()
                            cursor.close()
                            conn.commit()
                            conn.close()

                            draw_path = data[2]
                            message_title = data[3]
                            message_url = data[4]
                            message_body = data[5]
                            message_images = str(data[6])
                            message_images = message_images.replace("'", '"')
                            message_images = json.loads(message_images)["images"]

                            num = 10
                            cache_push_style = plugin_config("bilipush_push_style", groupcode)
                            msg = MessageSegment.text("")
                            while num > 0:
                                num -= 1
                                if cache_push_style.startswith("[绘图]"):
                                    file = open(draw_path, 'br')
                                    io_file = io.BytesIO(file.read())
                                    cache_msg = MessageSegment.image(io_file)
                                    msg += cache_msg
                                    cache_push_style = cache_push_style.removeprefix("[绘图]")
                                elif cache_push_style.startswith("[标题]"):
                                    cache_msg = MessageSegment.text(message_title)
                                    msg += cache_msg
                                    cache_push_style = cache_push_style.removeprefix("[标题]")
                                elif cache_push_style.startswith("[链接]"):
                                    cache_msg = MessageSegment.text(message_url)
                                    msg += cache_msg
                                    cache_push_style = cache_push_style.removeprefix("[链接]")
                                elif cache_push_style.startswith("[内容]"):
                                    cache_msg = MessageSegment.text(message_body)
                                    msg += cache_msg
                                    cache_push_style = cache_push_style.removeprefix("[内容]")
                                elif cache_push_style.startswith("[图片]"):
                                    num = 0
                                    for url in message_images:
                                        num += 1
                                        image = connect_api("image", url)
                                        image_path = f"{cachepath}{dynamicid}/"
                                        if not os.path.exists(image_path):
                                            os.makedirs(image_path)
                                        image_path += f"{num}.png"
                                        image.save(image_path)
                                        file = open(image_path, 'br')
                                        io_file = io.BytesIO(file.read())
                                        cache_msg = MessageSegment.image(io_file)
                                        msg += cache_msg
                                    cache_push_style = cache_push_style.removeprefix("[图片]")
                                elif cache_push_style == "":
                                    num = 0
                                else:
                                    logger.error("读取动态推送样式出错，请检查配置是否正确")

                            stime = random.randint(1, 200) / 10 + sleeptime
                            if "p" in groupcode:
                                send_qq = groupcode.removeprefix("gp")
                                if send_qq in friendlist:
                                    # bot已添加好友，发送消息
                                    try:
                                        await nonebot.get_bot(botid).send_private_msg(user_id=send_qq, message=msg)
                                        logger.debug("发送私聊成功")
                                    except Exception as e:
                                        logger.error(f"私聊内容发送失败：send_qq：{send_qq},"
                                                     f"message:{message},retrnpath:{draw_path}")
                                    conn = sqlite3.connect(livedb)
                                    cursor = conn.cursor()
                                    try:
                                        cursor.execute(
                                            f'replace into "gp{send_qq}"(dynamicid,uid) '
                                            f'values({dynamicid},{uid})')
                                    except Exception as e:
                                        logger.error(f"数据库出错：{e}")
                                    cursor.close()
                                    conn.commit()
                                    conn.close()
                                    await asyncio.sleep(stime)
                                else:
                                    logger.debug("bot未入群")
                            else:
                                send_groupcode = groupcode.removeprefix("g")
                                if send_groupcode in grouplist:
                                    # bot已添加好友，发送消息
                                    try:
                                        await nonebot.get_bot(botid).send_group_msg(group_id=send_groupcode, message=msg)
                                        logger.debug("发送群聊成功")
                                    except Exception as e:
                                        logger.error(f"群聊内容发送失败：groupcode：{send_groupcode},"
                                                     f"message:{message},retrnpath:{draw_path}")
                                    conn = sqlite3.connect(livedb)
                                    cursor = conn.cursor()
                                    try:
                                        cursor.execute(
                                            f'replace into "g{send_groupcode}"("dynamicid","uid") '
                                            f'values("{dynamicid}","{uid}")')
                                    except Exception as e:
                                        logger.error(f"数据库出错：{e}")
                                    cursor.close()
                                    conn.commit()
                                    conn.close()
                                    await asyncio.sleep(stime)
                                else:
                                    logger.debug("bot未入群")

    logger.debug("bili_push_runfinish")
    pass
