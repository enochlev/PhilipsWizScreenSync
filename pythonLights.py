import asyncio
import tkinter as tk
from pywizlight import wizlight, PilotBuilder, discovery
import pyautogui
import numpy as np
import time

import asyncio

class WizLightManager:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.bulbs = []
        self.bulbs_ips = []
        
    def discover_bulbs(self):
        bulbs = self.loop.run_until_complete(discovery.discover_lights())
        self.bulbs = bulbs
        self.bulbs_ips = [i.ip for i in bulbs]
        return bulbs

    def get_light_state(self, bulb_ip):
        bulb = wizlight(bulb_ip)
        state = self.loop.run_until_complete(bulb.updateState())
        return state.get_state()
        
    def turn_on_lights(self, bulb_ips, color = None, wait=True):
        tasks = []
        
        PB = PilotBuilder()
        if type(color) is int:
            PB = PilotBuilder(scene=color)
        elif type(color) is list and len(color) == 3:
            PB = PilotBuilder(rgb=color)
        elif type(color) is list and len(color) == 4:
            PB = PilotBuilder(rgb=color[:3],brightness=color[3])


        for bulb_ip in bulb_ips:
            bulb = wizlight(bulb_ip)
            tasks.append(bulb.turn_on(PB))
        if wait:
            self.loop.run_until_complete(asyncio.gather(*tasks))
        else:
            for task in tasks:
                self.loop.run_until_complete(task)

    def turn_off_lights(self, bulb_ips, wait=True):
        tasks = []
        

        for bulb_ip in bulb_ips:
            bulb = wizlight(bulb_ip)
            tasks.append(bulb.turn_off())
        if wait:
            self.loop.run_until_complete(asyncio.gather(*tasks))
        else:
            for task in tasks:
                self.loop.run_until_complete(task)


class App:
    def __init__(self, root, manager):
        self.root = root
        self.manager = manager
        self.screen_options = {}  # store screen options for each bulb
        self.running = False  # flag to check if the lights update task is running
        self.task = None  # store the running task

        # Radio buttons
        options = ["disable", "top", "bottom", "left", "right", "full"]
        for i, bulb in enumerate(self.manager.bulbs_ips):
            self.screen_options[bulb] = tk.StringVar()
            self.screen_options[bulb].set("full")  # default to full screen
            bulb_label = tk.Label(root, text=bulb)
            bulb_label.grid(row=i, column=0)

            for j, option in enumerate(options):
                rad_button = tk.Radiobutton(root, text=option, variable=self.screen_options[bulb], value=option)
                rad_button.grid(row=i, column=j+1)

            # Test button for each bulb
            test_button = tk.Button(root, text="Test", command=lambda bulb=bulb: self.test_bulb(bulb))
            test_button.grid(row=i, column=len(options)+1)

        # Run button
        self.run_button = tk.Button(root, text="Run", command=self.update_lights)
        self.run_button.grid(row=len(self.manager.bulbs)+1, column=0, columnspan=len(options)+2)


    def update_lights(self):
        while True:
            for bulb in self.manager.bulbs_ips:
                # Get the selected screen portion
                selected = self.screen_options[bulb].get()

                if selected == "disable":
                    continue  # ignore this bulb

                # Calculate screen coordinates for the selected portion
                region = self.calculate_region(selected)

                # Take a screenshot of the selected screen portion
                img = pyautogui.screenshot(region=region)
                frame = np.array(img)

                # Calculate the median color
                frame = frame[::20, ::20, :]
                frame = frame.reshape(-1, frame.shape[-1])
                rgbclr = [max(int(i), 10) for i in np.median(frame, axis=0)]
                rgbclr.append(int(sum(rgbclr)/5))
                # Turn on the bulb with the new color and brightness
                self.manager.turn_on_lights([bulb], rgbclr)
        time.sleep(.15)

    def calculate_region(self, selected):
        screen_size = pyautogui.size()
        if selected == "full":
            return (0, 0, screen_size[0], screen_size[1])
        elif selected == "top":
            return (0, 0, screen_size[0], screen_size[1] * 0.425)  # 15% overlap
        elif selected == "bottom":
            return (0, screen_size[1] * 0.575, screen_size[0], screen_size[1] * 0.425)
        elif selected == "left":
            return (0, 0, screen_size[0] * 0.425, screen_size[1])
        elif selected == "right":
            return (screen_size[0] * 0.575, 0, screen_size[0] * 0.425, screen_size[1])

    def test_bulb(self, bulb_ip):

        turned_on = self.manager.get_light_state(bulb_ip)

        if turned_on:
            self.manager.turn_off_lights([bulb_ip])
            time.sleep(.5)
            self.manager.turn_on_lights([bulb_ip],wait=False)
        
        else:
            self.manager.turn_on_lights([bulb_ip])
            time.sleep(.5)
            self.manager.turn_off_lights([bulb_ip],wait=False)


if __name__ == '__main__':
    root = tk.Tk()
    root.title("Screen Sync")
    manager = WizLightManager()
    manager.discover_bulbs()
    app = App(root, manager)
    root.mainloop()