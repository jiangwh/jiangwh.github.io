# Spring Bean 的销毁

我们在spring管理的bean中可以增加```@PreDestroy ```注解，来实现在jvm正常退出时，继续一些工作。

我们对jvm的正常退出解释：
1、代码中调用了```System.exit(status)```方法。
2、使用ctrl + c 命令关闭
3、使用kill命令（kill -9 是直接关闭，非常暴力，不会调用销毁方法）
上面这些关闭方式对我们的程序来很少使用，我们的应用经常会由于oom导致异常，导致业务不正常。因此可以使用 ```OnOutOfMemoryError``` 参数，让jvm在oom时触发调用命令。让该命令来kill当前进程（重启）。
```java -Xmx64m -Xms64m -XX:+HeapDumpOnOutOfMemoryError -XX:OnOutOfMemoryError="sh ./shutdown.sh" -jar name.jar```

赠送一个kill脚本。
```bash
#!/bin/bash
ps -ef | grep .jar | grep java | awk '{print $2}' | xargs kill

# jvm exist with exec commads
#java -Xmx64m -Xms64m -XX:+HeapDumpOnOutOfMemoryError -XX:OnOutOfMemoryError="sh ./shutdown.sh" -jar name.jar
# oom exit
#java -Xmx64m -Xms64m -XX:+HeapDumpOnOutOfMemoryError -XX:+ExitOnOutOfMemoryError -jar name.jar
#java -Xmx64m -Xms64m -XX:+HeapDumpOnOutOfMemoryError -XX:+CrashOnOutOfMemoryError -jar name.jar

```
## 简单示例


## Spring触发销毁bean

Spring 在refreshContext阶段，注册完成bean以及事件，注册一个shudown hook。

```java
	//启动过程中增加销毁hook
	private void refreshContext(ConfigurableApplicationContext context) {
		refresh(context);
		if (this.registerShutdownHook) {
			try {
				context.registerShutdownHook();
			}
			catch (AccessControlException ex) {
				// Not allowed in some environments.
			}
		}
	}
```

```java
@Override
	public void registerShutdownHook() {
		if (this.shutdownHook == null) {
			// No shutdown hook registered yet.
			this.shutdownHook = new Thread() {
				@Override
				public void run() {
					synchronized (startupShutdownMonitor) {
            			//发布时间 ContextClosedEvent
						//调用所有bean中增加destroy注解的方法
						doClose();
					}
				}
			};
			//注册shudown hook
			Runtime.getRuntime().addShutdownHook(this.shutdownHook);
		}
	}
```

