# H2 Code Snappet

## 对Int型的新认知

```java
    public int getDefaultRetentionTime() {
        return 45_000; //int类型中间是可以增加_
    }
```

## JMX MBean

```java

public static void registerMBean(ConnectionInfo connectionInfo,
            Database database) throws JMException {
        String path = connectionInfo.getName();
        if (!MBEANS.containsKey(path)) {
            MBeanServer mbeanServer = ManagementFactory.getPlatformMBeanServer();
            String name = database.getShortName();
            ObjectName mbeanObjectName = getObjectName(name, path);
            MBEANS.put(path, mbeanObjectName);
            DatabaseInfo info = new DatabaseInfo(database);
            Object mbean = new DocumentedMBean(info, DatabaseInfoMBean.class);
            mbeanServer.registerMBean(mbean, mbeanObjectName);
        }
    }

public class DocumentedMBean extends StandardMBean {
    /*extends a standardMBean*/
}
```

