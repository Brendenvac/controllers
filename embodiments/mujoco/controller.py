#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Copyright 2016-present Neuraville Inc. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
==============================================================================
"""

import threading
import copy
from time import sleep
from feagi_connector import sensors
from feagi_connector import actuators
from feagi_connector import retina as retina
from feagi_connector import pns_gateway as pns
from feagi_connector.version import __version__
from feagi_connector import feagi_interface as feagi
import time, random
import mujoco, mujoco.viewer

# Global variable section
camera_data = {"vision": []}  # This will be heavily relies for vision
paused = False


RUNTIME = 600 # (seconds) //timeout time
SPEED   = 120 # simulation step speed


def pause_standing(data, start_pos):
    data.qpos = start_pos 

def pause_standing_ctrl(data, start_pos): #this does not work lol it stresses him out
    current_pos = data.qpos[7:]
    start_pos = start_pos[7:]
    for i, pos in enumerate(current_pos):
            if (pos < start_pos[i]):
                data.ctrl[i] += .01
            elif (pos > start_pos[i]):
                data.ctrl[i] -= .01
    
def action(obtained_data, capabilities):
    """
    This is where you can make the robot do something based on FEAGI data. The variable
    obtained_data contains the data from FEAGI. The variable capabilities comes from
    the configuration.json file. It will need the capability to measure how much power it can control
    and calculate using the FEAGI data.

    obtained_data: dictionary.
    capabilities: dictionary.
    """
    recieve_servo_data = actuators.get_servo_data(obtained_data)
    recieve_servo_position_data = actuators.get_servo_position_data(obtained_data)

    if obtained_data:
        print("obtained data d: %d", obtained_data)
        
    if recieve_servo_position_data:
        # output like {0:0.50, 1:0.20, 2:0.30} # example but the data comes from your capabilities' servo range
        print("servo position data d: %d", recieve_servo_position_data)
        for real_id in recieve_servo_position_data:
            servo_number = real_id
            new_power = recieve_servo_position_data[real_id]
            data.ctrl[servo_number] = new_power
            
    if recieve_servo_data:
        # example output: {0: 0.245, 2: 1.0}
        print("servo data d: %d", recieve_servo_data)
        for real_id in recieve_servo_data:
            servo_number = real_id
            new_power = recieve_servo_data[real_id]
            data.ctrl[servo_number] = new_power
        

    """ recieve_gyro_data = actuators.get_gyro_data(obtained_data)

    if recieve_gyro_data:
        print("gyro data: %d", recieve_gyro_data)
        # example output: {0: 0.245, 2: 1.0}
            for real_id in recieve_gyro_data:
            servo_number = real_id
            new_power = recieve_servo_data[real_id]
            data.ctrl[servo_number] = new_power """
            


if __name__ == "__main__":
    # Generate runtime dictionary
    runtime_data = {"vision": [], "stimulation_period": None, "feagi_state": None,
                    "feagi_network": None}

    # This function will build the capabilities from your configuration.json and read the
    # args input. First, it will gather all details from your configuration.json. Once it's done,
    # it will read all input args, such as flags. Once it detects flags from the user, it will override
    # the configuration and use the input provided by the user.
    config = feagi.build_up_from_configuration()
    feagi_settings = config['feagi_settings'].copy()
    agent_settings = config['agent_settings'].copy()
    default_capabilities = config['default_capabilities'].copy()
    message_to_feagi = config['message_to_feagi'].copy()
    capabilities = config['capabilities'].copy()

    # Simply copying and pasting the code below will do the full work for you. It basically checks
    # and updates the network to ensure that it can connect with FEAGI. If it doesn't find FEAGI,
    # it will just wait and display "waiting on FEAGI...".
    # # # FEAGI registration # # # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
    feagi_settings, runtime_data, api_address, feagi_ipu_channel, feagi_opu_channel = \
        feagi.connect_to_feagi(feagi_settings, runtime_data, agent_settings, capabilities,
                               __version__)
    # - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

    # The function `create_runtime_default_list` will design and generate a complete JSON object
    # in the configuration, mainly for vision only. Once it's done, it will get the configuration JSON,
    # override all keys generated by this function, and store them into the same capabilities for
    # the rest of controller runtime.
    default_capabilities = pns.create_runtime_default_list(default_capabilities, capabilities)

    # This is for processing the data and updating in real-time based on the user's activity in BV,
    # such as cortical size, blink, reload genome, and other backend tasks.
    if "camera" in capabilities['input']:
        threading.Thread(target=retina.vision_progress,
                         args=(default_capabilities, feagi_settings, camera_data['vision'],),
                         daemon=True).start()
    
    model = mujoco.MjModel.from_xml_path('/Users/ctd/Downloads/humanoid-1.xml')
    data  = mujoco.MjData(model)
    
    actuators.start_servos(capabilities) # inserted here. This is not something you should do on your end. I will fix it shortly
    with mujoco.viewer.launch_passive(model, data) as viewer:
        start_time = time.time()
        start_pos = copy.copy(data.qpos) # get the starting positions before the simulation starts
        while viewer.is_running() and time.time() - start_time < RUNTIME:

            step_start = time.time()

            ##PAUSING 
            pause_standing(data, start_pos) #pause the model in the standing position
            #pause_standing_ctrl(data, start_pos) this doesn't work
            ##

            # steps the simulation forward 'tick'
            mujoco.mj_step(model, data)

            # The controller will grab the data from FEAGI in real-time
            message_from_feagi = pns.message_from_feagi
            if message_from_feagi:
                # Translate from feagi data to human readable data
                obtained_signals = pns.obtain_opu_data(message_from_feagi)
                pns.check_genome_status_no_vision(message_from_feagi)
                action(obtained_signals, data)

            ### READ POSITIONAL DATA HERE ###
            positions = data.qpos #all positions
            positions = positions[7:] #don't know what the first 7 positions are, but they're not joints so ignore them

            abdomen_positions = positions[:3] #first 3 are abdomen z,y,x
            abdomen_positions = abdomen_positions[::-1] #reverse it to x,y,z order

            """ for i, pos in enumerate(positions):
                print("[", i, "]", joints[i] ,f": {pos:{.3}g}") #print all joint positions"""
            print("data:" , data.sensordata)


            # Preparing data to send to FEAGI
            abdomen_gyro_data = {i: pos for i, pos in enumerate(abdomen_positions) if
                          pns.full_template_information_corticals}
            servo_data = {i: pos for i, pos in enumerate(positions[:20]) if
                          pns.full_template_information_corticals}
            
            #Creating message to send to FEAGI
            message_to_feagi_gyro = sensors.create_data_for_feagi('gyro',
                                                             capabilities,
                                                             message_to_feagi,
                                                             current_data=abdomen_gyro_data,
                                                             symmetric=True)
            message_to_feagi_servo = sensors.create_data_for_feagi('servo_position',
                                                             capabilities,
                                                             message_to_feagi,
                                                             current_data=servo_data,
                                                             symmetric=True)
            message_to_feagi_prox = sensors.create_data_for_feagi('proximity',
                                                             capabilities,
                                                             message_to_feagi,
                                                             current_data=servo_data[0],
                                                             symmetric=True, measure_enable=True)

            # Sends to feagi data
            pns.signals_to_feagi(message_to_feagi_servo, feagi_ipu_channel, agent_settings, feagi_settings)
            pns.signals_to_feagi(message_to_feagi_gyro, feagi_ipu_channel, agent_settings, feagi_settings)
            pns.signals_to_feagi(message_to_feagi_prox, feagi_ipu_channel, agent_settings, feagi_settings)

            # Clear data that is created by controller such as sensors
            message_to_feagi.clear()

            # Pick up changes to the physics state, apply perturbations, update options from GUI.
            viewer.sync()

            # Tick Speed # 
            time_until_next_step = (1/SPEED) - (time.time() - step_start)
            if time_until_next_step > 0:
                time.sleep(time_until_next_step)

        