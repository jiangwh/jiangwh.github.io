# Kube-Porxy

Kube-Proxy实现的两种方式：

1、iptables

2、ipvs

下面分别说明两种方式：

其中iptables每次转发都需要查找对应的规则，如果pod、svc 数量较多，那么查找规则时间会相应增加。

iptables实现也是朴实无华，最终通过os.exec.Command调用iptables。

具体实现

```go

//iptabels.go 保存iptables信息
func (runner *runner) SaveInto(table Table, buffer *bytes.Buffer) error {
	runner.mu.Lock()
	defer runner.mu.Unlock()

	trace := utiltrace.New("iptables save")
	defer trace.LogIfLong(2 * time.Second)

	// run and return
    // savecmd 就是 iptables-save
	iptablesSaveCmd := iptablesSaveCommand(runner.protocol)
	args := []string{"-t", string(table)}
    //args为table中信息
	klog.V(4).Infof("running %s %v", iptablesSaveCmd, args)
	cmd := runner.exec.Command(iptablesSaveCmd, args...)
	cmd.SetStdout(buffer)
	stderrBuffer := bytes.NewBuffer(nil)
	cmd.SetStderr(stderrBuffer)

	err := cmd.Run()
	if err != nil {
		stderrBuffer.WriteTo(buffer) // ignore error, since we need to return the original error
	}
	return err
}

func (executor *executor) Command(cmd string, args ...string) Cmd {
	return (*cmdWrapper)(osexec.Command(cmd, args...))
}
```





ipvs

```go

```

