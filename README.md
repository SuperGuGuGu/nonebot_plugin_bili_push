# nonebot-plugin-bili-push

B 订阅推送插件

仅支持 OB11 适配器

(kook 适配器请前往另一个仓库查看，但不建议使用-[bili_push for kook](https://github.com/SuperGuGuGu/nonebot_plugin_bili_push_kook))

## 示例

    /添加订阅 349218897  # 订阅 uid为 349218897 的用户 （仅动态）
    /添加订阅 L12151156  # 订阅 直播间id为 12151156 的用户 （动态+直播）
    /删除订阅 349218897  # 删除订阅 uid为 349218897 的用户 （动态+直播）
    /删除订阅 L12151156  # 删除订阅 直播间id为 12151156 的用户 （动态+直播）
    /最新动态  # 查看该uid的最新动态
    /查看订阅  # 查看当前群聊的所有订阅。显示为uid
    /帮助 查看命令菜单

![输入图片描述](README_md_files/9cf89890-0952-11ee-8733-25d9c7397331.jpeg?v=1&type=image) ![输入图片描述](README_md_files/7fd7ee50-0952-11ee-8733-25d9c7397331.jpeg?v=1&type=image)

## 安装

（以下方法二选一）

一.命令行安装：

```python
nb plugin install nonebot-plugin-bili-push
```

二.pip 安装：

1.执行此命令

```python
pip install nonebot-plugin-bili-push
```

2.修改 pyproject.toml 使其可以加载插件

```python
plugins = [”nonebot-plugin-bili-push“]
```

## 配置

在 nonebot2 项目的`.env`文件中选填配置

1.配置管理员账户，只有管理员才能添加订阅

    SUPERUSERS=["12345678"] # 配置 NoneBot 超级用户

2.插件数据存放位置，默认为 “./”。

    bilipush_basepath="./"

3.命令前缀，默认为"/"

```markup
COMMAND_START=["/"]
```

详细配置方法- [详细配置](https://github.com/SuperGuGuGu/nonebot_plugin_bili_push/blob/master/Config.md)

## To-Do

🔵 接下来：

- [ ] 保存直播推送封面，推送样式修改

- [ ] 配置仅直播推送或仅动态推送

- [ ] 开播添加 at 全体成员

- [ ] 对话式配置

- [ ] 推送黑名单（识别到文字或类型的时候不进行推送）

- [ ] 完善动态类型（目前仅支持文字、图文、视频、转发、文章）

- [ ] 字体排版优化（字符位置以及）

- [ ] 自动修改“只响应一个 bot”数据，以及不推送时加提醒

- [ ] 添加话题标签

- [ ] 添加动态底部相关的内容绘制（游戏、动漫、视频）

- [ ] 版面优化

- [ ] ~~增加多种适配器连接（无限期延迟~~

- [ ] ~~将请求 api 改为异步（无限期延迟~~

🟢 已完成：

- [x] 修复直播订阅

- [x] 对海外服务器支持

- [x] 配置推送样式

- [x] 设置默认字体。在禁用 插件 api 的时候使用默认字体

- [x] 单 nb 对接多 q 的兼容

## 灵感来源

Mirai 动态绘制插件 [BilibiliDynamic MiraiPlugin](https://github.com/Colter23/bilibili-dynamic-mirai-plugin)

## 交流

- 交流群[鸽子窝里有鸽子（291788927）](https://qm.qq.com/cgi-bin/qm/qr?k=QhOk7Z2jaXBOnAFfRafEy9g5WoiETQhy&jump_from=webapi&authKey=fCvx/auG+QynlI8bcFNs4Csr2soR8UjzuwLqrDN9F8LDwJrwePKoe89psqpozg/m)

- 有疑问或者建议都可以进群唠嗑唠嗑。
