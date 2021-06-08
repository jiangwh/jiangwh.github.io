# Docker

## 基本概念

### Namespace

```
setns() 函数
通过 setns() 函数可以将当前进程加入到已有的 namespace 中。setns() 在 C 语言库中的声明如下： 
#define _GNU_SOURCE
#include <sched.h>
int setns(int fd, int nstype);
和 clone() 函数一样，C 语言库中的 setns() 函数也是对 setns() 系统调用的封装：

fd：表示要加入 namespace 的文件描述符。它是一个指向 /proc/[pid]/ns 目录中文件的文件描述符，可以通过直接打开该目录下的链接文件或者打开一个挂载了该目录下链接文件的文件得到。
nstype：参数 nstype 让调用者可以检查 fd 指向的 namespace 类型是否符合实际要求。若把该参数设置为 0 表示不检查。
前面我们提到：可以通过挂载的方式把 namespace 保留下来。保留 namespace 的目的是为以后把进程加入这个 namespace 做准备。在 docker 中，使用 docker exec 命令在已经运行着的容器中执行新的命令就需要用到 setns() 函数。为了把新加入的 namespace 利用起来，还需要引入 execve() 系列的函数(笔者在 《Linux 创建子进程执行任务》一文中介绍过 execve() 系列的函数，有兴趣的同学可以前往了解)，该函数可以执行用户的命令，比较常见的用法是调用 /bin/bash 并接受参数运行起一个 shell。

unshare() 函数 和 unshare 命令
通过 unshare 函数可以在原进程上进行 namespace 隔离。也就是创建并加入新的 namespace 。unshare() 在 C 语言库中的声明如下：

#define _GNU_SOURCE
#include <sched.h>


```

### Cgroup





### UnionFS



## 动手造docker

### 设置网桥
net bridge

```go
	//利用go创建一个网桥
	linkAttrs := netlink.NewLinkAttrs()
	linkAttrs.Name = "bridge0"
	gBridge := &netlink.Bridge{LinkAttrs: linkAttrs}
	if err := netlink.LinkAdd(gBridge); err != nil {
		return err
	}
	//设置子网掩码
	addr, _ := netlink.ParseAddr("172.29.0.1/24") 
	netlink.AddrAdd(gBridge, addr)
	netlink.LinkSetUp(gBridge)
```

### 镜像下载
此处忽略

### 镜像运行文件准备
 挂载文件
```go
//overlay方式 挂载文件 
//func Mount(source string, target string, fstype string, flags uintptr, data string) (err error)
unix.Mount("none", "/var/run/gocker/containers/containerid/fs/mnt", "overlay", 0, "lowerdir=/var/lib/gocker/images,upperdir=,workdir=")

```

### 增加虚拟网卡

veth0为宿主机网卡
veth1为容器中网卡

```go
veth0 := "veth0_" + containerID[:6]
veth1 := "veth1_" + containerID[:6]
linkAttrs := netlink.NewLinkAttrs()
linkAttrs.Name = veth0
//veth0的对端为veth1
veth0Struct := &netlink.Veth{
		LinkAttrs:        linkAttrs,
		PeerName:         veth1,
		PeerHardwareAddr: createMACAddress(),
}
if err := netlink.LinkAdd(veth0Struct); err != nil {
	return err
}
netlink.LinkSetUp(veth0Struct)
gockerBridge, _ := netlink.LinkByName("gocker0")
netlink.LinkSetMaster(veth0Struct, gockerBridge)
```



### 设置网络namespace

```go
//tag目录,保证容器目录的存在
unix.Open("ns target dir", unix.O_RDONLY|unix.O_CREAT|unix.O_EXCL, 0644)
//打开net文件
fd,_ := unix.Open("/proc/self/ns/net", unix.O_RDONLY, 0)
//创建mount namespace
unix.Unshare(unix.CLONE_NEWNET)
//挂载
unix.Mount("/proc/self/ns/net", "target dir", "bind", unix.MS_BIND, "")
//设置net的namespace
unix.Setns(fd, unix.CLONE_NEWNET)
```

### 容器内部网络
设置网络Veth1
```go
fd, err = unix.Open("挂载net目录", unix.O_RDONLY, 0)
//设置网卡名称
veth1 := "veth1_" + containerID[:6]
veth1Link, err := netlink.LinkByName(veth1)

//veth1设置在的namespace，也就是在容器中
netlink.LinkSetNsFd(veth1Link, fd);

//为veth1设置网络IP地址
addr, _ := netlink.ParseAddr(createIPAddress() + "/16")
netlink.AddrAdd(veth1Link, addr)
//启动网络veth1
netlink.LinkSetUp(veth1Link)
//定义路由信息	
route := netlink.Route{
		Scope:     netlink.SCOPE_UNIVERSE,
		LinkIndex: veth1Link.Attrs().Index,
		Gw:        net.ParseIP("172.29.0.1"),
		Dst:       nil,
	}
//增加路由信息
netlink.RouteAdd(&route)
```

### 设置Hostname

```go
unix.Sethostname([]byte(containerID))
```

### 加入到网络Namespace

```go
fd, err := unix.Open("ns target dir", unix.O_RDONLY, 0)
unix.Setns(fd, unix.CLONE_NEWNET)
```

### 设置cgroup

```go
// 创建cgroupfile
/sys/fs/cgroup/memory/gocker/containerId
/sys/fs/cgroup/pids/gocker/containerId
/sys/fs/cgroup/cpu/gocker/containerId
//内存限制
echo mem > /sys/fs/cgroup/memory/gocker/containerId/memory.limit_in_bytes
//number max process
echo pids > /sys/fs/cgroup/pids/gocker/containerId/pids.max
//number max of cpu

echo cpus_quota >/sys/fs/cgroup/cpu/gocker/containerId/cpu.cfs_quota_us
echo cpus_period /sys/fs/cgroup/cpu/gocker/containerId/cpu.cfs_period_us
```

### 设置容器根目录

```go
unix.Chroot("mount target dir")
os.Chdir("/")
```

### mount

```go
unix.Mount("proc", "/proc", "proc", 0, "")
unix.Mount("tmpfs", "/tmp", "tmpfs", 0, "")
unix.Mount("tmpfs", "/dev", "tmpfs", 0, "")
unix.Mount("devpts", "/dev/pts", "devpts", 0, "")
unix.Mount("sysfs", "/sys", "sysfs", 0, "")
```

### 增加本地lo

```go
links, _ := netlink.LinkList()
	for _, link := range links {
		if link.Attrs().Name == "lo" {
			loAddr, _ := netlink.ParseAddr("127.0.0.1/32")
			if err := netlink.AddrAdd(link, loAddr); err != nil {
				log.Println("Unable to configure local interface!")
			}
			netlink.LinkSetUp(link)
		}
	}
```

### 执行传入命令

