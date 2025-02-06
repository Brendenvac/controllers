import copy
import time
import threading
import sys
import subprocess
import argparse
import json
from version import __version__
from feagi_connector import retina
from feagi_connector import sensors
from feagi_connector import actuators
from feagi_connector import pns_gateway as pns
from feagi_connector import feagi_interface as FEAGI
import base64
import numpy as np
import cv2

camera_data = {"vision": {'0': []}}
previous_frame_data = dict()
rgb = dict()
rgb['camera'] = dict()
raw_data_msg = {'camera': [], "gyro": []}
FEAGI.validate_requirements('requirements.txt')  # you should get it from the boilerplate generator


def check_the_flag():
    parser = argparse.ArgumentParser(description="Run Gazebo simulation and capture JSON output from a topic.")
    parser.add_argument("--sdf", type=str, default="shapes.sdf", help="Path to the SDF file")

    args, remaining_args = parser.parse_known_args()
    path = args.sdf  # e.g., './humanoid.xml' or 'C:/path/to/humanoid.xml'
    available_list_from_feagi_connector = FEAGI.get_flag_list()
    cleaned_args = []
    skip_next = False
    for i, arg in enumerate(sys.argv[1:]):
        if skip_next:
            skip_next = False
            continue
        if arg in available_list_from_feagi_connector:
            cleaned_args.append(arg)
            if i + 1 < len(sys.argv[1:]) and not sys.argv[1:][i + 1].startswith("-"):
                cleaned_args.append(sys.argv[1:][i + 1])
                skip_next = True
    sys.argv = [sys.argv[0]] + cleaned_args
    return path


def create_entity():
    """
    Function to create a new entity in Gazebo using the gz service command.
    """
    create_command = [
        "gz", "service", "-s", "/world/free_world/create",
        "--reqtype", "gz.msgs.EntityFactory",
        "--reptype", "gz.msgs.Boolean",
        "--timeout", "300",
        "--req",
        "sdf_filename: 'smart_car.sdf' pose: {position: {z: 1}} name: 'new_name' allow_renaming: false"
    ]

    try:
        # Run the command and capture the output
        result = subprocess.run(create_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        print("Entity creation output:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print("Failed to create entity:")
        print(e.stderr)
    except FileNotFoundError:
        print("The 'gz' command was not found. Make sure it is installed and available in your PATH.")


def initalize_gyro():
    topic_command = ["gz", "topic", "-e", "-t", "/imu", "--json-output"]
    topic_process = subprocess.Popen(topic_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return topic_process


def initalize_camera():
    topic_command = ["gz", "topic", "-e", "-t", "/Camera0/image", "--json-output"]  # I hardcoded. Otherrobot has this
    topic_process = subprocess.Popen(topic_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return topic_process


def read_gyro(gyro_instance):
    return json.loads(gyro_instance.stdout.readline())


def get_camera_json(camera_instance):
    while True:
        raw_data_msg['camera'] = json.loads(camera_instance.stdout.readline())
        time.sleep(0.0001)


def get_gyro_json(gyro_instance):
    while True:
        raw_data_msg['gyro'] = json.loads(gyro_instance.stdout.readline())
        time.sleep(0.0001)


def read_camera(raw_data_msg):
    raw_data = copy.deepcopy(raw_data_msg['camera'])
    msg = raw_data
    if len(msg) > 0:
        data = msg['data']
        height = int(msg['width'])
        width = int(msg['height'])
        decoded_data = list(base64.b64decode(data))
        new_rgb = np.array(decoded_data, dtype=np.uint8)
        bgr = new_rgb.reshape(width, height, 3)
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    else:
        return []


if __name__ == '__main__':
    world = check_the_flag()
    runtime_data = dict()
    config = FEAGI.build_up_from_configuration()
    feagi_settings = config['feagi_settings'].copy()
    agent_settings = config['agent_settings'].copy()
    default_capabilities = config['default_capabilities'].copy()
    message_to_feagi = config['message_to_feagi'].copy()
    capabilities = config['capabilities'].copy()

    actuators.start_generic_opu(capabilities)

    # # # FEAGI registration # # # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    # - - - - - - - - - - - - - - - - - - #
    feagi_settings, runtime_data, api_address, feagi_ipu_channel, feagi_opu_channel = \
        FEAGI.connect_to_feagi(feagi_settings, runtime_data, agent_settings, capabilities,
                               __version__)
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # overwrite manual
    threading.Thread(target=retina.vision_progress, args=(default_capabilities, feagi_settings, camera_data,),
                     daemon=True).start()

    # camera
    camera_instance = initalize_camera()
    threading.Thread(target=get_camera_json, args=(camera_instance,), daemon=True).start()
    # gyro
    gyro_instance = initalize_gyro()
    threading.Thread(target=get_gyro_json, args=(gyro_instance,), daemon=True).start()
    # server_command = f"gz sim -v 4 {world} -s -r"
    # gui_command = "gz sim -v 4 -g"
    # server_process = subprocess.Popen(server_command, shell=True)
    # gui_process = subprocess.Popen(gui_command, shell=True)

    print("Creating a new entity in Gazebo...")
    time.sleep(2)
    create_entity()
    while True:
        try:
            raw_frame = read_camera(raw_data_msg)
            # Post image into vision
            previous_frame_data, rgb, default_capabilities = retina.process_visual_stimuli(
                raw_frame,
                default_capabilities,
                previous_frame_data,
                rgb, capabilities)
            message_from_feagi = pns.message_from_feagi
            # INSERT SENSORS INTO the FEAGI DATA SECTION BEGIN
            message_to_feagi = pns.generate_feagi_data(rgb, message_to_feagi)
            if message_from_feagi:
                obtained_signals = pns.obtain_opu_data(message_from_feagi)

            # Add gyro data into feagi data
            data_from_gyro = raw_data_msg['gyro']
            gyro = {'0': [data_from_gyro['orientation']['x'], data_from_gyro['orientation']['y'],
                          data_from_gyro['orientation']['z']]}
            if gyro:
                message_to_feagi = sensors.create_data_for_feagi('gyro', capabilities, message_to_feagi, gyro,
                                                                 symmetric=True, measure_enable=True)

            # Sending data to FEAGI
            pns.signals_to_feagi(message_to_feagi, feagi_ipu_channel, agent_settings, feagi_settings)
            message_to_feagi.clear()
            time.sleep(feagi_settings['feagi_burst_speed'])
        except KeyboardInterrupt as ke:
            print("ERROR: ", ke)
            # Terminate all processes after 60 minutes or interruption
            # server_process.terminate()
            # gui_process.terminate()

            # Wait for processes to cleanly exit
            # server_process.wait()
            # gui_process.wait()
            break
