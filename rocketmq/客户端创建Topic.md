# 客户端创建Topic
1、topic的名字规则 ^[%|a-zA-Z0-9_-]+$
2、topic的长度限制 127

相关步骤：
1、通过集群名字获取topic的路由信息，一个topic会分布在多个broken上面。
2、对获取的broken信息发布topic信息。

