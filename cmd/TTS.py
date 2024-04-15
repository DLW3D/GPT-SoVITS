import sys, os
import time
import yaml
import threading
import pyaudio
import wave
import tkinter as tk
from tkinter import filedialog
from inference_cmd import get_tts_wav, change_sovits_weights, change_gpt_weights


def block_print():
    sys.stdout = open(os.devnull, 'w')


def enable_print():
    sys.stdout = sys.__stdout__


# 使用iprint使交互界面不被其他信息干扰
def iprint(*args, **kwargs):
    enable_print()
    print(*args, **kwargs)
    block_print()


class Text2play:
    def __init__(self):
        self.pyAudio = pyaudio.PyAudio()
        self.channels = 1  # 声道数，1或2
        self.async_players = []
        self.async_players_idx = 0
        self.target_device_index = None

        # 模型
        self.id = 0
        self.name = ''
        self.model_dict_path = './cmd/model.yaml'

    @property
    def model_dict(self):
        with open(self.model_dict_path, 'r', encoding='utf-8') as f:
            model_dict = yaml.load(f, Loader=yaml.FullLoader)
        return model_dict

    def get_wav_by_id(self, text, id=None):
        if id is not None:
            self.set_config_by_id(id)
        return self.get_wav(text)

    def set_config_by_id(self, id):
        self.set_device(self.model_dict[id]['device'])
        self.set_model(**self.model_dict[id])
        self.id = id
        self.name = self.model_dict[id]['name']

    def set_model(self, sovits_path, gpt_path, **kwargs):
        change_sovits_weights(sovits_path)
        change_gpt_weights(gpt_path)

    def set_device(self, device_name):
        if not device_name:
            self.target_device_index = None
            return
        # 选择音频输出设备
        all_device = [self.pyAudio.get_device_info_by_index(i) for i in range(self.pyAudio.get_device_count())]
        target_device_name = device_name
        for device in all_device:
            if target_device_name in device['name']:
                self.target_device_index = device['index']
                return
        raise ValueError(f"Can not find device named [{device_name}] in your device list:\n{[i['name'] for i in all_device]}")

    def get_wav(self, text):
        sampling_rate, audio = next(get_tts_wav(
            self.model_dict[self.id]['ref_wav_path'],
            self.model_dict[self.id]['prompt_text'],
            self.model_dict[self.id]['prompt_language'],
            text,
            self.model_dict[self.id]['text_language'],
            how_to_cut=None,
            top_k=5,
            top_p=1,
            temperature=1,
        ))
        return audio, sampling_rate

    # 阻塞式播放（弃用）
    def play(self, audio, rate=32000):
        # 打开声音输出流
        stream = self.pyAudio.open(
            format=self.pyAudio.get_format_from_width(audio.dtype.itemsize),
            channels=self.channels,
            rate=rate,
            output=True,
            output_device_index=self.target_device_index,
        )
        stream.write(audio.tobytes())  # 播放
        time.sleep(stream.get_output_latency())  # 防止音频由于设备延迟还没播完就被关闭了
        stream.stop_stream()
        stream.close()

    def play_async(self, audio, rate, text, auto_start):
        self.async_players.append(
            AsyncPlayer(self.pyAudio, self.target_device_index, audio, rate, self.channels,
                        text=text, auto_start=auto_start)
        )

    def tts(self, text, id, auto_start):
        audio, sampling_rate = self.get_wav_by_id(text, id)
        self.play_async(audio, sampling_rate, f"{self.name}：{text}", auto_start)
        self.async_players_idx = -1

    def interact(self, name_id=0):
        while True:
            iprint('输入：', end='', flush=True)   # 必须指定立即刷新，否则windows shell下不会刷新
            msg = input()
            # 判断特殊命令
            # 帮助
            if msg in ['？', '?', 'help']:
                iprint('当前: {}'.format(name_id))
                iprint('配置列表：')
                s = ''
                for k, v in self.model_dict.items():
                    s += '{}:{} '.format(k, v['name'])
                s += '\n单字命令： q:前 w:复 e:后  s:停 r:播 d:重 c:关'
                iprint(s)
                continue
            # 退出
            if msg in ['quit', 'exit', 'stop']:
                break
            # 单字命令
            if len(msg.lower()) == 1:
                cmd = msg.lower()
                try:
                    if cmd == 'q':  # 选择前一句
                        if self.async_players_idx > -len(self.async_players):
                            self.async_players_idx -= 1
                        iprint('选择：' + self.async_players[self.async_players_idx].text)
                    elif cmd == 'e':  # 选择后一句
                        if self.async_players_idx < -1:
                            self.async_players_idx += 1
                        iprint('选择：' + self.async_players[self.async_players_idx].text)
                    elif cmd == 'w':  # 选择最后一句（复位）
                        self.async_players_idx = -1
                        iprint('选择：' + self.async_players[self.async_players_idx].text)
                    elif cmd == 's':   # stop
                        self.async_players[self.async_players_idx].stop()
                    elif cmd == 'r':   # resume
                        self.async_players[self.async_players_idx].start()
                    elif cmd == 'd':   # duplicate
                        self.async_players[self.async_players_idx].restart()
                    elif cmd == 'c':    # close
                        self.async_players.pop(self.async_players_idx).close()
                        if self.async_players_idx < -1:
                            self.async_players_idx += 1
                    else:   # 无匹配
                        cmd = None
                except IndexError as e:
                    iprint(e)
                if cmd is not None:
                    continue
            # 切换配置
            msg = msg.replace('：', ':')
            if ':' in msg:
                name_id_, msg_ = msg.split(':')
                if name_id_ == 's':  # 保存音频文件
                    self.async_players.pop(self.async_players_idx).save()
                    continue
                try:
                    name_id = int(name_id_)
                    msg = msg_
                except ValueError as e:
                    pass
            if msg == '':
                continue
            # 替换掉特殊字符
            msg = msg.replace('+', '加').replace('-', '减').replace('*', '乘').replace('/', '除')
            msg = msg.replace('=', '等于').replace('>', '大于').replace('<', '小于')
            # 自动播放
            auto_start = True
            if msg[0] == ' ':
                auto_start = False
            # 播放
            try:
                threading.Thread(target=self.tts, args=(msg, name_id, auto_start)).start()
            except Exception as e:
                iprint(e)

    def close(self):
        self.pyAudio.terminate()

    @staticmethod
    def num2char(msg):
        msg = msg.replace('0', '零').replace('1', '一').replace('2', '二').replace('3', '三').replace('4', '四')
        msg = msg.replace('5', '五').replace('6', '六').replace('7', '七').replace('8', '八').replace('9', '九')
        return msg


class AsyncPlayer:
    def __init__(self, pyAudio, target_device_index, audio, rate, channels=1, text=None, auto_start=True):
        self.pyAudio = pyAudio
        self.target_device_index = target_device_index
        self.audio = audio
        self.rate = rate
        self.channels = channels
        self.text = text
        self.seek = 0
        self.stream = None
        self.silent_save = True  # 保存wav文件路径为？当前目录下save文件夹：弹窗指定路径
        if auto_start:
            self.restart()
        else:
            iprint('Ready:' + text, end="\r\n")

    # 重播
    def restart(self):
        self.close()
        self.seek = 0
        self.stream = self.pyAudio.open(
            format=self.pyAudio.get_format_from_width(self.audio.dtype.itemsize),
            channels=self.channels,
            rate=self.rate,
            output=True,
            stream_callback=self.callback,
            output_device_index=self.target_device_index,
        )

    def callback(self, in_data, frame_count, time_info, status):
        start = self.seek
        self.seek += frame_count
        data = self.audio[start: self.seek]
        return data, pyaudio.paContinue

    # 继续
    def start(self):
        if self.stream:
            self.stream.start_stream()

    # 暂停
    def stop(self):
        if self.stream:
            self.stream.stop_stream()

    # 停止
    def close(self):
        self.stop()
        if self.stream:
            self.stream.close()

    # 保存
    def save(self, file_name=None):
        file_name = file_name or self.text[:20]

        if self.silent_save:
            # 默认保存位置
            save_path = './save/'
            os.makedirs(save_path, exist_ok=True)
            file_path = os.path.join(save_path, file_name) + '.wav'
        else:
            # 弹窗选择保存位置
            root = tk.Tk()
            root.withdraw()
            file_path = filedialog.asksaveasfilename(initialfile=file_name, defaultextension=".wav",
                                                     filetypes=[("WAV files", "*.wav")])
            if not file_path:
                return  # User canceled

        wf = wave.open(file_path, 'wb')
        wf.setnchannels(self.channels)
        wf.setsampwidth(self.pyAudio.get_sample_size(self.pyAudio.get_format_from_width(self.audio.dtype.itemsize)))
        wf.setframerate(self.rate)
        wf.writeframes(b''.join(self.audio))
        wf.close()

    def __del__(self):
        self.close()


if __name__ == '__main__':
    tts = Text2play()
    tts.interact()
