# Docker

## 基本概念

### Namespace

```bash
man namespaces
```

隔离资源

> - IPC：用于隔离进程间通讯所需的资源（ System V IPC, POSIX message queues），PID命名空间和IPC命名空间可以组合起来用，同一个IPC名字空间内的进程可以彼此看见，允许进行交互，不同空间进程无法交互
> - Network：隔离网络资源。Network Namespace为进程提供了一个完全独立的网络协议栈的视图。包括网络设备接口，IPv4和IPv6协议栈，IP路由表，防火墙规则，socket等等。
> - Mount：隔离文件系统挂载点。每个进程都存在于一个mount Namespace里面，mount Namespace为进程提供了一个文件层次视图。 
> - PID：隔离进程的ID。linux通过命名空间管理进程号，同一个进程，在不同的命名空间进程号不同！ ...
> - User：隔离用户和用户组的ID。 用于隔离用户
> - UTS：隔离主机名和域名信息。用于隔离主机名
```bash
# 查看某个pid的ns信息
ubuntu@kubelet:/proc/35678/ns$ sudo ls -al
total 0
dr-x--x--x 2 root root 0 Jun 10 22:36 .
dr-xr-xr-x 9 root root 0 Jun 10 22:36 ..
lrwxrwxrwx 1 root root 0 Jun 10 22:36 cgroup -> 'cgroup:[4026531835]'
lrwxrwxrwx 1 root root 0 Jun 10 22:36 ipc -> 'ipc:[4026531839]'
lrwxrwxrwx 1 root root 0 Jun 10 22:36 mnt -> 'mnt:[4026531840]'
lrwxrwxrwx 1 root root 0 Jun 10 22:36 net -> 'net:[4026531992]'
lrwxrwxrwx 1 root root 0 Jun 10 22:36 pid -> 'pid:[4026531836]'
lrwxrwxrwx 1 root root 0 Jun 10 22:36 pid_for_children -> 'pid:[4026531836]'
lrwxrwxrwx 1 root root 0 Jun 10 22:36 user -> 'user:[4026531837]'
lrwxrwxrwx 1 root root 0 Jun 10 22:36 uts -> 'uts:[4026531838]'

#查看挂载信息
ubuntu@kubelet:/proc/35678$ cat mountinfo 
25 30 0:23 / /sys rw,nosuid,nodev,noexec,relatime shared:7 - sysfs sysfs rw
26 30 0:5 / /proc rw,nosuid,nodev,noexec,relatime shared:14 - proc proc rw
27 30 0:6 / /dev rw,nosuid,noexec,relatime shared:2 - devtmpfs udev rw,size=485116k,nr_inodes=121279,mode=755
28 27 0:24 / /dev/pts rw,nosuid,noexec,relatime shared:3 - devpts devpts rw,gid=5,mode=620,ptmxmode=000
29 30 0:25 / /run rw,nosuid,nodev,noexec,relatime shared:5 - tmpfs tmpfs rw,size=100488k,mode=755
30 1 252:1 / / rw,relatime shared:1 - ext4 /dev/vda1 rw
```

涉及到Namespace的操作接口包括clone()、setns()、unshare()以及还有/proc下的部分文件。为了使用特定的Namespace，在使用这些接口的时候需要指定以下一个或多个参数：

CLONE_NEWNS: 用于指定Mount Namespace
CLONE_NEWUTS: 用于指定UTS Namespace
CLONE_NEWIPC: 用于指定IPC Namespace
CLONE_NEWPID: 用于指定PID Namespace
CLONE_NEWNET: 用于指定Network Namespace
CLONE_NEWUSER: 用于指定User Namespace
下面简单概述一下这几个接口的用法。


clone() 函数
系统调用来创建一个独立Namespace的进程
int clone(int (*child_func)(void *), void *child_stack, int flags, void *arg);
它通过flags参数来控制创建进程时的特性，比如新创建的进程是否与父进程共享虚拟内存等。比如可以传入CLONE_NEWNS标志使得新创建的进程拥有独立的Mount Namespace，也可以传入多个flags使得新创建的进程拥有多种特性，比如：
flags = CLONE_NEWNS | CLONE_NEWUTS | CLONE_NEWIPC;
传入这个flags那么新创建的进程将同时拥有独立的Mount Namespace、UTS Namespace和IPC Namespace。

setns() 函数
通过 setns() 函数可以将当前进程加入到已有的 namespace 中。setns() 在 C 语言库中的声明如下： 
```
#define _GNU_SOURCE
#include <sched.h>
int setns(int fd, int nstype);
```
和 clone() 函数一样，C 语言库中的 setns() 函数也是对 setns() 系统调用的封装：

fd：表示要加入 namespace 的文件描述符。它是一个指向 /proc/[pid]/ns 目录中文件的文件描述符，可以通过直接打开该目录下的链接文件或者打开一个挂载了该目录下链接文件的文件得到。
nstype：参数 nstype 让调用者可以检查 fd 指向的 namespace 类型是否符合实际要求。若把该参数设置为 0 表示不检查。
前面我们提到：可以通过挂载的方式把 namespace 保留下来。保留 namespace 的目的是为以后把进程加入这个 namespace 做准备。

unshare() 函数 和 unshare 命令
通过 unshare 函数可以在原进程上进行 namespace 隔离。也就是创建并加入新的 namespace 。

unshare()系统调用用于将当前进程和所在的Namespace分离，并加入到一个新的Namespace中，相对于setns()系统调用来说，unshare()不用关联之前存在的Namespace，只需要指定需要分离的Namespace就行，该调用会自动创建一个新的Namespace。

unshare()的函数描述如下：

int unshare(int flags);
其中flags用于指明要分离的资源类别，它支持的flags与clone系统调用支持的flags类似，这里简要的叙述一下几种标志：

CLONE_FILES: 子进程一般会共享父进程的文件描述符，如果子进程不想共享父进程的文件描述符了，可以通过这个flag来取消共享。
CLONE_FS: 使当前进程不再与其他进程共享文件系统信息。
CLONE_SYSVSEM: 取消与其他进程共享SYS V信号量。
CLONE_NEWIPC: 创建新的IPC Namespace，并将该进程加入进来。

Mount Namespace用来隔离文件系统的挂载点，不同Mount Namespace的进程拥有不同的挂载点，同时也拥有了不同的文件系统视图。Mount Namespace是历史上第一个支持的Namespace，它通过CLONE_NEWNS来标识的。

进程在创建Mount Namespace时，会把当前的文件结构复制给新的Namespace，新的Namespace中的所有mount操作仅影响自身的文件系统。但随着引入挂载传播的特性，Mount Namespace变得并不是完全意义上的资源隔离，这种传播特性使得多Mount Namespace之间的挂载事件可以相互影响。

挂载传播定义了挂载对象之间的关系，系统利用这些关系来决定挂载对象中的挂载事件对其他挂载对象的影响。其中挂载对象之间的关系描述如下：

共享关系(MS_SHARED)：一个挂载对象的挂载事件会跨Namespace共享到其他挂载对象。
从属关系(MS_SLAVE): 传播的方向是单向的，即只能从Master传播到Slave方向。
私有关系(MS_PRIVATE): 不同Namespace的挂载事件是互不影响的(默认选项)。
不可绑定关系(MS_UNBINDABLE): 一个不可绑定的私有挂载，与私有挂载类似，但是不能执行挂载操作。

```bash
mount --make-shared /mntS      # 将挂载点设置为共享关系属性
mount --make-private /mntP     # 将挂载点设置为私有关系属性
mount --make-slave /mntY       # 将挂载点设置为从属关系属性
mount --make-unbindable /mntU  # 将挂载点设置为不可绑定属性
```



绑定挂载的引入使得`mount`的其中一个参数不一定要是一个特殊文件，也可以是该文件系统上的一个普通文件目录。Linux中绑定挂载的用法如下

```bash
mount --bind /home/work /home/alpha
mount -o bind /home/work /home/alpha
```







### Cgroup

限制资源使用

- cgroup子系统查看

```bash
jiangwh@ubuntu:~$ lssubsys -a
cpuset
cpu,cpuacct
blkio
memory
devices
freezer
net_cls,net_prio
perf_event
hugetlb
pids
rdma
```

- 各个子系统说明

```
cpu      子系统，主要限制进程的 cpu 使用率。
cpuacct  子系统，可以统计 cgroups 中的进程的 cpu 使用报告。
cpuset   子系统，可以为 cgroups 中的进程分配单独的 cpu 节点或者内存节点。
memory   子系统，可以限制进程的 memory 使用量。
blkio    子系统，可以限制进程的块设备 io。
devices  子系统，可以控制进程能够访问某些设备。
net_cls  子系统，可以标记 cgroups 中进程的网络数据包，然后可以使用 tc 模块（traffic control）对数据包进行控制。
net_prio 子系统,用来设计网络流量的优先级
freezer  子系统，可以挂起或者恢复 cgroups 中的进程。
ns       子系统，可以使不同 cgroups 下面的进程使用不同的 namespace
hugetlb  子系统.主要针对于HugeTLB系统进行限制，这是一个大页文件系统。
```

- 查看cgroup的挂载点

```bash 
jiangwh@ubuntu:/sys/fs/cgroup/cpu/gocker/5b39264034e6$ mount -t cgroup
cgroup on /sys/fs/cgroup/systemd type cgroup (rw,nosuid,nodev,noexec,relatime,xattr,name=systemd)
cgroup on /sys/fs/cgroup/pids type cgroup (rw,nosuid,nodev,noexec,relatime,pids)
cgroup on /sys/fs/cgroup/cpuset type cgroup (rw,nosuid,nodev,noexec,relatime,cpuset)
cgroup on /sys/fs/cgroup/net_cls,net_prio type cgroup (rw,nosuid,nodev,noexec,relatime,net_cls,net_prio)
cgroup on /sys/fs/cgroup/memory type cgroup (rw,nosuid,nodev,noexec,relatime,memory)
cgroup on /sys/fs/cgroup/cpu,cpuacct type cgroup (rw,nosuid,nodev,noexec,relatime,cpu,cpuacct)
cgroup on /sys/fs/cgroup/rdma type cgroup (rw,nosuid,nodev,noexec,relatime,rdma)
cgroup on /sys/fs/cgroup/blkio type cgroup (rw,nosuid,nodev,noexec,relatime,blkio)
cgroup on /sys/fs/cgroup/perf_event type cgroup (rw,nosuid,nodev,noexec,relatime,perf_event)
cgroup on /sys/fs/cgroup/freezer type cgroup (rw,nosuid,nodev,noexec,relatime,freezer)
cgroup on /sys/fs/cgroup/devices type cgroup (rw,nosuid,nodev,noexec,relatime,devices)
cgroup on /sys/fs/cgroup/hugetlb type cgroup (rw,nosuid,nodev,noexec,relatime,hugetlb)
```


- 查看cgroup组,以下展示了test组，所有tasks中pid都收到该组的限制。

```bash
jiangwh@ubuntu:/sys/fs/cgroup/cpu/test$ ls -al
total 0
drwxr-xr-x 3 root root 0 Jun  5 13:18 .
dr-xr-xr-x 6 root root 0 Jun  5 13:17 ..
drwxr-xr-x 2 root root 0 Jun  5 13:26 5b39264034e6
-rw-r--r-- 1 root root 0 Jun  5 13:26 cgroup.clone_children
-rw-r--r-- 1 root root 0 Jun  5 13:26 cgroup.procs
-r--r--r-- 1 root root 0 Jun  5 13:26 cpuacct.stat
-rw-r--r-- 1 root root 0 Jun  5 13:26 cpuacct.usage
-r--r--r-- 1 root root 0 Jun  5 13:26 cpuacct.usage_all
-r--r--r-- 1 root root 0 Jun  5 13:26 cpuacct.usage_percpu
-r--r--r-- 1 root root 0 Jun  5 13:26 cpuacct.usage_percpu_sys
-r--r--r-- 1 root root 0 Jun  5 13:26 cpuacct.usage_percpu_user
-r--r--r-- 1 root root 0 Jun  5 13:26 cpuacct.usage_sys
-r--r--r-- 1 root root 0 Jun  5 13:26 cpuacct.usage_user
-rw-r--r-- 1 root root 0 Jun  5 13:26 cpu.cfs_period_us
-rw-r--r-- 1 root root 0 Jun  5 13:26 cpu.cfs_quota_us
-rw-r--r-- 1 root root 0 Jun  5 13:26 cpu.shares
-r--r--r-- 1 root root 0 Jun  5 13:26 cpu.stat
-rw-r--r-- 1 root root 0 Jun  5 13:26 notify_on_release
-rw-r--r-- 1 root root 0 Jun  5 13:26 tasks
```

- mount 方式处理cgroup

> kernel是通过一个虚拟树状文件系统来配置cgroups的。我们首先需要创建并挂载一个hierarchy(cgroup树)。即先mkdir后mount


```bash
mount -t cgroup -o none,name=cgroup-test cgroup-test cgroup-test/
```
通用的方式
```bash
mount -t cgroup -o subsystems name /cgroup/name
```

cgorup 验证
```bash
# mem验证
cd /sys/fs/cgroup/memory
mkdir mem_test
echo 10M > memory.limit_in_bytes 
# 不使用swap空间
swapoff -a
echo 0 > memory.swappiness
# 将当前shell进程写入任务，该shell启动的程序也收到控制
echo $$ > tasks
# 正常执行
stress --vm 1 --vm-bytes 1M  --timeout 1200s
# 正常执行
stress --vm 1 --vm-bytes 9M  --timeout 1200s 
# 失败
stress --vm 1 --vm-bytes 10M  --timeout 1200s
# 确认失败原因
journalctl -f
```

提示
>stress: info: [69430] dispatching hogs: 0 cpu, 0 io, 1 vm, 0 hdd
>stress: FAIL: [69430] (415) <-- worker 69431 got signal 9
>stress: WARN: [69430] (417) now reaping child worker processes
>stress: FAIL: [69430] (451) failed run completed in 0s

日志
>-- Logs begin at Sun 2021-05-30 12:29:02 CST. --
>Jun 13 14:21:19 kubelet kernel: Memory cgroup stats for /mem_test:
>Jun 13 14:21:19 kubelet kernel: anon 9842688
>                            file 0
>                            kernel_stack 0
>                            slab 409600
>                            sock 0
>                            shmem 0
>                            file_mapped 0
>                            file_dirty 0
>                            file_writeback 0
>                            anon_thp 0
>                            inactive_anon 0
>                            active_anon 9732096
>                            inactive_file 0
>                            active_file 0
>                            unevictable 0
>                            slab_reclaimable 139264
>                            slab_unreclaimable 270336
>                            pgfault 12177
>                            pgmajfault 0
>                            workingset_refault 165
>                            workingset_activate 0
>                            workingset_nodereclaim 0
>                            pgrefill 1454
>                            pgscan 1438
>                            pgsteal 37
>                            pgactivate 1419
>                            pgdeactivate 1454
>                            pglazyfree 0
>                            pglazyfreed 0
>                            thp_fault_alloc 0
>                            thp_collapse_alloc 0
>Jun 13 14:21:19 kubelet kernel: Tasks state (memory values in pages):
>Jun 13 14:21:19 kubelet kernel: [  pid  ]   uid  tgid total_vm      rss pgtables_bytes swapents oom_score_adj name
>Jun 13 14:21:19 kubelet kernel: [  69258]     0 69258     2240      998    57344        0             0 bash
>Jun 13 14:21:19 kubelet kernel: [  69430]     0 69430      964      246    49152        0             0 stress
>Jun 13 14:21:19 kubelet kernel: [  69431]     0 69431     3525     2378    69632        0             0 stress
>Jun 13 14:21:19 kubelet kernel: oom-kill:constraint=CONSTRAINT_MEMCG,nodemask=(null),cpuset=/,mems_allowed=0,oom_memcg=/mem_test,task_memcg=/mem_test,task=stress,pid=69431,uid=0
>Jun 13 14:21:19 kubelet kernel: Memory cgroup out of memory: Killed process 69431 (stress) total-vm:14100kB, anon-rss:9304kB, file-rss:208kB, shmem-rss:0kB, UID:0 pgtables:68kB oom_score_adj:0
>Jun 13 14:21:19 kubelet kernel: oom_reaper: reaped process 69431 (stress), now anon-rss:0kB, file-rss:0kB, shmem-rss:0kB

### UnionFS

​		UnionFS是一种为Linux，FreeBSD，NetBSD操作系统设计的文件系统服务，这个文件系统服务的功能是将其他文件系统联合起来，挂载到同一挂载点。它使用branch把不同文件系统目录和文件进行“透明”覆盖，形成一个单一一致的文件系统。这些branches有两种模式：read-only和read-write，虚拟出来的联合文件系统可以对任何文件进行操作，但是实际上原文件并没有被修改。这里涉及到UnionFS的一个重要的资源管理技术：写时复制（copy on write）。

​		overlay文件系统分为lowerdir、upperdir、merged。workdir（可选）必须和upperdir是mount在同一个文件系统下。 对外统一展示为merged，uperdir和lower的同名文件会被upperdir覆盖。具体层次如下



```bash
#OverlayFS has a workdir option, beside two other directories lowerdir and upperdir, which needs to be an empty directory.Unfortunately the kernel documentation of overlayfs does not talk much about the purpose of this option.

mount -t overlay overlay -o lowerdir=/lower,upperdir=/upper,workdir=/work /merged

#lower dir 可以为多个目录
#lower 可以为只读文件，文件中内容为路径，以:号分割,docker中就是以这种方式指向了例外一个镜像，实现分层镜像。
mount -t overlay overlay -o lowerdir=/lower1:/lower2:/lower3,upperdir=/upper,workdir=/work /merged

#不设定upperdir那么merged目录为只读目录
mount -t overlay overlay -o lowerdir=/lower1:/lower2 /merged
```
查看overlay挂载文件

```bash
jiangwh@ubuntu:~$ mount -t overlay
overlay on /run/k3s/containerd/io.containerd.runtime.v2.task/k8s.io/e8a5ff993357df5c3c995a966d88440745a9c0b79e21f38bdb89b1531fb13a1c/rootfs type overlay (rw,relatime,lowerdir=/var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/2/fs,upperdir=/var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/1937/fs,workdir=/var/lib/rancher/k3s/agent/containerd/io.containerd.snapshotter.v1.overlayfs/snapshots/1937/work)
```



### images

​		镜像文件：一个分层压缩文件。对外形式一般为tar包。

```bash
# rootfs 中展示各层的sha值
docker image inspect imagesId
```

​		每个镜像都存在一个link，用于实现分层。

```bash
# 查看镜像
# docker 中镜像的描述信息在 
# /var/lib/docker/image/overlay2/imagedb/metadata --> update信息、parent
# /var/lib/docker/image/overlay2/imagedb/content --> tag(inspect的相关信息)
docker images
```



## 脚本方式

```bash
#创建目录
mkdir myroot
cd myroot
#创建oldroot以便迁移root用
mkdir oldroot
#获取rootfs
sudo docker pull alpine
sudo docker export `sudo docker run -d alpine ` | tar  -xf-
#屏蔽挂载事件
mount --make-rprivate /
#隔离挂载、用户、通信、pid、网络
unshare --mount --uts --ipc --net --pid --fork /bin/bash
#设置隔离系统的hostname
hostname myns
#重新bind以便切换root
# bind 命令 --bind opr target，会展示使用opr目录，target原有内容不会改变，处理完成后umount
mount --bind `pwd`/myroot `pwd`/myroot
#重新进入隔离目录
cd `pwd`/myroot
#改变root路径
pivot_root . oldroot
#设置当前系统的环境
PATH=$PATH:/bin:/sbin
#挂载当前空间的process
mount -t proc none /proc
#卸载非正在使用挂载点
umount -a
#验证逻辑

```



## 动手造docker

### 设置网桥
net bridge

``` go
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
