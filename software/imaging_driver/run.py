import argparse
import io
import logging
from threading import Condition

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder as MJPEGEncoder
from picamera2.outputs import FileOutput

from flask import Response
from flask import Flask
from flask import render_template
from flask import request
from flask.json import jsonify
import time
import sys

class StreamingOutput(io.BufferedIOBase):
    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf):
        with self.condition:
            self.frame = buf
            self.condition.notify_all()

# initialize a flask object
app = Flask(__name__)

# initialize a default setting
default_settings = {}

# detect the number and model of camera(s) attached
camera_info = Picamera2.global_camera_info()
for cam in camera_info:
    if cam["Model"] == "imx708":
        if "Num" in cam:
            cam_id = cam["Num"]
        else:
            cam_id = 0
        default_settings["cam{}".format(cam_id)] = {
            "enable": True,
            "resolution": (2304, 1296),
            "controls": {
                "AeEnable": False,
                "AnalogueGain": 4,
                "ExposureTime": 30000,
                "AwbEnable": False,
                "ColourGains": (1.6, 2.0),
            },
            "focusControls": {
                "AfMode": 0, # AfModeManual = 0, AfModeAuto = 1, AfModeContinuous = 2
                "LensPosition": 10.0,
            }
        }
    else:
        if "Num" in cam:
            cam_id = cam["Num"]
        else:
            cam_id = 0
        default_settings["cam{}".format(cam_id)] = {
            "enable": True,
            "resolution": (1024, 720),
            "controls": {
                "AeEnable": False,
                "AnalogueGain": 5.5,
                "ExposureTime": 25000,
                "AwbEnable": False,
                "ColourGains": (1.2, 1.5),
            },
        }
N_cameras = len(camera_info)

default_settings["mic"] = {
    "enable": False,
    "sampleRate": 48000,
    "bitsPerSample": 16,
    "channels": 2,
    "chunk": 1024
}

def deepcopy(d):
    if isinstance(d, dict):
        return {k: deepcopy(v) for k, v in d.items()}
    elif isinstance(d, list):
        return [deepcopy(v) for v in d]
    return d
settings = deepcopy(default_settings)

# initialize camera related variables
cameras = [None for _ in range(N_cameras)]
camera_outputs = [StreamingOutput() for _ in range(N_cameras)]

def setup_camera():
    global cameras, camera_outputs, settings
    try:
        for id in range(2):
            cam_key = "cam{}".format(id)
            if cam_key not in settings:
                continue
            if settings["cam{}".format(id)]["enable"]:
                print("... setting up camera {}".format(id))
                if cameras[id] is not None:
                    cameras[id].stop_recording()
                    cameras[id].close()
                    cameras[id] = None
                cameras[id] = Picamera2(id)
                cameras[id].configure(cameras[id].create_video_configuration(main={"size": settings["cam{}".format(id)]["resolution"]}))
                cameras[id].set_controls(settings["cam{}".format(id)]["controls"])
                cameras[id].start_recording(MJPEGEncoder(), FileOutput(camera_outputs[id]))
                if "focusControls" in settings["cam{}".format(id)]: # only set focus controls if they are present
                    cameras[id].set_controls(settings["cam{}".format(id)]["focusControls"])
                print("... camera {} setup complete".format(id))
            else:
                if cameras[id] is not None:
                    cameras[id].stop_recording()
                    cameras[id].close()
                    cameras[id] = None
    except Exception as e:
        return "Failed to setup camera: {}".format(e)
    return "success"

# initialize microhpone related variables
audio_device = None
audio_stream = None
audio_setup_condition = Condition()
wav_header = None

def gen_audio_header(sampleRate, bitsPerSample, channels):
    datasize = 2000*10**6
    o = bytes("RIFF",'ascii')                                               # (4byte) Marks file as RIFF
    o += (datasize + 36).to_bytes(4,'little')                               # (4byte) File size in bytes excluding this and RIFF marker
    o += bytes("WAVE",'ascii')                                              # (4byte) File type
    o += bytes("fmt ",'ascii')                                              # (4byte) Format Chunk Marker
    o += (16).to_bytes(4,'little')                                          # (4byte) Length of above format data
    o += (1).to_bytes(2,'little')                                           # (2byte) Format type (1 - PCM)
    o += (channels).to_bytes(2,'little')                                    # (2byte)
    o += (sampleRate).to_bytes(4,'little')                                  # (4byte)
    o += (sampleRate * channels * bitsPerSample // 8).to_bytes(4,'little')  # (4byte)
    o += (channels * bitsPerSample // 8).to_bytes(2,'little')               # (2byte)
    o += (bitsPerSample).to_bytes(2,'little')                               # (2byte)
    o += bytes("data",'ascii')                                              # (4byte) Data Chunk Marker
    o += (datasize).to_bytes(4,'little')                                    # (4byte) Data size in bytes
    return o


def setup_microphone():
    global settings, audio_device, audio_stream, audio_setup_condition, wav_header
    wav_header = gen_audio_header(settings["mic"]["sampleRate"], settings["mic"]["bitsPerSample"], settings["mic"]["channels"])

    with audio_setup_condition:
        msg = "success"
        if settings["mic"]["enable"]:
            # make sure to only import once
            if "pyaudio" not in sys.modules:
                try:
                    import pyaudio
                except ImportError:
                    return "pyaudio is not installed"
            if settings["mic"]["bitsPerSample"] == 16:
                audio_format = pyaudio.paInt16
            else: 
                raise NotImplementedError("Only 16-bit audio is supported")
            if audio_stream is not None:
                audio_stream.close()
                audio_stream = None
            audio_device = pyaudio.PyAudio()
            # find the audio device
            audio_device_id = -1
            for i in range(audio_device.get_device_count()):
                dev = audio_device.get_device_info_by_index(i)
                if 'USB' in dev['name']:
                    audio_device_id = i
            if audio_device_id == -1:
                msg = 'USB Mic not found'
            else:
                audio_stream = audio_device.open(
                    format=audio_format, channels=settings["mic"]["channels"],
                    rate=settings["mic"]["sampleRate"], input=True, input_device_index=audio_device_id,
                )
        else:
            if audio_stream is not None:
                audio_stream.close()
                audio_stream = None
        audio_setup_condition.notify_all()
    return msg

@app.route('/audio')
def audio():
    def sound():
        print("recording...")
        # TODO: wav_header will not be updated if the settings are changed
        first_run = True
        while True:
            with audio_setup_condition:
                audio_setup_condition.wait()
                if audio_stream is not None:
                    audio_frame = audio_stream.read(settings["mic"]["chunk"], exception_on_overflow=False)
                    if first_run:
                        data = wav_header + audio_frame
                        first_run = False
                    else:
                        data = audio_frame
                    yield(data)
                else:
                    # yield a blank frame
                    yield(b'\x00'*settings["mic"]["chunk"])

    return Response(sound(), mimetype="audio/x-wav")

@app.route("/")
@app.route("/index.html")
def index():
    # return the rendered template
    return render_template("index.html")


# def parse_key_and_update_settings(key, value, subsettings):
#     if "-" in key:
#         first_dash = key.index("-")
#         key_parts = [key[:first_dash], key[first_dash+1:]]
#         if key_parts[0] in subsettings:
#             return parse_key_and_update_settings(key_parts[1], value, subsettings[key_parts[0]])
#         else:
#             return "Unknown key: {}".format(key)
#     else:
#         if key in subsettings:
#             subsettings[key] = value
#             return "success"
#         else:
#             return "Unknown key: {}".format(key)

# def parse_setting_value(value):
#     if "True" in value or "true" in value:
#         return True
#     elif "False" in value or "false" in value:
#         return False
#     elif '(' in value and ')' in value:
#         dtype = float if '.' in value else int
#         return tuple(map(dtype, value[value.index("(")+1:value.index(")")].split(',')))
#     else:
#         try:
#             if '.' in value:
#                 return float(value)
#             else:
#                 return int(value)
#         except ValueError:
#             return value


def update_settings(response, new_settings):
    # parse arguments and update the settings
    global settings
    settings_old = deepcopy(settings)

    def overwrite_setting_with_request(sub_settings, req):
        for key in req:
            print(key, key in sub_settings)
            if key in sub_settings:
                if isinstance(req[key], dict):
                    msg = overwrite_setting_with_request(sub_settings[key], req[key])
                    if msg != "success":
                        return msg
                else:
                    sub_settings[key] = req[key]
            else:
                return "Unknown key: {}".format(key)
        return "success"
    print(new_settings)
    status = overwrite_setting_with_request(settings, new_settings)
    print(settings)
    if status != "success":
        settings = settings_old
        response["status"] = "error"
        response["message"] += status
        print(response)
        return response
    # for key in request.args:
    #     status = parse_key_and_update_settings(key, parse_setting_value(request.args[key]), settings)
    #     if status != "success":
    #         settings = settings_old
    #         response["status"] = "error"
    #         response["message"] += status
    #         return jsonify(response)

    # setup the camera based on the new settings
    status = setup_camera()
    if status != "success":
        response["status"] = "error"
        response["message"] += "; " + status
    
    # setup the microphone based on the new settings
    status = setup_microphone()
    if status != "success":
        response["status"] = "error"
        response["message"] += "; " + status
    response["settings"] = settings
    return response

@app.route("/reset-settings")
def reset_setting():
    global default_settings
    print("resetting settings")
    response = {"status": "success", "message": ""}
    response = update_settings(response, deepcopy(default_settings))
    return jsonify(response)

@app.route("/settings", methods=['GET', 'POST'])
def setting():
    global settings
    response = {"status": "success", "message": ""}

    if request.method == 'GET':
        return jsonify(settings)
    elif request.method == 'POST':
        response = update_settings(response, request.json)
        return jsonify(response)
    else:
        response["status"] = "error"
        response["message"] = "Invalid request method"
    return jsonify(response)


@app.route("/cam_feed/<id>")
def video_feed(id=0):
    if "cam{}".format(id) not in settings:
        return Response("Invalid camera id", status=400)
    def generate_frame(cam_id):
        while True:
            # wait until the lock is acquired
            with camera_outputs[cam_id].condition:
                camera_outputs[cam_id].condition.wait()
                frame = camera_outputs[cam_id].frame
            # yield the output frame in the byte format
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + bytearray(frame) + b"\r\n"
            )
    return Response(generate_frame(cam_id=int(id)), mimetype="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    # ap.add_argument(
    #     "-i", "--ip", type=str, required=True, help="ip address of the device"
    # )
    ap.add_argument(
        "-o",
        "--port",
        type=int,
        default=8000,
        help="ephemeral port number of the server (1024 to 65535)",
    )
    args = vars(ap.parse_args())

    # initial setup w/ default params
    # cam_status = setup_camera()
    # print("Inittialize camera: ", cam_status)
    # mic_status = setup_microphone()
    # print("Inittialize microphone: ", mic_status)

    # start the flask app
    app.run(
        host="0.0.0.0",
        port=args["port"],
        debug=False,
        threaded=True,
        use_reloader=False,
    )
