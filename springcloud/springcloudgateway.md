# 定义路由

增加Normal路由信息

```bash
curl -X POST -H "Content-Type: application/json"  -d '{"id":"sina","predicates":[{"args":{"_genkey_2":"/sina/**"},"name":"Path"}],"filters":[],"uri":"https://www.sina.com","order":"2"}' 127.0.0.1:8080/actuator/gateway/routes/sina
```

定义查询路由信息

```bash
curl -X POST -H "Content-Type: application/json"  -d '{"id":"sina","predicates":[{"args":{"param":"s","regexp":"1"},"name":"Query"}],"filters":[],"uri":"https://www.baidu.com","order":"1"}' 127.0.0.1:8080/actuator/gateway/routes/sina
```



增加fallback路由

```bash
curl -X POST -H "Content-Type: application/json"  -d '{"id":"sina","predicates":[{"args":{"_genkey_2":"/sina/**"},"name":"Path"}],"filters":[{"args":{"name":"fallbackcmd","fallbackUri" :"forward:/hystrixfallback"},"name":"Hystrix"}],"uri":"https://www.sccina.com","order":"2"}' 127.0.0.1:8080/actuator/gateway/routes/sina -vvv
```

增加域名 路径匹配

```bash
curl -X POST -H "Content-Type: application/json"  -d '{"id":"sina","predicates":[{"args":{"_genkey_2":"/baidu/**"},"name":"Path"},{"args":{"_genkey_3":"www.baidu.com"},"name":"Host"}],"filters":[],"uri":"https://www.baidu.com","order":"1"}' 127.0.0.1:8080/actuator/gateway/routes/sina
```

路径重写

```bash
curl -X POST -H "Content-Type: application/json"  -d '{"id":"sina","predicates":[{"args":{"_genkey_2":"/baidu/**"},"name":"Path"}],"filters":[{"name":"RewritePath","args":{"regexp":"/baidu","replacement":"/"}}],"uri":"https://www.baidu.com","order":"1"}' 127.0.0.1:8080/actuator/gateway/routes/sina
```



## 如何确定filter或者predicate的参数

```java
//HystrixGatewayFilterFactory
//转为map
public static class Config {
		private String name;
		private Setter setter;
		private URI fallbackUri;
}

//QueryRoutePredicateFactory
public static class Config {
		@NotEmpty
		private String param;
		private String regexp;
}
```

