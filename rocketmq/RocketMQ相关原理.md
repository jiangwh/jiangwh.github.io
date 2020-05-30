# RocketMQ相关原理

“RocketMQ是一个统一的消息引擎，轻量级的数据处理平台“这是引用官方的描述。我还是习惯称为：消息中间件。



## RocketMQ的简单介绍

### rocketmq的架构

![img](http://rocketmq.apache.org/assets/images/rmq-basic-arc.png)

rocketmq支持nameserver的集群（各个nameserver上面的数据是完成一致的，主要是通过客户端进行负载均衡）。

broken也支持集群部署的，通过master、slave的方式集群。broken的信息是完全同步备份的。broken对消息的处理通过store层处理，store层的消息通过raft算法保证集群数据的同步。

rocketmq底层消息通过netty进行进行通信。

## namesvr集群

namesvr是一个简单的服务注册的服务。



## broken集群

broken 可以支持多个master模式、2-master 2-salve模式……

broken的角色切换主要是依赖DLedgerServer角色切换，触发broken中角色切换(在4.5.1版本之后存在该功能，之前的功能没有角色切换)。



