# ffmpeg

最简单转码, 以mov转为mp4为例(支持绝大多数编/解码格式):

```
ffmpeg -i in.mov out.mp4
```

仅转码视频, 音频保持不变:

```
ffmpeg -i in.mov -c:a copy out.mp4
```

减小视频分辨率到720p, 码率为2500kbps, fps 30:

```
ffmpeg -i in.mov -vf scale=-2:720 -b:v 2500k -r 30 out.mp4
```

去掉音频:

```
ffmpeg -i in.mov -c:v copy -an out.mov
```

增大12dB音量:

```
ffmpeg -i in.mov -c copy -af volume=12dB out.mov
```

macOS使用显卡加速mpeg4转码(普通macbook应该只能使用这个, 独显可能支持更多驱动):

```
ffmpeg -i in.mov -c:v h264_videotoolbox out.mp4
```

录制在线视频流(示例将MPEG TS流视频不转码保存为ts文件, 源为m3u8列表文件):

```
ffmpeg -i http://xxx.com/yyy/zzz.m3u8 -c copy out.ts
```

录制在线视频流, 保存的同时转码:

```
ffmpeg -i https://xxx.yyy.flv?a=XXX&b=YYY -c:v h264_videotoolbox -vf scale=-2:720 -b:v 2500k out.mp4
```

截取视频中的一部分:

```
ffmpeg -ss 00:xx:yy -i in.mp4 -to 00:mm:nn -c copy -copyts out.mp4
```

-ss后面是起始时间戳, -to后面是结束时间戳, -copyts表示拷贝时间戳, 这会影响到音画同步. 在线视频流也支持从保存某个时间段的视频



```bash
# -aframes number     set the number of audio frames to output
# -aq quality         set audio quality (codec-specific)
# -ar rate            set audio sampling rate (in Hz)
# -ac channels        set number of audio channels
# -an                 disable audio
# -acodec codec       force audio codec ('copy' to copy stream)
# -vol volume         change audio volume (256=normal)
# -af filter_graph    set audio filters
ffmpeg -i out.mp3 -b:a 24K -acodec mp3 -ar 16000 -ac 1 out2Kz.mp3 
# 声道转为1个
ffmpeg -i out.mp3 -b:a 12K -acodec mp3 -ar 8000 -ac 1 out2z.mp3
ffmpeg -i out.mp3 -b:a 24K -acodec wmav2 -ar 8000 -ac 1 out.wma
```

