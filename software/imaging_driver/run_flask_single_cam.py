import argparse
import io
import logging
from threading import Condition

from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from libcamera import controls

from flask import Response
from flask import Flask
from flask import render_template
import time

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

# initialize cameras
cam0 = Picamera2(0)
cam0.configure(cam0.create_video_configuration(main={"size": (1024, 720)}))

cam0.set_controls({"AeEnable": False, "AnalogueGain": 5.5, "ExposureTime": 25000, "AwbEnable": False, "ColourGains": (1.2, 1.5)})

output0 = StreamingOutput()
cam0.start_recording(JpegEncoder(), FileOutput(output0))

def generate_frame(cam_id):
    # grab global references to the output frame and lock variables
    # global output_frame, lock
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with output0.condition:
            output0.condition.wait()
            frame = output0.frame
        # yield the output frame in the byte format
        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + bytearray(frame) + b"\r\n"
        )

@app.route("/")
@app.route("/index.html")
def index():
    # return the rendered template
    print("here")
    return render_template("index_single_cam.html")


@app.route("/cam_feed/<id>")
def video_feed(id=0):
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

    # start the flask app
    app.run(
        host="0.0.0.0",
        port=args["port"],
        debug=False,
        threaded=True,
        use_reloader=False,
    )