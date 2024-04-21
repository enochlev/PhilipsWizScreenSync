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
        
    def discover_bulbs(self, manual_ip):
        manual_ip = None
        bulbs = self.loop.run_until_complete(discovery.discover_lights())
        self.bulbs = bulbs
        manual_light = wizlight(manual_ip)
        self.bulbs.append(manual_light)
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
    IDLE = "IDLE"
    RUNNING = "RUNNING"

    def __init__(self, root):
        self.root = root
        self.manager = WizLightManager()
        self.screen_options = {}  # store screen options for each bulb
        self.running = False  # flag to check if the lights update task is running
        self.task = None  # store the running task
        self.state = self.IDLE

        # Set window title and icon
        self.root.title("Wiz Light Controller")
        self.root.iconbitmap(resource_path("icon.ico"))

        # Logo
        self.logo = tk.PhotoImage(file=resource_path("icon.gif")) # Load the icon as a PhotoImage
        self.logo_label = tk.Label(self.root, image=self.logo)
        self.logo_label.grid(row=0, column=0, padx=10, pady=10)

        # Search Button
        self.search_button = tk.Button(self.root, text="Search for Wiz Lights", command=self.start_screen, width=25)
        self.search_button.grid(row=1, column=0, padx=10, pady=10)

        # Manually Add
        manual_ip = tk.StringVar()
        self.manual_input = tk.Entry(self.root,textvariable=manual_ip, width = 15)
        self.manual_label = tk.Label(self.root, text='Manually Add:', font=('calibre',10, 'bold'), anchor='w')
        # Pass input IP to lights
        self.manual_submit = tk.Button(self.root, text="Submit", command=lambda:self.start_screen(manual_ip), width=10) #
        self.manual_label.grid(row=2, column=0, sticky="w", padx=10)
        self.manual_input.grid(row=2, column=0, sticky="e")
        self.manual_submit.grid(row=2, column=1, padx=10)

        # Center the window on the screen
        self.center_window()
    def adjust_window_size(self):
        self.root.update_idletasks()
        self.root.geometry('')  # This sets the window size to its natural size.

    def center_window(self):
        # Center the window on the screen
        self.root.update_idletasks()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        ws = self.root.winfo_screenwidth()
        hs = self.root.winfo_screenheight()
        x = (ws/2) - (w/2)
        y = (hs/2) - (h/2)
        self.root.geometry('%dx%d+%d+%d' % (w, h, x, y))

    def start_screen(self, manual_ip = None):
        """Press Button to search for IP address"""
        self.manager.discover_bulbs(manual_ip)

        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Transition to the main screen
        self.run_screen()



    def run_screen(self):
        # Set up a frame for better layout and padding
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.grid(row=0, column=0, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Radio buttons
        options = ["disable", "top", "bottom", "left", "right", "full"]
        extended_options = ["VibrantSelector", "Median"]
        for i, bulb in enumerate(self.manager.bulbs_ips):
            self.screen_options[bulb] = tk.StringVar(value="full")  # default to full screen
            bulb_label = tk.Label(main_frame, text=bulb)
            bulb_label.grid(row=i, column=0, padx=5, pady=5, sticky="w")

            for j, option in enumerate(options):
                rad_button = tk.Radiobutton(main_frame, text=option, variable=self.screen_options[bulb], value=option)
                rad_button.grid(row=i, column=j+1, padx=5)

            # Test button for each bulb
            test_button = tk.Button(main_frame, text="Test", command=lambda bulb=bulb: self.test_bulb(bulb))
            test_button.grid(row=i, column=len(options)+1, padx=5, pady=5)

        # Run button
        self.run_button = tk.Button(main_frame, text="Run", command=self.toggle_run)
        self.run_button.grid(row=len(self.manager.bulbs)+2, column=0, columnspan=len(options)+2, pady=10)

        # Slider for update frequency
        self.frequency = tk.DoubleVar(value=0.15)  # Default value
        frequency_label = tk.Label(main_frame, text="Update Frequency (in seconds). Lower values may cause lag, but makes PC run harder.")
        frequency_label.grid(row=len(self.manager.bulbs)+3, column=0, columnspan=len(options)+2, sticky="w", pady=5)
        frequency_slider = tk.Scale(main_frame, from_=0.00, to=2.0, resolution=0.05, orient="horizontal", variable=self.frequency)
        frequency_slider.grid(row=len(self.manager.bulbs)+4, column=0, columnspan=len(options)+2, sticky="we", padx=5, pady=5)


        self.algorithm_choice = tk.StringVar(value="LeVibrantV1")  # Default value
        algorithm_label = tk.Label(main_frame, text="Color Processing Algorithm")
        algorithm_label.grid(row=len(self.manager.bulbs) + 5, column=0, columnspan=len(options) + 2, sticky="w", pady=5)
        algorithms = ["LeVibrantV1", "Median"]

        # Calculate starting column for centered placement
        total_columns = len(options) + 2  # +2 accounts for the bulb label and the test button
        center_column = total_columns // 2
        half_algorithms = len(algorithms) // 2
        start_col = center_column - half_algorithms

        for index, alg in enumerate(algorithms):
            alg_radio = tk.Radiobutton(main_frame, text=alg, variable=self.algorithm_choice, value=alg)
            alg_radio.grid(row=len(self.manager.bulbs) + 6, column=start_col + index, padx=5)
        self.adjust_window_size()
        self.center_window()

    def dominant_vibrant_color(self,frame):
        # Convert the RGB frame to HSV
        median = [max(int(i), 10) for i in np.median(frame, axis=0)]

        frame = frame[frame.max(axis=1) > 120]

        max_value = frame.max(axis=1)
        min_value = frame.min(axis=1)
        diff = (max_value - min_value) + (min_value/2)

        # This will help in avoiding division by zero errors
        diff[diff == 0] = 1

        # Calculate the saturation
        s = diff / max_value
        s[max_value == 0] = 0  # if max is zero, then s should be zero, not NaN due to division

        # Filter the vibrant colors (Here, we take saturation value above 0.5 as vibrant, you can adjust this threshold)
        vibrant_pixels = frame[s > 0.7]

        if vibrant_pixels.size == 0:  # If no vibrant pixel found, return average color
            return median

        # Round the colors to group them (you can adjust the rounding to group more/less colors)
        rounded_pixels = (vibrant_pixels // 16) * 16

        # Find unique colors and their counts
        unique_colors, counts = np.unique(rounded_pixels, axis=0, return_counts=True)
        unique_colors = unique_colors[counts > 1]
        counts = counts[counts > 1]

        if unique_colors.size == 0:
            return median
        
        # Return the color with the maximum count
        return [int(c) for c in unique_colors[counts.argmax()]]

    def update_lights(self):
        if self.state != self.RUNNING:
            return
        rgbclr = []
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
            frame = frame[::80, ::80, :]
            frame = frame.reshape(-1, frame.shape[-1])

            if self.algorithm_choice.get()  == 'LeVibrantV1':
                rgbclr = self.dominant_vibrant_color(frame)
            elif self.algorithm_choice.get()  == 'Median':
                rgbclr = [max(int(i), 10) for i in np.median(frame, axis=0)]

            rgbclr.append(int(sum(rgbclr) / 3))
            # rgbclr.append(int(sum(rgbclr)/5))
            # Turn on the bulb with the new color and brightness
            self.manager.turn_on_lights([bulb], rgbclr)

        self.root.after(int(1000*self.frequency.get()), self.update_lights)

    def toggle_run(self):
        if self.state == self.IDLE:
            self.state = self.RUNNING
            self.run_button.config(text="Stop")
            self.update_lights()
        else:
            self.state = self.IDLE
            self.run_button.config(text="Run")
            self.root.after(150, self.update_lights)

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

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    import sys
    import os
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


if __name__ == '__main__':
    root = tk.Tk()
    app = App(root)
    root.mainloop()