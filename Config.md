# 配置

## 全局配置

1.推送样式

> 动态的推送样式 可配置选项：\[绘图]\[标题]\[链接]\[内容]\[图片]

```markup
bilipush_push_style="[绘图][标题][链接]"
```

2.刷新间隔：

> 每次刷新间隔多少分钟，默认为 12 分钟。

```markup
bilipush_waittime=12
```

3.发送间隔：

> 每次发送完成后等待的时间，单位秒，默认 10-30 秒。 时间为设置的时间再加上随机延迟 1-20 秒

```markup
bilipush_sleeptime=10
```

4.最大发送数量

> 限制单次发送数量，防止一次性发送太多图导致风控。 默认 5 条

```markup
bilipush_maximum_send=5

```

5.自动删除缓存

> 自动删除2天前的动态缓存

```
bilipush_remove_cache=true

```

6.其他配置项

> 只响应一个 bot 一个群内有多个 bot，可以只让 1 个 bot 推送消息。 默认为关闭该功能，既所有 bot 都会响应 （正在考虑是否改为默认开启，如不需要请关闭该功能）

```markup
bilipush_botswift=false
```

> 是否使用花音的 api 来支持更丰富的内容
>
> 默认开启。如出现连接不上或其他故障，请尝试关闭。

```markup
bilipush_emojiapi=true
```

> 配置 api 地址，如未填写则使用默认地址。

```markup
bilipush_apiurl="http://cdn.kanon.ink"
```

## 群内配置项

```markup
# 设置的群号
# 注意：需要在群号前面添加字母g
[g123456789]

# 群内插件管理员。可以用于"增减管理员"命令以外的所有命令。
group_admin=["123456", "111111", "222222"]

# 只响应一个 bot功能。默认关闭
bilipush_botswift=false

# 群内命令前缀。配置后将忽略全局配置。
group_command_starts=["/"]

# 群内推送样式。
bilipush_push_style="[绘图][标题][链接]"

# at所有成员。默认关闭（未上线功能，开启不会有任何效果）
at_all=false

# 群内忽略直播推送列表
# 配置后将忽略以下uid的直播推送
ignore_live_list=["2", "111111", "222222"]

# 群内忽略动态推送列表
# 配置后将忽略以下uid的动态推送
ignore_dynamic_list=["2", "111111", "222222"]


[plugin]
cookies_SESSDATA="T123TEXT"
cookies_bili_jct="T123TEXT"

```

