# Arthas 中日志级别的处理

```bash
logger --name ROOT --level debug
```

## 更新日志级别

```java
public void level(CommandProcess process) {
        Instrumentation inst = process.session().getInstrumentation();
        boolean result = false;
        try {
          	//更新log4j日志级别
            Boolean updateResult = this.updateLevel(inst, Log4jHelper.class);
            if (Boolean.TRUE.equals(updateResult)) {
                result = true;
            }
        } catch (Throwable e) {
            logger.error("logger command update log4j level error", e);
        }

        try {
            //更新logback日志级别
            Boolean updateResult = this.updateLevel(inst, LogbackHelper.class);
            if (Boolean.TRUE.equals(updateResult)) {
                result = true;
            }
        } catch (Throwable e) {
            logger.error("logger command update logback level error", e);
        }

        try {
          	//更新log4j2日志级别
            Boolean updateResult = this.updateLevel(inst, Log4j2Helper.class);
            if (Boolean.TRUE.equals(updateResult)) {
                result = true;
            }
        } catch (Throwable e) {
            logger.error("logger command update log4j2 level error", e);
        }

        if (result) {
            process.write("Update logger level success.\n");
        } else {
            process.write("Update logger level fail. Try to specify the classloader with the -c option. Use `sc -d CLASSNAME` to find out the classloader hashcode.\n");
        }
    }
```

更新日志级别的方法：

```java
//存在指定classload，修改日志级别的使用场景。
private Boolean updateLevel(Instrumentation inst, Class<?> helperClass) throws Exception {
        ClassLoader classLoader = null;
        if (hashCode == null) {
            classLoader = ClassLoader.getSystemClassLoader();
        } else {
            classLoader = ClassLoaderUtils.getClassLoader(inst, hashCode);
        }
				//classload会加载对应的loghelp类。
  			//待确认其中原因
        Class<?> clazz = classLoader.loadClass(helperClassNameWithClassLoader(classLoader, helperClass));
        Method updateLevelMethod = clazz.getMethod("updateLevel", new Class<?>[] { String.class, String.class });
        return (Boolean) updateLevelMethod.invoke(null, new Object[] { this.name, this.level });

    }
```

