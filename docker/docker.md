# Docker

## 基本概念

### Namespace



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

