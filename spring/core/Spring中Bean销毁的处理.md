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
Spring Bean 中的可以定义多个销毁的方法，执行销毁方法的顺序，按照方法在类中的顺序。
这些销毁方法不能携带任何参数。


## 简单示例

```java
@Component
@Getter
@Slf4j
public class MessageContainer {
	private static final int CAP = Integer.MAX_VALUE;

	private LinkedBlockingQueue<WrapperEvent> messageQueue;

	private CopyOnWriteArrayList<WrapperEvent> delayEvent;

	@Autowired
	QueueModelRepository repository;

	@PostConstruct
	public void initContainer() {
    //在容器初始化时，加载数据库持久化消息。
		log.info("init message container");
		List<QueueModel> queueModelList = repository.findAll();
		messageQueue = Queues.newLinkedBlockingQueue(CAP);
		delayEvent = Lists.newCopyOnWriteArrayList();
		if (null != queueModelList && queueModelList.size() > 0) {
			queueModelList.forEach(q -> {
				messageQueue.addAll(q.getQueue());
				delayEvent.addAll(q.getEvent());
			});
			repository.deleteAll();
		}
	}

	@PreDestroy
	public void destroyContainer() {
    //容器销毁时持久化未处理的消息。
		log.info("destroy message container");
		QueueModel queueModel = QueueModel.builder().queue(messageQueue).event(delayEvent).build();
		repository.save(queueModel);
		messageQueue.clear();
		delayEvent.clear();
	}
}
```




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

```java
		/*共调用的初始化方法 在docreate阶段调用*/
		public void invokeInitMethods(Object target, String beanName) throws Throwable {
			Collection<LifecycleElement> checkedInitMethods = this.checkedInitMethods;
			Collection<LifecycleElement> initMethodsToIterate =
					(checkedInitMethods != null ? checkedInitMethods : this.initMethods);
			if (!initMethodsToIterate.isEmpty()) {
				for (LifecycleElement element : initMethodsToIterate) {
					if (logger.isTraceEnabled()) {
						logger.trace("Invoking init method on bean '" + beanName + "': " + element.getMethod());
					}
					element.invoke(target);
				}
			}
		}

		public void invokeDestroyMethods(Object target, String beanName) throws Throwable {
			Collection<LifecycleElement> checkedDestroyMethods = this.checkedDestroyMethods;
			Collection<LifecycleElement> destroyMethodsToUse =
					(checkedDestroyMethods != null ? checkedDestroyMethods : this.destroyMethods);
			if (!destroyMethodsToUse.isEmpty()) {
				for (LifecycleElement element : destroyMethodsToUse) {
					if (logger.isTraceEnabled()) {
						logger.trace("Invoking destroy method on bean '" + beanName + "': " + element.getMethod());
					}
					element.invoke(target);
				}
			}
		}

```

执行方法顺序的源码
```java
Method[] methods = getDeclaredMethods(clazz);
for (Method method : methods) {
			try {
				mc.doWith(method);
			}
			catch (IllegalAccessException ex) {
				throw new IllegalStateException("Not allowed to access method '" + method.getName() + "': " + ex);
			}
		}
		/**doWith 使用的表达式*/
		method -> {
				if (this.initAnnotationType != null && method.isAnnotationPresent(this.initAnnotationType)) {
					LifecycleElement element = new LifecycleElement(method);
					currInitMethods.add(element);
					if (logger.isTraceEnabled()) {
						logger.trace("Found init method on class [" + clazz.getName() + "]: " + method);
					}
				}
				if (this.destroyAnnotationType != null && method.isAnnotationPresent(this.destroyAnnotationType)) {
					currDestroyMethods.add(new LifecycleElement(method));
					if (logger.isTraceEnabled()) {
						logger.trace("Found destroy method on class [" + clazz.getName() + "]: " + method);
					}
				}
			}
```

