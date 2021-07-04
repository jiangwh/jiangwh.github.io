# nginx-controllers

## docker images

镜像文件处理：

1、采用多阶段构建的方式

2、安装lua环境

```bash
ENV LUA_PATH="/usr/local/share/luajit-2.1.0-beta3/?.lua;/usr/local/share/lua/5.1/?.lua;/usr/local/lib/lua/?.lua;;"
ENV LUA_CPATH="/usr/local/lib/lua/?/?.so;/usr/local/lib/lua/?.so;;"
```

lua实现了负载均衡相关策略：包括随机、balancer_sticky。

3、模版方式



## 配置变更

nginx的配置可以来自多处的变更

1、configmap

2、annotation

3、secret

4、ingress

5、svc

6、ep

## 配置存储

通过store将相关配置更新

## 网络

ipvs/iptable 转发



