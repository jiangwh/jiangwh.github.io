import ffmpy3 as ffmpy


def transcode():
    ff = ffmpy.FFmpeg(
        inputs={'input.ts': None},
        outputs={'output.mp4': '-c:a mp2 -c:v mpeg2video'})
    return ff.cmd


def compressVideo():
    ff = ffmpy.FFmpeg(inputs={'/Users/jiangwh/Desktop/1.mp4': None},
                      outputs={'output.mp4': '-r 20'})
    return ff.cmd


def getAudio():
    ff = ffmpy.FFmpeg(
        inputs={"/Users/jiangwh/Desktop/1.mp4": None},
        outputs={'out.mp3': "-f mp3 -ar 16000"}
    )
    return ff


def cutVideo():
    ff = ffmpy.FFmpeg(inputs={"/Users/jiangwh/Desktop/1.mp4": None},
                      outputs={"out.mp4": ['-ss', '00:01:20',
                                           '-t', '02:00:00',
                                           '-vcodec', 'copy',
                                           '-acodec', 'copy']}
                      )
    ff.run()


def ConcatVideo():
    ff = ffmpy.FFmpeg(
        global_options=['-f', 'concat'],
        inputs={[]: None},
        outputs={'output.mp4': ['-c', 'copy']}
    )
    return ff

# Audio options:
# -aframes number     set the number of audio frames to output
# -aq quality         set audio quality (codec-specific)
# -ar rate            set audio sampling rate (in Hz)
# -ac channels        set number of audio channels
# -an                 disable audio
# -acodec codec       force audio codec ('copy' to copy stream)
# -vol volume         change audio volume (256=normal)
# -af filter_graph    set audio filters


def compressAudio():
    ff = ffmpy.FFmpeg(
        inputs={"out.mp3": None},
        outputs={"out2z.mp3": "-b:a 12K -acodec mp3 -ar 8000 -ac 1"}
    )
    return ff
def compressAudio24():
    ff = ffmpy.FFmpeg(
        inputs={"out.mp3": None},
        outputs={"out2Kz.mp3": "-b:a 24K -acodec mp3 -ar 16000 -ac 1"}
    )
    return ff

def tranAudio():
    ff = ffmpy.FFmpeg(
        inputs={"out.mp3": None},
        outputs={"out.wav": "-f wav"}
    )
    return ff

def tranAudioMp32WMA():
    ff = ffmpy.FFmpeg(
        inputs={"out.mp3": None},
        outputs={"out.wma": "-b:a 24K -acodec wmav2 -ar 8000 -ac 1"}
    )
    return ff

if __name__ == '__main__':
    compressAudio24().run()
    # tranAudioMp32WMA().run()
