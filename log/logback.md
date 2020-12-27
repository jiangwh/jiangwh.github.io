# logback的使用

​	logback是我们常用的日志框架，但是我们正常都是直接复制配置文件，从未了解过logback框架本身。最近遇到一个需求，需要将日志加密处理，发现logback是一个非常灵活的日志框架。因此记录下该日志框架的强大。

## 配置示例

```xml
<configuration>
  <!-- jvm shutdownhook -->
  <shutdownHook/>
  <!-- condition -->
  <if condition='property("HOSTNAME").contains("torino")'>
    <then>
      <appender name="CON" class="ch.qos.logback.core.ConsoleAppender">
        <encoder>
          <pattern>%d %-5level %logger{35} - %msg %n</pattern>
        </encoder>
      </appender>
      <root>
        <appender-ref ref="CON" />
      </root>
    </then>
  </if>
  
  <include file="src/main/java/includedConfig.xml"/> <!-- include config that define the append -->
  <include resource="includedConfig.xml"/>
  <include url="http://some.host.com/includedConfig.xml"/>
    
  <!-- define the message converter -->
  <conversionRule conversionWord="cvt" converterClass="com.jiangwh.MyConverter" />
        
  <appender name="STDOUT" class="ch.qos.logback.core.ConsoleAppender">
    <!-- encoders are assigned the type
         ch.qos.logback.classic.encoder.PatternLayoutEncoder by default -->
    <encoder> <!-- the class att can define encoder -->
        <layout>
      		<pattern>%d{HH:mm:ss.SSS} [%thread] %-5level %logger{36} - %cvt{%msg}%n</pattern>
        </layout>
    </encoder>
  </appender>
    
  <logger name="com.jiangwh" level="INFO"/> <!-- define the logger level in the specific package -->
  <root level="debug">
    <appender-ref ref="STDOUT" />
  </root>
    
    
  
</configuration>
```

