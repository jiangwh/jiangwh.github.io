# Spring Core 

Spring core后续文中称为核心技术。

核心技术主要包括了：ioc容器、资源加载、数据验证绑定和类型转换、SPEL、AOP、空安全、数据缓存以及编解码。

## IOC 容器

org.springframework.context.ApplicationContext

1、初始化

2、配置

3、封装bean

如果使用xml配置，可以通过ClassPathXmlApplicationContext、FileSystemXmlApplicationContext来初始化IOC容器。



bean

| Property                 | Explained in…                                                |
| :----------------------- | :----------------------------------------------------------- |
| Class                    | [Instantiating Beans](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-factory-class) |
| Name                     | [Naming Beans](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-beanname) |
| Scope                    | [Bean Scopes](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-factory-scopes) |
| Constructor arguments    | [Dependency Injection](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-factory-collaborators) |
| Properties               | [Dependency Injection](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-factory-collaborators) |
| Autowiring mode          | [Autowiring Collaborators](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-factory-autowire) |
| Lazy initialization mode | [Lazy-initialized Beans](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-factory-lazy-init) |
| Initialization method    | [Initialization Callbacks](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-factory-lifecycle-initializingbean) |
| Destruction method       | [Destruction Callbacks](https://docs.spring.io/spring-framework/docs/current/spring-framework-reference/core.html#beans-factory-lifecycle-disposablebe) |



## 资源处理

### 内置资源加载类

#### UrlResoure



#### FileUrlResource



#### ClassPathResource



#### ByteArrayResource



### ResourceLoader



## 验证、数据绑定、类型转换



## SPEL



## AOP

面向切面的编程。



## 空安全

### @Nullable



### @NonNull

lombok的@Builder注解支持，判断增加了@NonNull注解的字段不能为null。可能为lombok的bug??

### @NonNullApi



### @NonNullFields



## 数据缓冲以及编解码

