import os
import shutil
import glob
from concurrent.futures import ThreadPoolExecutor
from tkinter import filedialog
import PySimpleGUI as sg
from lib.pyrife_ncnn_vulkan_GUI import Pyrife_ncnn_vulkan
from lib.pyffmpeg_GUI import Pyffmpeg
from lib.confighandler import ConfigHandler
from lib.VERSION import Version

class Work:
    def __init__(self, path: str):
        self.__config = ConfigHandler(path)
        self.config_data = self.__config.read_all()
        self.rife = Pyrife_ncnn_vulkan(self.config_data["USER"]["pyrife_ncnn_vulkan_config"])
        self.ffmpeg = Pyffmpeg(self.config_data["USER"]["pyffmpeg_config"])
        self.rife.apply_all_from_config()
        self.ffmpeg.apply_all_from_config()

        self.list_rifever = [os.path.basename(i.rstrip("\\")) for i in glob.glob(f"{os.path.dirname(self.rife.rifeexe)}\\*\\")]


class GUI:
    def __init__(self, list_rifever, rifeconfig, ffmpegconfig):

        self.column_inputfile = sg.Frame("ファイル選択", expand_x=True, layout=[
            [sg.Text("ファイルを指定してください:"), sg.InputText(expand_x=True, key = "-inputfile-", enable_events=True), sg.FileBrowse(button_text="参照", enable_events=True)],
            [sg.Text("選択されたファイル:"), sg.Text("", key="-nowselectfile-", expand_x=True)]])
        
        self.column_ffmpeg_in = sg.Frame("FFmpegによる前処理の設定", expand_x=True, layout=[
            [sg.Text("画像の拡張子:", (18,1)), sg.InputText(ffmpegconfig["image_extension"], (10,1), key="-imageextension-")]
        ])
        
        self.column_rife = sg.Frame("RIFEの設定", expand_x=True, layout=[
            [sg.Text("RIFEのバージョン:", (18,1)), sg.Combo(list_rifever, rifeconfig["rifever"], (9,1), key="-rifever-"), sg.Text("RIFEの並行処理数:", (18,1)), sg.InputText(rifeconfig["rifeusage"], (10,1), key="-rifeusage-")],
            [sg.Text("RIFEの使用GPUNo.:", (18,1)), sg.InputText(rifeconfig["rifegpu"], (10,1), key="-rifegpu-"), sg.Text("補完処理の回数:", (18,1)), sg.InputText(rifeconfig["times"], (10,1), key="-times-")]
        ])

        self.column_ffmpeg_out = sg.Frame("出力の設定", expand_x=True, layout=[
            [sg.Text("ffmpegの動画出力オプション:"), sg.InputText(ffmpegconfig["option"], expand_x=True, key="-option-")],
            [sg.Text("動画の保存先:"), sg.FolderBrowse(button_text="参照", enable_events=True, target="-completefolder-"), sg.InputText(ffmpegconfig["complete_folder"], expand_x=True, key="-completefolder-"),sg.Text("\\"), sg.InputText("(ファイル名)", key="-videoname-", size=(20,1)),sg.Text("."),sg.InputText(ffmpegconfig["video_extension"], (10,1), key="-videoextension-")]
        ])

        self.console = sg.Output(expand_x=True, expand_y=True, )

        self.debugmode = True
        self.debug = sg.Column(layout=[
            [sg.Text("status:", visible=self.debugmode), sg.Input("home", visible=self.debugmode, disabled=True, size=(12,1), key="-debug_status-")]
        ])

        self.column_startstop = sg.Column(justification="RIGHT", layout=[
            [sg.Button("中止", disabled=True, key="-cancel-"), sg.Button("実行", key="-run-")]
        ])
        
        self.layout = [
            [self.column_inputfile],
            [sg.Column([[self.column_ffmpeg_in, self.column_rife]], justification="CENTER")],
            [self.column_ffmpeg_out],
            [self.console],
            [self.debug, self.column_startstop]
            ]
        self.window = sg.Window("RIFE", self.layout, size=(800,600), resizable=True)


class Control:
    def __init__(self):
        self.work = Work(".\\setting\\config.ini")
        self.GUI = GUI(self.work.list_rifever, self.work.rife.config_data["USER"], self.work.ffmpeg.config_data["USER"])
        self.status = "home"

    def update_status(self, code: str):
        self.status = code
        self.GUI.window["-debug_status-"].update(self.status)

    def run(self):
        while True:
            event, values = self.GUI.window.read()

            if event == "-inputfile-":
                self.update_status("inputfile")
                self.GUI.window["-nowselectfile-"].update(values["-inputfile-"])
#                self.__inputfilevalue: str = os.path.basename(values["-inputfile-"])
#                if "." in self.__inputfilevalue:
#                    self.GUI.window["-videoname-"].update(f"\\{self.__inputfilevalue.rsplit('.', 1)[0]}_rife.")
#                else:
#                    self.GUI.window["-videoname-"].update(f"\\{self.__inputfilevalue}_rife.")
                self.update_status("home")

            if event == "-run-":
                self.update_status("run_change_setting")
                self.GUI.window["-run-"].update(disabled=True)
                self.GUI.window["-cancel-"].update(disabled=False)
                self.work.ffmpeg.input_file = values["-inputfile-"]
                self.work.ffmpeg.image_extension = values["-imageextension-"]
                self.work.rife.output_extension = values["-imageextension-"]
                self.work.rife.rifever = values["-rifever-"]
                self.work.rife.rifeusage = values["-rifeusage-"]
                self.work.rife.rifegpu = values["-rifegpu-"]
                self.work.rife.times = values["-times-"]
                self.work.ffmpeg.video_extension = values["-videoextension-"]
                self.work.ffmpeg.option = values["-option-"]
                def run_all():
                    if self.status == "run_change_setting":
                        self.update_status("run_vid2img")
                        self.work.ffmpeg.video_to_image()
                    if self.status == "run_vid2img":
                        self.update_status("run_rife")
                        self.work.rife.run()
                    if self.status == "run_rife":
                        self.update_status("run_img2vid")
                        self.work.ffmpeg.image_to_video(str(int(self.work.ffmpeg.get_framerate())*(2**int(self.work.rife.times))), values["-videoname-"])
                self.GUI.window.start_thread(lambda: run_all(), end_key="-finish-")

            if event == "-finish-":
                self.GUI.window["-run-"].update(disabled=False)
                self.GUI.window["-cancel-"].update(disabled=True)
                self.update_status("home")

            if event == "-cancel-":
                if self.status == "run_vid2img":
                    self.update_status("cancel_vid2img")
                    self.work.ffmpeg.running_vid2img.kill()
                if self.status == "run_rife":
                    self.update_status("cancel_rife")
                    self.work.rife.running_rife.kill()
                if self.status == "run_img2vid":
                    self.update_status("cancel_img2vid")
                    self.work.ffmpeg.running_img2vid.kill()
                print("作業を中断しました")
                self.update_status("home")

                

            if event == sg.WIN_CLOSED:
                break

        self.GUI.window.close()


if __name__ == "__main__":
    os.chdir(os.path.dirname(__file__))
    App = Control()
    App.run()