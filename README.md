<div align="center">
<h1>GPT-SoVITS-WebUI</h1>
强大的少样本语音转换与语音合成
<h2>命令行实时交互TTS</h2>

基于 [RVC-Boss/GPT-SoVITS-WebUI](https://github.com/RVC-Boss/GPT-SoVITS)
</div>

## 添加了以下功能：
- 简易命令行终端交互，输入文本实时播放语音。
- 一键切换模型
- 多线程推断和播放
- 播放控制：暂停，继续，重播等

## 项目配置
- 该项目基于官方文档在win10上测试通过
1. 按照[GPT-SoVITS-WebUI官方文档](docs/cn/README.md)进行配置，确保通过官方测试用例。


2. 在你使用的python环境中安装 pyaudio 库 `pip install pyaudio`


3. 编辑模型配置文件`cmd/model.yaml`，指定使用中可切换的模型、参考音频以及声音输出设备。

    按照模板的yaml格式添加所需的配置信息即可。

    其中`device`留空为使用系统默认播放设备。若需指定输出设备，则执行下述python代码检查系统中的音频输出设备，并选择其一填入。

    ```python
    import pyaudio
   
    pyAudio = pyaudio.PyAudio()
    all_device = [pyAudio.get_device_info_by_index(i) for i in range(pyAudio.get_device_count())]
    output_device_name_1 = [i['name'] for i in all_device if i['maxOutputChannels']>0 and i['hostApi']==0]
    print('----------------------------')
    print('\n'.join(output_device_name_1))
    print('----------------------------')
    output_device_name_2 = [i['name'] for i in all_device if i['maxOutputChannels']>0 and i['hostApi']>0]
    print('\n'.join(output_device_name_2))
    print('----------------------------')
    ```
4. 如需将音频输出转为输入（播放的声音映射到麦克风中），安装虚拟音频设备 [VB-CABLE Virtual Audio Device](https://vb-audio.com/Cable/) 然后配置文件中指定`device: CABLE Input`
    
## 操作说明
启动根目录下的 `tts.bat`。程序初始化完成后，最后一行出现`输入：`后即可输入需要TTS的文本。

输入文本后敲击回车，会开启一个线程在后台将其转换为音频，并立即播放到指定设备。在这过程中用户可以输入下一条文本并提交下一个TTS任务。

输入`？`可查看当前选择的模型、配置可用的模型和用于播放控制的命令。

### 模型选择
在交互界面中，输入`[num]: [text]`，使用第`[num]`个模型将`[text]`转为语音并立即播放。例如：
```
输入：1: 测试测试，一二三四
```
也可输入`[num]:`切换模型，再直接输入`[text]`进行TTS：
```
输入：1: 测试一 (使用模型1播放：测试一)
输入：2:
输入：测试二 (使用模型2播放：测试二)
输入：测试三 (使用模型2播放：测试三)
输入：3:测试四 (使用模型3播放：测试四)
输入：测试五 (使用模型3播放：测试五)
```

### 播放控制
可以使用单字命令进行播放控制，也可选择之前播放的语音进行重播。
- s: 暂停播放
- r: 恢复播放
- d: 重播
- c: 关闭（删除该条语音）
- q: 选择前一句
- w: 选择最后一句
- e: 选择后一句
```
输入：1: 测试一 (模型1播放：测试一)
输入：2: 测试二 (模型2播放：测试二)
输入：测试三 (模型2播放：测试三)
输入：d (模型2播放：测试三)
输入：q
选择：测试二
输入：q
选择：测试一
输入：d (模型1播放：测试一)
输入：e
选择：测试二
输入：d (模型2播放：测试二)
```

### TODO
- [x] 播放控制，如暂停、继续、重播。
- [x] 异步播放，非阻塞播放，允许多个音频同时播放。
- [x] 多线程推断，模型推断时可以进行下一次输入。
- [x] 配置文件热重载。
- [ ] 播放设备独立于模型配置，可实时切换，实现设备A预览后设备B播放。
- [ ] 交互操作：保存当前音频为wav文件。

---

[原始项目README文档](docs/README.md)