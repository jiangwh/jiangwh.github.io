# Dashboard 命令

## 简单介绍

dashboard命令主要用户查看目标进程的概况信息，主要包括线程、内存、GC等。

```bash
dashboard
```

## 相关源码

1、线程信息的获取

```java
public static Map<String, Thread> getThreads() {
  			//通过当前线程获取group信息，然后再获取group的parent信息，直至找到root信息。
        ThreadGroup root = getRoot(); 
        Thread[] threads = new Thread[root.activeCount()];
        while (root.enumerate(threads, true) == threads.length) {
            threads = new Thread[threads.length * 2];
        }
        SortedMap<String, Thread> map = new TreeMap<String, Thread>(new Comparator<String>() {
            @Override
            public int compare(String o1, String o2) {
                return o1.compareTo(o2);
            }
        });
  			//线程存放到map之后返回。
        for (Thread thread : threads) {
            if (thread != null) {
                map.put(thread.getName() + "-" + thread.getId(), thread);
            }
        }
        return map;
    }

```

2、内存信息的获取

```java
 private static void addMemoryInfo(TableElement table) {
   			//通过mbean获取heap的使用情况
        MemoryUsage heapMemoryUsage = ManagementFactory.getMemoryMXBean().getHeapMemoryUsage();
        MemoryUsage nonHeapMemoryUsage = ManagementFactory.getMemoryMXBean().getNonHeapMemoryUsage();

        List<MemoryPoolMXBean> memoryPoolMXBeans = ManagementFactory.getMemoryPoolMXBeans();

        new MemoryEntry("heap", heapMemoryUsage).addTableRow(table, Decoration.bold.bold());
        for (MemoryPoolMXBean poolMXBean : memoryPoolMXBeans) {
            if (MemoryType.HEAP.equals(poolMXBean.getType())) {
                MemoryUsage usage = poolMXBean.getUsage();
                String poolName = beautifyName(poolMXBean.getName());
                new MemoryEntry(poolName, usage).addTableRow(table);
            }
        }

        new MemoryEntry("nonheap", nonHeapMemoryUsage).addTableRow(table, Decoration.bold.bold());
        for (MemoryPoolMXBean poolMXBean : memoryPoolMXBeans) {
            if (MemoryType.NON_HEAP.equals(poolMXBean.getType())) {
                MemoryUsage usage = poolMXBean.getUsage();
                String poolName = beautifyName(poolMXBean.getName());
                new MemoryEntry(poolName, usage).addTableRow(table);
            }
        }

        addBufferPoolMemoryInfo(table);
    }

///////////
 private static void addBufferPoolMemoryInfo(TableElement table) {
        try {
            @SuppressWarnings("rawtypes")
            Class bufferPoolMXBeanClass = Class.forName("java.lang.management.BufferPoolMXBean");
            @SuppressWarnings("unchecked")
            List<BufferPoolMXBean> bufferPoolMXBeans = ManagementFactory.getPlatformMXBeans(bufferPoolMXBeanClass);
            for (BufferPoolMXBean mbean : bufferPoolMXBeans) {
                long used = mbean.getMemoryUsed();
                long total = mbean.getTotalCapacity();
                new MemoryEntry(mbean.getName(), used, total, Long.MIN_VALUE).addTableRow(table);
            }
        } catch (ClassNotFoundException e) {
            // ignore
        }
    }
```

3、GC信息的获取

```java
    private static void addGcInfo(TableElement table) {
      	//通过gc的mbean获取gc相关信息。
        List<GarbageCollectorMXBean> garbageCollectorMxBeans = ManagementFactory.getGarbageCollectorMXBeans();
        for (GarbageCollectorMXBean garbageCollectorMXBean : garbageCollectorMxBeans) {
            String name = garbageCollectorMXBean.getName();
            table.add(new RowElement().style(Decoration.bold.bold()).add("gc." + beautifyName(name) + ".count",
                    "" + garbageCollectorMXBean.getCollectionCount()));
            table.row("gc." + beautifyName(name) + ".time(ms)", "" + garbageCollectorMXBean.getCollectionTime());
        }
    }
```

## 总结

arthas 的 dashbroad中获取的信息主要通过:

1、thread group

2、mbean

```
java.lang.management.BufferPoolMXBean;
java.lang.management.GarbageCollectorMXBean;
java.lang.management.ManagementFactory;
java.lang.management.MemoryPoolMXBean;
java.lang.management.MemoryType;
java.lang.management.MemoryUsage;
```

来获取相关信息，作为目标进程的概览信息。