# Hystrix

## 简单的示例

```java
public static void main(String[] args) throws InterruptedException {
		HystrixCommandGroupKey key = HystrixCommandGroupKey.Factory.asKey("cmd");
		HystrixCommand.Setter setter = HystrixCommand.Setter.withGroupKey(key);
		/////////////////////////////////////////
		HystrixCommandProperties.Setter proSetter = HystrixCommandProperties.defaultSetter();
		proSetter.withCircuitBreakerEnabled(true);
		proSetter.withExecutionIsolationStrategy(HystrixCommandProperties.ExecutionIsolationStrategy.SEMAPHORE);
		proSetter.withExecutionTimeoutEnabled(true);
		proSetter.withExecutionIsolationSemaphoreMaxConcurrentRequests(2);
		proSetter.withExecutionIsolationThreadInterruptOnTimeout(true);
		proSetter.withExecutionTimeoutInMilliseconds(5 * 1000);
		setter.andCommandPropertiesDefaults(proSetter);

		/////////////////////////////////////////
		HystrixThreadPoolProperties.Setter threadSetter = HystrixThreadPoolProperties.defaultSetter();

		setter.andThreadPoolPropertiesDefaults(threadSetter);

		HystrixCommand<String> hystrixCommand = new HystrixCommand<String>(setter) {
			@Override
			protected String run() throws Exception {
				return "finish";
			}

			@Override
			protected String getFallback() {
				return "fallback";
			}
		};

		String res = hystrixCommand.execute();
		System.out.println(res);

	}
```

利用hystrix可以实现限流、熔断、降低的操作，下面具体介绍下。

## 限流

### 限流策略

hystrix中提供了两种限流的策略。

- THREAD

- SEMAPHORE

Thread策略，就使用thread pool的队列size 以及 线程池数量来控制请求并发量。

```java
 /* package */static class HystrixThreadPoolDefault implements HystrixThreadPool {
        private static final Logger logger = LoggerFactory.getLogger(HystrixThreadPoolDefault.class);

        private final HystrixThreadPoolProperties properties;
        private final BlockingQueue<Runnable> queue;
        private final ThreadPoolExecutor threadPool;
        private final HystrixThreadPoolMetrics metrics;
        private final int queueSize;
   
 }
//ThreadPool 创建的方式
public ThreadPoolExecutor getThreadPool(final HystrixThreadPoolKey threadPoolKey, HystrixThreadPoolProperties threadPoolProperties) {
        final ThreadFactory threadFactory = getThreadFactory(threadPoolKey);

        final boolean allowMaximumSizeToDivergeFromCoreSize = threadPoolProperties.getAllowMaximumSizeToDivergeFromCoreSize().get();
        final int dynamicCoreSize = threadPoolProperties.coreSize().get();
        final int keepAliveTime = threadPoolProperties.keepAliveTimeMinutes().get();
        final int maxQueueSize = threadPoolProperties.maxQueueSize().get();
        final BlockingQueue<Runnable> workQueue = getBlockingQueue(maxQueueSize);

        if (allowMaximumSizeToDivergeFromCoreSize) {
            final int dynamicMaximumSize = threadPoolProperties.maximumSize().get();
            if (dynamicCoreSize > dynamicMaximumSize) {
                logger.error("Hystrix ThreadPool configuration at startup for : " + threadPoolKey.name() + " is trying to set coreSize = " +
                        dynamicCoreSize + " and maximumSize = " + dynamicMaximumSize + ".  Maximum size will be set to " +
                        dynamicCoreSize + ", the coreSize value, since it must be equal to or greater than the coreSize value");
                return new ThreadPoolExecutor(dynamicCoreSize, dynamicCoreSize, keepAliveTime, TimeUnit.MINUTES, workQueue, threadFactory);
            } else {
                return new ThreadPoolExecutor(dynamicCoreSize, dynamicMaximumSize, keepAliveTime, TimeUnit.MINUTES, workQueue, threadFactory);
            }
        } else {
            return new ThreadPoolExecutor(dynamicCoreSize, dynamicCoreSize, keepAliveTime, TimeUnit.MINUTES, workQueue, threadFactory);
        }
    }
```



Semaphore策略，需要将thread pool的队列size设置为无限（Integer.MAX_VALUE）,然后ConcurrentHashMap、TryableSemaphore.tryAcquire()方法来控制并发。

```java
//获取semaphore
protected TryableSemaphore getExecutionSemaphore() {
        if (properties.executionIsolationStrategy().get() == ExecutionIsolationStrategy.SEMAPHORE) {
            if (executionSemaphoreOverride == null) {
                TryableSemaphore _s = executionSemaphorePerCircuit.get(commandKey.name());
                if (_s == null) {
                    // we didn't find one cache so setup
                    executionSemaphorePerCircuit.putIfAbsent(commandKey.name(), new TryableSemaphoreActual(properties.executionIsolationSemaphoreMaxConcurrentRequests()));
                    // assign whatever got set (this or another thread)
                    return executionSemaphorePerCircuit.get(commandKey.name());
                } else {
                    return _s;
                }
            } else {
                return executionSemaphoreOverride;
            }
        } else {
            // return NoOp implementation since we're not using SEMAPHORE isolation
            return TryableSemaphoreNoOp.DEFAULT;
        }
    }
//执行
private Observable<R> applyHystrixSemantics(final AbstractCommand<R> _cmd) {
        // mark that we're starting execution on the ExecutionHook
        // if this hook throws an exception, then a fast-fail occurs with no fallback.  No state is left inconsistent
        executionHook.onStart(_cmd);

        /* determine if we're allowed to execute */
        if (circuitBreaker.allowRequest()) {
            final TryableSemaphore executionSemaphore = getExecutionSemaphore();
            final AtomicBoolean semaphoreHasBeenReleased = new AtomicBoolean(false);
            final Action0 singleSemaphoreRelease = new Action0() {
                @Override
                public void call() {
                    if (semaphoreHasBeenReleased.compareAndSet(false, true)) {
                        executionSemaphore.release();
                    }
                }
            };

            final Action1<Throwable> markExceptionThrown = new Action1<Throwable>() {
                @Override
                public void call(Throwable t) {
                    eventNotifier.markEvent(HystrixEventType.EXCEPTION_THROWN, commandKey);
                }
            };

            if (executionSemaphore.tryAcquire()) {
                try {
                    /* used to track userThreadExecutionTime */
                    executionResult = executionResult.setInvocationStartTime(System.currentTimeMillis());
                    return executeCommandAndObserve(_cmd)
                            .doOnError(markExceptionThrown)
                            .doOnTerminate(singleSemaphoreRelease)
                            .doOnUnsubscribe(singleSemaphoreRelease);
                } catch (RuntimeException e) {
                    return Observable.error(e);
                }
            } else {
                return handleSemaphoreRejectionViaFallback();
            }
        } else {
            return handleShortCircuitViaFallback();
        }
    }

```

