import tkinter as tk
from tkinter import filedialog, messagebox, Scrollbar, Canvas, Frame, Label, Entry, Scale, StringVar, IntVar, DoubleVar, \
    BooleanVar, ttk, Menu, colorchooser, simpledialog
from PIL import Image, ImageTk, ImageOps, ImageEnhance, ImageFilter, ExifTags
from pillow_heif import register_heif_opener
import os
import json
import sys
import time
from datetime import datetime
from functools import partial
from threading import Thread
import pickle
import math

register_heif_opener()


def main():
    root = tk.Tk()
    root.geometry("1200x800")
    root.minsize(800, 600)

    app = HEICViewerApp(root)

    # Check if a file was passed as a command line argument
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        app.open_image_file(sys.argv[1])

    root.mainloop()


class HEICViewerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("HEIC Viewer and Converter")
        self.setup_variables()
        self.setup_ui()
        self.create_menu()
        self.setup_bindings()
        self.load_settings()
        self.update_theme()
        self.update_recent_files_menu()

    def setup_variables(self):
        self.heic_image = None
        self.original_image = None
        self.displayed_image = None
        self.heic_photo = None
        self.current_file_path = None
        self.zoom_level = 1.0
        self.rotation_angle = 0
        self.edit_history = []
        self.edit_position = -1
        self.edit_limit = 20
        self.is_dark_mode = BooleanVar(value=True)
        self.show_info = BooleanVar(value=True)
        self.quality_value = IntVar(value=90)
        self.recent_files = []
        self.max_recent_files = 10
        self.is_slideshow_active = False
        self.slideshow_delay = IntVar(value=3)
        self.current_directory = None
        self.directory_files = []
        self.current_directory_index = -1
        self.last_save_directory = os.path.expanduser("~")
        self.last_open_directory = os.path.expanduser("~")
        self.is_fullscreen = False
        self.crop_start_x = None
        self.crop_start_y = None
        self.is_cropping = False
        self.crop_rectangle = None
        self.image_info = StringVar(value="No image loaded")
        self.status_message = StringVar(value="Ready")
        self.brightness_value = DoubleVar(value=1.0)
        self.contrast_value = DoubleVar(value=1.0)
        self.sharpness_value = DoubleVar(value=1.0)
        self.settings_file = os.path.join(os.path.expanduser("~"), ".heicviewer_settings.json")

    def setup_ui(self):
        self.root.configure(bg='#2B2B2B')
        self.setup_styles()

        self.main_frame = Frame(self.root, bg=self.get_theme_color("bg"))
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.setup_toolbar()
        self.setup_canvas_area()
        self.setup_sidebar()
        self.setup_status_bar()

    def setup_styles(self):
        self.colors = {
            "dark": {
                "bg": "#2B2B2B",
                "canvas_bg": "#313335",
                "button_bg": "#3C3F41",
                "text": "#CCCCCC",
                "highlight": "#4B6EAF",
                "sidebar_bg": "#383838"
            },
            "light": {
                "bg": "#F2F2F2",
                "canvas_bg": "#FFFFFF",
                "button_bg": "#E0E0E0",
                "text": "#333333",
                "highlight": "#5C8AE6",
                "sidebar_bg": "#E8E8E8"
            }
        }

        self.style = ttk.Style()
        self.style.theme_use('clam')

    def get_theme_color(self, key):
        theme = "dark" if self.is_dark_mode.get() else "light"
        return self.colors[theme][key]

    def update_theme(self):
        bg_color = self.get_theme_color("bg")
        canvas_bg = self.get_theme_color("canvas_bg")
        button_bg = self.get_theme_color("button_bg")
        text_color = self.get_theme_color("text")
        highlight_color = self.get_theme_color("highlight")
        sidebar_bg = self.get_theme_color("sidebar_bg")

        self.root.configure(bg=bg_color)
        self.main_frame.configure(bg=bg_color)
        self.canvas.configure(bg=canvas_bg)
        self.sidebar_frame.configure(bg=sidebar_bg)
        self.toolbar_frame.configure(bg=bg_color)
        self.status_bar.configure(bg=bg_color)
        self.status_label.configure(bg=bg_color, fg=text_color)
        self.info_label.configure(bg=bg_color, fg=text_color)

        for widget in self.toolbar_frame.winfo_children():
            if isinstance(widget, tk.Button):
                widget.configure(bg=button_bg, fg=text_color, activebackground=highlight_color)

        for widget in self.sidebar_frame.winfo_children():
            if isinstance(widget, tk.Label):
                widget.configure(bg=sidebar_bg, fg=text_color)
            elif isinstance(widget, tk.Scale):
                widget.configure(bg=sidebar_bg, fg=text_color, troughcolor=canvas_bg, activebackground=highlight_color)
            elif isinstance(widget, tk.Button):
                widget.configure(bg=button_bg, fg=text_color, activebackground=highlight_color)
            elif isinstance(widget, tk.Frame):
                widget.configure(bg=sidebar_bg)
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label):
                        child.configure(bg=sidebar_bg, fg=text_color)
                    elif isinstance(child, tk.Button):
                        child.configure(bg=button_bg, fg=text_color, activebackground=highlight_color)
                    elif isinstance(child, tk.Scale):
                        child.configure(bg=sidebar_bg, fg=text_color, troughcolor=canvas_bg,
                                        activebackground=highlight_color)

        if self.displayed_image:
            self.update_image()

    def setup_toolbar(self):
        self.toolbar_frame = Frame(self.main_frame, bg=self.get_theme_color("bg"))
        self.toolbar_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        buttons = [
            ("Open", self.open_heic),
            ("Save JPEG", self.save_as_jpeg),
            ("Save PNG", self.save_as_png),
            ("Batch Convert", self.show_batch_dialog),
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Zoom In", self.zoom_in),
            ("Zoom Out", self.zoom_out),
            ("Rotate Left", self.rotate_left),
            ("Rotate Right", self.rotate_right),
            ("Flip H", self.flip_horizontal),
            ("Flip V", self.flip_vertical),
            ("Crop", self.start_crop),
            ("Reset", self.reset_image)
        ]

        for text, command in buttons:
            btn = tk.Button(self.toolbar_frame, text=text, command=command,
                            bg=self.get_theme_color("button_bg"),
                            fg=self.get_theme_color("text"),
                            font=('Helvetica', 10),
                            relief='flat',
                            padx=5,
                            pady=2,
                            width=8)
            btn.pack(side=tk.LEFT, padx=2, pady=2)

    def setup_canvas_area(self):
        self.canvas_frame = Frame(self.main_frame, bg=self.get_theme_color("bg"))
        self.canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.canvas = Canvas(self.canvas_frame,
                             bg=self.get_theme_color("canvas_bg"),
                             bd=0,
                             highlightthickness=0)
        self.vbar = Scrollbar(self.canvas_frame, orient='vertical', command=self.canvas.yview)
        self.hbar = Scrollbar(self.canvas_frame, orient='horizontal', command=self.canvas.xview)

        self.canvas.configure(yscrollcommand=self.vbar.set, xscrollcommand=self.hbar.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.vbar.grid(row=0, column=1, sticky='ns')
        self.hbar.grid(row=1, column=0, sticky='ew')

        self.canvas_frame.grid_rowconfigure(0, weight=1)
        self.canvas_frame.grid_columnconfigure(0, weight=1)

    def setup_sidebar(self):
        self.sidebar_frame = Frame(self.main_frame, bg=self.get_theme_color("sidebar_bg"), width=200)
        self.sidebar_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        Label(self.sidebar_frame, text="Image Adjustments", font=('Helvetica', 12, 'bold'),
              bg=self.get_theme_color("sidebar_bg"),
              fg=self.get_theme_color("text")).pack(pady=10)

        adjust_frame = Frame(self.sidebar_frame, bg=self.get_theme_color("sidebar_bg"))
        adjust_frame.pack(fill=tk.X, padx=10, pady=5)

        Label(adjust_frame, text="Brightness:",
              bg=self.get_theme_color("sidebar_bg"),
              fg=self.get_theme_color("text")).pack(anchor=tk.W)

        brightness_scale = Scale(adjust_frame, from_=0.0, to=2.0, resolution=0.1,
                                 orient=tk.HORIZONTAL, variable=self.brightness_value,
                                 command=self.apply_adjustments,
                                 bg=self.get_theme_color("sidebar_bg"),
                                 fg=self.get_theme_color("text"),
                                 troughcolor=self.get_theme_color("canvas_bg"),
                                 length=180)
        brightness_scale.pack(fill=tk.X)

        Label(adjust_frame, text="Contrast:",
              bg=self.get_theme_color("sidebar_bg"),
              fg=self.get_theme_color("text")).pack(anchor=tk.W)

        contrast_scale = Scale(adjust_frame, from_=0.0, to=2.0, resolution=0.1,
                               orient=tk.HORIZONTAL, variable=self.contrast_value,
                               command=self.apply_adjustments,
                               bg=self.get_theme_color("sidebar_bg"),
                               fg=self.get_theme_color("text"),
                               troughcolor=self.get_theme_color("canvas_bg"),
                               length=180)
        contrast_scale.pack(fill=tk.X)

        Label(adjust_frame, text="Sharpness:",
              bg=self.get_theme_color("sidebar_bg"),
              fg=self.get_theme_color("text")).pack(anchor=tk.W)

        sharpness_scale = Scale(adjust_frame, from_=0.0, to=2.0, resolution=0.1,
                                orient=tk.HORIZONTAL, variable=self.sharpness_value,
                                command=self.apply_adjustments,
                                bg=self.get_theme_color("sidebar_bg"),
                                fg=self.get_theme_color("text"),
                                troughcolor=self.get_theme_color("canvas_bg"),
                                length=180)
        sharpness_scale.pack(fill=tk.X)

        filter_frame = Frame(self.sidebar_frame, bg=self.get_theme_color("sidebar_bg"))
        filter_frame.pack(fill=tk.X, padx=10, pady=5)

        Label(filter_frame, text="Image Filters", font=('Helvetica', 11, 'bold'),
              bg=self.get_theme_color("sidebar_bg"),
              fg=self.get_theme_color("text")).pack(pady=5)

        filters = [
            ("None", self.filter_none),
            ("Blur", self.filter_blur),
            ("Sharpen", self.filter_sharpen),
            ("Contour", self.filter_contour),
            ("Detail", self.filter_detail),
            ("Emboss", self.filter_emboss),
            ("Edge Enhance", self.filter_edge_enhance),
            ("Smooth", self.filter_smooth),
            ("Grayscale", self.filter_grayscale),
            ("Sepia", self.filter_sepia)
        ]

        filter_buttons_frame = Frame(filter_frame, bg=self.get_theme_color("sidebar_bg"))
        filter_buttons_frame.pack(fill=tk.X)

        column, row = 0, 0
        for text, command in filters:
            btn = tk.Button(filter_buttons_frame, text=text, command=command,
                            bg=self.get_theme_color("button_bg"),
                            fg=self.get_theme_color("text"),
                            font=('Helvetica', 9),
                            relief='flat',
                            width=10)
            btn.grid(row=row, column=column, padx=2, pady=2, sticky='ew')
            column += 1
            if column > 1:
                column = 0
                row += 1

        export_frame = Frame(self.sidebar_frame, bg=self.get_theme_color("sidebar_bg"))
        export_frame.pack(fill=tk.X, padx=10, pady=10)

        Label(export_frame, text="JPEG Quality:",
              bg=self.get_theme_color("sidebar_bg"),
              fg=self.get_theme_color("text")).pack(anchor=tk.W)

        quality_scale = Scale(export_frame, from_=1, to=100,
                              orient=tk.HORIZONTAL, variable=self.quality_value,
                              bg=self.get_theme_color("sidebar_bg"),
                              fg=self.get_theme_color("text"),
                              troughcolor=self.get_theme_color("canvas_bg"),
                              length=180)
        quality_scale.pack(fill=tk.X)

        export_buttons_frame = Frame(export_frame, bg=self.get_theme_color("sidebar_bg"))
        export_buttons_frame.pack(fill=tk.X, pady=5)

        exports = [
            ("JPEG", self.save_as_jpeg),
            ("PNG", self.save_as_png),
            ("WebP", self.save_as_webp),
            ("TIFF", self.save_as_tiff),
            ("BMP", self.save_as_bmp),
            ("GIF", self.save_as_gif)
        ]

        column, row = 0, 0
        for text, command in exports:
            btn = tk.Button(export_buttons_frame, text=text, command=command,
                            bg=self.get_theme_color("button_bg"),
                            fg=self.get_theme_color("text"),
                            font=('Helvetica', 9),
                            relief='flat',
                            width=8)
            btn.grid(row=row, column=column, padx=2, pady=2, sticky='ew')
            column += 1
            if column > 2:
                column = 0
                row += 1

        theme_btn = tk.Button(self.sidebar_frame, text="Toggle Theme",
                              command=self.toggle_theme,
                              bg=self.get_theme_color("button_bg"),
                              fg=self.get_theme_color("text"),
                              font=('Helvetica', 10),
                              relief='flat')
        theme_btn.pack(fill=tk.X, padx=10, pady=5)

        info_btn = tk.Button(self.sidebar_frame, text="Show Metadata",
                             command=self.show_metadata,
                             bg=self.get_theme_color("button_bg"),
                             fg=self.get_theme_color("text"),
                             font=('Helvetica', 10),
                             relief='flat')
        info_btn.pack(fill=tk.X, padx=10, pady=5)

        slideshow_btn = tk.Button(self.sidebar_frame, text="Slideshow",
                                  command=self.toggle_slideshow,
                                  bg=self.get_theme_color("button_bg"),
                                  fg=self.get_theme_color("text"),
                                  font=('Helvetica', 10),
                                  relief='flat')
        slideshow_btn.pack(fill=tk.X, padx=10, pady=5)

    def setup_status_bar(self):
        self.status_bar = Frame(self.main_frame, height=25, bg=self.get_theme_color("bg"))
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.status_label = Label(self.status_bar, textvariable=self.status_message,
                                  bg=self.get_theme_color("bg"),
                                  fg=self.get_theme_color("text"),
                                  anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=10)

        self.info_label = Label(self.status_bar, textvariable=self.image_info,
                                bg=self.get_theme_color("bg"),
                                fg=self.get_theme_color("text"),
                                anchor=tk.E)
        self.info_label.pack(side=tk.RIGHT, padx=10)

    def create_menu(self):
        self.menu_bar = Menu(self.root)
        self.root.config(menu=self.menu_bar)

        file_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_heic, accelerator="Ctrl+O")
        file_menu.add_command(label="Save As JPEG", command=self.save_as_jpeg, accelerator="Ctrl+S")
        file_menu.add_command(label="Save As PNG", command=self.save_as_png, accelerator="Ctrl+P")
        file_menu.add_separator()

        self.recent_menu = Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        file_menu.add_separator()

        file_menu.add_command(label="Batch Convert", command=self.show_batch_dialog, accelerator="Ctrl+B")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Alt+F4")

        edit_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Redo", command=self.redo, accelerator="Ctrl+Y")
        edit_menu.add_separator()
        edit_menu.add_command(label="Rotate Left", command=self.rotate_left, accelerator="Ctrl+L")
        edit_menu.add_command(label="Rotate Right", command=self.rotate_right, accelerator="Ctrl+R")
        edit_menu.add_command(label="Flip Horizontal", command=self.flip_horizontal, accelerator="Ctrl+H")
        edit_menu.add_command(label="Flip Vertical", command=self.flip_vertical, accelerator="Ctrl+V")
        edit_menu.add_separator()
        edit_menu.add_command(label="Crop", command=self.start_crop, accelerator="Ctrl+X")
        edit_menu.add_command(label="Resize", command=self.resize_image, accelerator="Ctrl+E")
        edit_menu.add_separator()
        edit_menu.add_command(label="Reset Image", command=self.reset_image, accelerator="Ctrl+0")

        view_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Zoom In", command=self.zoom_in, accelerator="Ctrl++")
        view_menu.add_command(label="Zoom Out", command=self.zoom_out, accelerator="Ctrl+-")
        view_menu.add_command(label="Fit to Window", command=self.fit_to_window, accelerator="Ctrl+W")
        view_menu.add_command(label="Actual Size", command=self.actual_size, accelerator="Ctrl+1")
        view_menu.add_separator()
        view_menu.add_checkbutton(label="Show Info", variable=self.show_info, command=self.toggle_info)
        view_menu.add_command(label="Toggle Full Screen", command=self.toggle_fullscreen, accelerator="F11")
        view_menu.add_separator()
        view_menu.add_command(label="Toggle Theme", command=self.toggle_theme, accelerator="Ctrl+T")

        tools_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Show Metadata", command=self.show_metadata, accelerator="Ctrl+M")
        tools_menu.add_command(label="Image Info", command=self.show_image_info, accelerator="Ctrl+I")
        tools_menu.add_separator()

        filter_menu = Menu(tools_menu, tearoff=0)
        tools_menu.add_cascade(label="Filters", menu=filter_menu)

        filters = [
            ("None", self.filter_none),
            ("Blur", self.filter_blur),
            ("Sharpen", self.filter_sharpen),
            ("Contour", self.filter_contour),
            ("Detail", self.filter_detail),
            ("Emboss", self.filter_emboss),
            ("Edge Enhance", self.filter_edge_enhance),
            ("Smooth", self.filter_smooth),
            ("Grayscale", self.filter_grayscale),
            ("Sepia", self.filter_sepia)
        ]

        for text, command in filters:
            filter_menu.add_command(label=text, command=command)

        tools_menu.add_separator()
        tools_menu.add_command(label="Slideshow", command=self.toggle_slideshow, accelerator="F5")

        help_menu = Menu(self.menu_bar, tearoff=0)
        self.menu_bar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_command(label="Credits", command=self.show_credits)

    def setup_bindings(self):
        self.root.bind("<Control-o>", lambda e: self.open_heic())
        self.root.bind("<Control-s>", lambda e: self.save_as_jpeg())
        self.root.bind("<Control-p>", lambda e: self.save_as_png())
        self.root.bind("<Control-z>", lambda e: self.undo())
        self.root.bind("<Control-y>", lambda e: self.redo())
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-0>", lambda e: self.reset_image())
        self.root.bind("<Control-1>", lambda e: self.actual_size())
        self.root.bind("<Control-w>", lambda e: self.fit_to_window())
        self.root.bind("<Control-t>", lambda e: self.toggle_theme())
        self.root.bind("<Control-b>", lambda e: self.show_batch_dialog())
        self.root.bind("<Control-l>", lambda e: self.rotate_left())
        self.root.bind("<Control-r>", lambda e: self.rotate_right())
        self.root.bind("<Control-h>", lambda e: self.flip_horizontal())
        self.root.bind("<Control-v>", lambda e: self.flip_vertical())
        self.root.bind("<Control-x>", lambda e: self.start_crop())
        self.root.bind("<Control-e>", lambda e: self.resize_image())
        self.root.bind("<Control-m>", lambda e: self.show_metadata())
        self.root.bind("<Control-i>", lambda e: self.show_image_info())
        self.root.bind("<F5>", lambda e: self.toggle_slideshow())
        self.root.bind("<F11>", lambda e: self.toggle_fullscreen())
        self.root.bind("<Escape>", lambda e: self.cancel_fullscreen_or_crop())
        self.root.bind("<Left>", lambda e: self.previous_image())
        self.root.bind("<Right>", lambda e: self.next_image())
        self.root.bind("<Delete>", lambda e: self.delete_current_image())

        self.root.bind("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind("<ButtonPress-1>", self.on_canvas_press)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        self.canvas.bind("<ButtonPress-3>", self.show_context_menu)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.save_settings()
        self.root.quit()

    def load_settings(self):
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    settings = json.load(f)

                    if 'is_dark_mode' in settings:
                        self.is_dark_mode.set(settings['is_dark_mode'])
                    if 'show_info' in settings:
                        self.show_info.set(settings['show_info'])
                    if 'quality_value' in settings:
                        self.quality_value.set(settings['quality_value'])
                    if 'recent_files' in settings:
                        self.recent_files = settings['recent_files']
                    if 'slideshow_delay' in settings:
                        self.slideshow_delay.set(settings['slideshow_delay'])
                    if 'last_save_directory' in settings:
                        self.last_save_directory = settings['last_save_directory']
                    if 'last_open_directory' in settings:
                        self.last_open_directory = settings['last_open_directory']
        except Exception as e:
            self.status_message.set(f"Error loading settings: {str(e)}")

    def fill_to_window(self):
        if not self.displayed_image:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            self.root.after(100, self.fill_to_window)
            return

        img_width, img_height = self.displayed_image.size

        zoom_x = canvas_width / img_width
        zoom_y = canvas_height / img_height

        self.zoom_level = max(zoom_x, zoom_y)

        self.update_image()

    def save_settings(self):
        try:
            settings = {
                'is_dark_mode': self.is_dark_mode.get(),
                'show_info': self.show_info.get(),
                'quality_value': self.quality_value.get(),
                'recent_files': self.recent_files,
                'slideshow_delay': self.slideshow_delay.get(),
                'last_save_directory': self.last_save_directory,
                'last_open_directory': self.last_open_directory
            }

            with open(self.settings_file, 'w') as f:
                json.dump(settings, f)

        except Exception as e:
            self.status_message.set(f"Error saving settings: {str(e)}")

    def open_heic(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.last_open_directory,
            filetypes=[
                ("Image files", "*.heic *.HEIC *.heif *.HEIF *.jpg *.jpeg *.JPG *.JPEG *.png *.PNG")
            ]
        )

        if not file_path:
            return

        self.open_image_file(file_path)

    def open_image_file(self, file_path):
        try:
            self.last_open_directory = os.path.dirname(file_path)
            self.current_file_path = file_path

            self.original_image = Image.open(file_path)
            self.heic_image = self.original_image.copy()
            self.displayed_image = self.heic_image.copy()

            self.reset_image_state()
            self.add_to_recent_files(file_path)
            self.scan_directory(file_path)

            # Instead of simply updating, call fill_to_window to adjust zoom level appropriately.
            self.update_image()
            self.fill_to_window()

            self.status_message.set(f"Opened: {os.path.basename(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")
            self.status_message.set("Error opening file")

    def reset_image_state(self):
        self.zoom_level = 1.0
        self.rotation_angle = 0
        self.edit_history = []
        self.edit_position = -1
        self.brightness_value.set(1.0)
        self.contrast_value.set(1.0)
        self.sharpness_value.set(1.0)
        self.is_cropping = False
        if self.crop_rectangle:
            self.canvas.delete(self.crop_rectangle)
            self.crop_rectangle = None

    def add_to_recent_files(self, file_path):
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)

        self.recent_files.insert(0, file_path)

        if len(self.recent_files) > self.max_recent_files:
            self.recent_files = self.recent_files[:self.max_recent_files]

        self.update_recent_files_menu()

    def update_recent_files_menu(self):
        self.recent_menu.delete(0, tk.END)

        if not self.recent_files:
            self.recent_menu.add_command(label="No recent files", state=tk.DISABLED)
            return

        for file_path in self.recent_files:
            if os.path.exists(file_path):
                display_path = os.path.basename(file_path)
                self.recent_menu.add_command(
                    label=display_path,
                    command=lambda path=file_path: self.open_image_file(path)
                )

        self.recent_menu.add_separator()
        self.recent_menu.add_command(label="Clear Recent Files", command=self.clear_recent_files)

    def clear_recent_files(self):
        self.recent_files = []
        self.update_recent_files_menu()

    def scan_directory(self, file_path):
        directory = os.path.dirname(file_path)
        if directory:
            self.current_directory = directory
            self.directory_files = []

            for f in os.listdir(directory):
                if f.lower().endswith(('.heic', '.heif', '.jpg', '.jpeg', '.png')):
                    full_path = os.path.join(directory, f)
                    self.directory_files.append(full_path)

            self.directory_files.sort()

            if file_path in self.directory_files:
                self.current_directory_index = self.directory_files.index(file_path)
            else:
                self.current_directory_index = -1

    def update_image(self):
        if not self.displayed_image:
            return

        width, height = self.displayed_image.size
        scaled_width = int(width * self.zoom_level)
        scaled_height = int(height * self.zoom_level)

        if scaled_width < 1:
            scaled_width = 1
        if scaled_height < 1:
            scaled_height = 1

        # Resize the image with the new dimensions
        displayed = self.displayed_image.resize((scaled_width, scaled_height), Image.LANCZOS)
        self.heic_photo = ImageTk.PhotoImage(displayed)

        # Update the scroll region if you're using scrollbars
        self.canvas.config(scrollregion=(0, 0, scaled_width, scaled_height))
        self.canvas.delete("all")

        # Get canvas dimensions to center the image
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        x_center = canvas_width // 2
        y_center = canvas_height // 2

        # Draw the image centered on the canvas
        self.canvas.create_image(x_center, y_center, image=self.heic_photo, anchor='center')

        self.update_image_info()

    def update_image_info(self):
        if self.displayed_image and self.show_info.get():
            file_name = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled"
            width, height = self.displayed_image.size

            try:
                file_size = os.path.getsize(self.current_file_path)
                size_str = self.format_file_size(file_size)
            except:
                size_str = "Unknown"

            info_text = f"{file_name} | {width}x{height} | {size_str} | {int(self.zoom_level * 100)}%"
            self.image_info.set(info_text)
        else:
            self.image_info.set("")

    def format_file_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

    def save_as_jpeg(self):
        if not self.displayed_image:
            messagebox.showinfo("No Image", "No image is currently loaded.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=self.last_save_directory,
            defaultextension=".jpg",
            filetypes=[("JPEG files", "*.jpg")]
        )

        if file_path:
            try:
                self.last_save_directory = os.path.dirname(file_path)
                quality = self.quality_value.get()

                if self.displayed_image.mode == 'RGBA':
                    rgb_image = Image.new('RGB', self.displayed_image.size, (255, 255, 255))
                    rgb_image.paste(self.displayed_image, mask=self.displayed_image.split()[3])
                    rgb_image.save(file_path, format='JPEG', quality=quality)
                else:
                    self.displayed_image.save(file_path, format='JPEG', quality=quality)

                self.status_message.set(f"Saved as JPEG: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.status_message.set("Error saving file")

    def save_as_png(self):
        if not self.displayed_image:
            messagebox.showinfo("No Image", "No image is currently loaded.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=self.last_save_directory,
            defaultextension=".png",
            filetypes=[("PNG files", "*.png")]
        )

        if file_path:
            try:
                self.last_save_directory = os.path.dirname(file_path)
                self.displayed_image.save(file_path, format='PNG')
                self.status_message.set(f"Saved as PNG: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.status_message.set("Error saving file")

    def save_as_webp(self):
        if not self.displayed_image:
            messagebox.showinfo("No Image", "No image is currently loaded.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=self.last_save_directory,
            defaultextension=".webp",
            filetypes=[("WebP files", "*.webp")]
        )

        if file_path:
            try:
                self.last_save_directory = os.path.dirname(file_path)
                quality = self.quality_value.get()
                self.displayed_image.save(file_path, format='WEBP', quality=quality)
                self.status_message.set(f"Saved as WebP: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.status_message.set("Error saving file")

    def save_as_tiff(self):
        if not self.displayed_image:
            messagebox.showinfo("No Image", "No image is currently loaded.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=self.last_save_directory,
            defaultextension=".tiff",
            filetypes=[("TIFF files", "*.tiff *.tif")]
        )

        if file_path:
            try:
                self.last_save_directory = os.path.dirname(file_path)
                self.displayed_image.save(file_path, format='TIFF')
                self.status_message.set(f"Saved as TIFF: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.status_message.set("Error saving file")

    def save_as_bmp(self):
        if not self.displayed_image:
            messagebox.showinfo("No Image", "No image is currently loaded.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=self.last_save_directory,
            defaultextension=".bmp",
            filetypes=[("BMP files", "*.bmp")]
        )

        if file_path:
            try:
                self.last_save_directory = os.path.dirname(file_path)
                self.displayed_image.save(file_path, format='BMP')
                self.status_message.set(f"Saved as BMP: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.status_message.set("Error saving file")

    def save_as_gif(self):
        if not self.displayed_image:
            messagebox.showinfo("No Image", "No image is currently loaded.")
            return

        file_path = filedialog.asksaveasfilename(
            initialdir=self.last_save_directory,
            defaultextension=".gif",
            filetypes=[("GIF files", "*.gif")]
        )

        if file_path:
            try:
                self.last_save_directory = os.path.dirname(file_path)
                self.displayed_image.save(file_path, format='GIF')
                self.status_message.set(f"Saved as GIF: {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.status_message.set("Error saving file")

    def show_batch_dialog(self):
        batch_window = tk.Toplevel(self.root)
        batch_window.title("Batch Convert")
        batch_window.geometry("400x300")
        batch_window.resizable(False, False)
        batch_window.transient(self.root)
        batch_window.grab_set()

        if self.is_dark_mode.get():
            batch_window.configure(bg=self.get_theme_color("bg"))

        format_var = StringVar(value="jpg")
        quality_var = IntVar(value=self.quality_value.get())
        resize_var = BooleanVar(value=False)
        width_var = IntVar(value=1920)
        height_var = IntVar(value=1080)
        maintain_aspect = BooleanVar(value=True)

        Label(batch_window, text="Batch Convert Settings", font=("Helvetica", 14, "bold"),
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        format_frame = Frame(batch_window,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        format_frame.pack(fill=tk.X, padx=20, pady=5)

        Label(format_frame, text="Output Format:",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(side=tk.LEFT)

        formats = [("JPEG", "jpg"), ("PNG", "png"), ("WebP", "webp"), ("TIFF", "tiff"), ("BMP", "bmp")]

        format_subframe = Frame(format_frame,
                                bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        format_subframe.pack(side=tk.RIGHT)

        for text, value in formats:
            rb = tk.Radiobutton(format_subframe, text=text, variable=format_var, value=value,
                                bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                                fg=self.get_theme_color("text") if self.is_dark_mode.get() else None,
                                selectcolor=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None)
            rb.pack(side=tk.LEFT)

        quality_frame = Frame(batch_window,
                              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        quality_frame.pack(fill=tk.X, padx=20, pady=5)

        Label(quality_frame, text="Quality (JPEG/WebP):",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(side=tk.LEFT)

        quality_scale = Scale(quality_frame, from_=1, to=100, orient=tk.HORIZONTAL,
                              variable=quality_var, length=200,
                              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None,
                              troughcolor=self.get_theme_color("canvas_bg") if self.is_dark_mode.get() else None)
        quality_scale.pack(side=tk.RIGHT)

        resize_frame = Frame(batch_window,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        resize_frame.pack(fill=tk.X, padx=20, pady=5)

        resize_check = tk.Checkbutton(resize_frame, text="Resize Images", variable=resize_var,
                                      bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                                      fg=self.get_theme_color("text") if self.is_dark_mode.get() else None,
                                      selectcolor=self.get_theme_color(
                                          "button_bg") if self.is_dark_mode.get() else None)
        resize_check.pack(anchor=tk.W)

        dimension_frame = Frame(batch_window,
                                bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        dimension_frame.pack(fill=tk.X, padx=40, pady=5)

        Label(dimension_frame, text="Width:",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).grid(row=0, column=0, sticky=tk.W)

        width_entry = Entry(dimension_frame, textvariable=width_var, width=6)
        width_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        Label(dimension_frame, text="Height:",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).grid(row=1, column=0, sticky=tk.W)

        height_entry = Entry(dimension_frame, textvariable=height_var, width=6)
        height_entry.grid(row=1, column=1, sticky=tk.W, padx=5)

        aspect_check = tk.Checkbutton(dimension_frame, text="Maintain Aspect Ratio", variable=maintain_aspect,
                                      bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                                      fg=self.get_theme_color("text") if self.is_dark_mode.get() else None,
                                      selectcolor=self.get_theme_color(
                                          "button_bg") if self.is_dark_mode.get() else None)
        aspect_check.grid(row=2, column=0, columnspan=2, sticky=tk.W)

        button_frame = Frame(batch_window,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        convert_button = tk.Button(
            button_frame, text="Convert Files",
            command=lambda: self.batch_convert_files(
                format_var.get(), quality_var.get(),
                resize_var.get(), width_var.get(), height_var.get(),
                maintain_aspect.get(), batch_window
            ),
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        convert_button.pack(side=tk.LEFT, padx=10)

        cancel_button = tk.Button(
            button_frame, text="Cancel",
            command=batch_window.destroy,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        cancel_button.pack(side=tk.RIGHT, padx=10)

    def batch_convert_files(self, target_format, quality, do_resize, width, height, maintain_aspect, dialog):
        file_paths = filedialog.askopenfilenames(
            initialdir=self.last_open_directory,
            filetypes=[
                ("Image files", "*.heic *.HEIC *.heif *.HEIF *.jpg *.jpeg *.JPG *.JPEG *.png *.PNG")
            ]
        )

        if not file_paths:
            dialog.destroy()
            return

        save_folder = filedialog.askdirectory(initialdir=self.last_save_directory)

        if not save_folder:
            dialog.destroy()
            return

        self.last_save_directory = save_folder

        progress_window = tk.Toplevel(self.root)
        progress_window.title("Converting...")
        progress_window.geometry("400x100")
        progress_window.resizable(False, False)
        progress_window.transient(self.root)
        progress_window.grab_set()

        if self.is_dark_mode.get():
            progress_window.configure(bg=self.get_theme_color("bg"))

        Label(progress_window, text="Converting files...",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        progress = ttk.Progressbar(progress_window, orient="horizontal", length=350, mode="determinate")
        progress.pack(pady=10, padx=25)

        progress["maximum"] = len(file_paths)

        dialog.destroy()

        def process_files():
            try:
                for i, file_path in enumerate(file_paths):
                    base_name = os.path.basename(file_path)
                    file_name = os.path.splitext(base_name)[0]
                    save_path = os.path.join(save_folder, f"{file_name}.{target_format}")

                    img = Image.open(file_path)

                    if do_resize:
                        if maintain_aspect:
                            img.thumbnail((width, height), Image.LANCZOS)
                        else:
                            img = img.resize((width, height), Image.LANCZOS)

                    if target_format.lower() == "jpg":
                        if img.mode == 'RGBA':
                            rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                            rgb_img.paste(img, mask=img.split()[3])
                            rgb_img.save(save_path, format="JPEG", quality=quality)
                        else:
                            img.save(save_path, format="JPEG", quality=quality)
                    elif target_format.lower() == "webp":
                        img.save(save_path, format="WEBP", quality=quality)
                    else:
                        format_name = {"png": "PNG", "tiff": "TIFF", "bmp": "BMP"}
                        img.save(save_path, format=format_name.get(target_format.lower(), target_format.upper()))

                    progress["value"] = i + 1
                    self.root.update_idletasks()

                messagebox.showinfo("Batch Conversion", "Conversion completed successfully!", parent=progress_window)
                self.status_message.set(f"Converted {len(file_paths)} files to {target_format.upper()}")
            except Exception as e:
                messagebox.showerror("Error", f"Error during batch conversion: {str(e)}", parent=progress_window)
                self.status_message.set("Error during batch conversion")
            finally:
                progress_window.destroy()

        Thread(target=process_files).start()

    def on_mousewheel(self, event):
        if event.state & 0x4:  # Check if Ctrl key is pressed
            if event.delta > 0:
                self.zoom_in()
            else:
                self.zoom_out()
        else:
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_canvas_press(self, event):
        if self.is_cropping:
            self.crop_start_x = self.canvas.canvasx(event.x)
            self.crop_start_y = self.canvas.canvasy(event.y)

            if self.crop_rectangle:
                self.canvas.delete(self.crop_rectangle)

            self.crop_rectangle = self.canvas.create_rectangle(
                self.crop_start_x, self.crop_start_y,
                self.crop_start_x, self.crop_start_y,
                outline="red", width=2
            )
        else:
            self.canvas.scan_mark(event.x, event.y)

    def on_canvas_drag(self, event):
        if self.is_cropping and self.crop_start_x is not None and self.crop_start_y is not None:
            current_x = self.canvas.canvasx(event.x)
            current_y = self.canvas.canvasy(event.y)

            self.canvas.coords(
                self.crop_rectangle,
                self.crop_start_x, self.crop_start_y,
                current_x, current_y
            )
        else:
            self.canvas.scan_dragto(event.x, event.y, gain=1)

    def update_crop_rectangle(self):
        if self.crop_rectangle and self.crop_start_x is not None and self.crop_start_y is not None:
            self.canvas.coords(
                self.crop_rectangle,
                self.crop_start_x, self.crop_start_y,
                self.crop_start_x + 100, self.crop_start_y + 100
            )

    def on_canvas_release(self, event):
        if self.is_cropping and self.crop_rectangle:
            end_x = self.canvas.canvasx(event.x)
            end_y = self.canvas.canvasy(event.y)

            if abs(end_x - self.crop_start_x) > 10 and abs(end_y - self.crop_start_y) > 10:
                start_x = min(self.crop_start_x, end_x) / self.zoom_level
                start_y = min(self.crop_start_y, end_y) / self.zoom_level
                end_x = max(self.crop_start_x, end_x) / self.zoom_level
                end_y = max(self.crop_start_y, end_y) / self.zoom_level

                self.apply_crop(start_x, start_y, end_x, end_y)

            self.is_cropping = False
            self.canvas.delete(self.crop_rectangle)
            self.crop_rectangle = None
            self.crop_start_x = None
            self.crop_start_y = None

    def start_crop(self):
        if not self.displayed_image:
            return

        self.is_cropping = True
        self.status_message.set("Click and drag to select crop area")

    def apply_crop(self, start_x, start_y, end_x, end_y):
        if not self.displayed_image:
            return

        try:
            left = max(0, int(start_x))
            top = max(0, int(start_y))
            right = min(self.displayed_image.width, int(end_x))
            bottom = min(self.displayed_image.height, int(end_y))

            if right <= left or bottom <= top:
                return

            new_image = self.displayed_image.crop((left, top, right, bottom))

            self.add_to_history()
            self.displayed_image = new_image
            self.update_image()

            self.status_message.set(f"Cropped to {right - left}x{bottom - top}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to crop image: {str(e)}")
            self.status_message.set("Error cropping image")

    def zoom_in(self):
        if not self.displayed_image:
            return

        self.zoom_level *= 1.2
        self.update_image()

    def zoom_out(self):
        if not self.displayed_image:
            return

        self.zoom_level /= 1.2
        if self.zoom_level < 0.01:
            self.zoom_level = 0.01

        self.update_image()

    def actual_size(self):
        if not self.displayed_image:
            return

        self.zoom_level = 1.0
        self.update_image()

    def fit_to_window(self):
        if not self.displayed_image:
            return

        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            return

        img_width, img_height = self.displayed_image.size

        width_ratio = canvas_width / img_width
        height_ratio = canvas_height / img_height

        self.zoom_level = min(width_ratio, height_ratio) * 0.95

        self.update_image()

    def rotate_left(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.rotate(90, expand=True)
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.update_image()

        self.status_message.set(f"Rotated left to {self.rotation_angle}°")

    def rotate_right(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.rotate(-90, expand=True)
        self.rotation_angle = (self.rotation_angle - 90) % 360
        self.update_image()

        self.status_message.set(f"Rotated right to {self.rotation_angle}°")

    def flip_horizontal(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = ImageOps.mirror(self.displayed_image)
        self.update_image()

        self.status_message.set("Flipped horizontally")

    def flip_vertical(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = ImageOps.flip(self.displayed_image)
        self.update_image()

        self.status_message.set("Flipped vertically")

    def resize_image(self):
        if not self.displayed_image:
            return

        resize_window = tk.Toplevel(self.root)
        resize_window.title("Resize Image")
        resize_window.geometry("300x200")
        resize_window.resizable(False, False)
        resize_window.transient(self.root)
        resize_window.grab_set()

        if self.is_dark_mode.get():
            resize_window.configure(bg=self.get_theme_color("bg"))

        width, height = self.displayed_image.size

        new_width = IntVar(value=width)
        new_height = IntVar(value=height)
        maintain_aspect = BooleanVar(value=True)

        Label(resize_window, text="Resize Image", font=("Helvetica", 12, "bold"),
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        dim_frame = Frame(resize_window,
                          bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        dim_frame.pack(fill=tk.X, padx=20, pady=5)

        Label(dim_frame, text="Width:",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).grid(row=0, column=0, sticky=tk.W)

        width_entry = Entry(dim_frame, textvariable=new_width, width=6)
        width_entry.grid(row=0, column=1, sticky=tk.W, padx=5)

        Label(dim_frame, text="px",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).grid(row=0, column=2, sticky=tk.W)

        Label(dim_frame, text="Height:",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).grid(row=1, column=0, sticky=tk.W)

        height_entry = Entry(dim_frame, textvariable=new_height, width=6)
        height_entry.grid(row=1, column=1, sticky=tk.W, padx=5)

        Label(dim_frame, text="px",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).grid(row=1, column=2, sticky=tk.W)

        aspect_check = tk.Checkbutton(resize_window, text="Maintain Aspect Ratio", variable=maintain_aspect,
                                      bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                                      fg=self.get_theme_color("text") if self.is_dark_mode.get() else None,
                                      selectcolor=self.get_theme_color(
                                          "button_bg") if self.is_dark_mode.get() else None)
        aspect_check.pack(padx=20, pady=5, anchor=tk.W)

        def update_height(*args):
            if maintain_aspect.get():
                try:
                    new_w = int(new_width.get())
                    if new_w > 0:
                        aspect = width / height
                        new_height.set(int(new_w / aspect))
                except:
                    pass

        def update_width(*args):
            if maintain_aspect.get():
                try:
                    new_h = int(new_height.get())
                    if new_h > 0:
                        aspect = width / height
                        new_width.set(int(new_h * aspect))
                except:
                    pass

        new_width.trace_add("write", update_height)
        new_height.trace_add("write", update_width)

        button_frame = Frame(resize_window,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        def apply_resize():
            try:
                w = int(new_width.get())
                h = int(new_height.get())

                if w <= 0 or h <= 0:
                    messagebox.showerror("Invalid Dimensions", "Width and height must be positive values.",
                                         parent=resize_window)
                    return

                self.add_to_history()
                self.displayed_image = self.displayed_image.resize((w, h), Image.LANCZOS)
                self.update_image()

                self.status_message.set(f"Resized to {w}x{h}")
                resize_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to resize image: {str(e)}", parent=resize_window)

        resize_button = tk.Button(
            button_frame, text="Resize",
            command=apply_resize,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        resize_button.pack(side=tk.LEFT, padx=10)

        cancel_button = tk.Button(
            button_frame, text="Cancel",
            command=resize_window.destroy,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        cancel_button.pack(side=tk.RIGHT, padx=10)

    def reset_image(self):
        if not self.original_image:
            return

        self.add_to_history()
        self.displayed_image = self.original_image.copy()
        self.brightness_value.set(1.0)
        self.contrast_value.set(1.0)
        self.sharpness_value.set(1.0)
        self.update_image()

        self.status_message.set("Image reset to original")

    def add_to_history(self):
        if not self.displayed_image:
            return

        if len(self.edit_history) > self.edit_position + 1:
            self.edit_history = self.edit_history[:self.edit_position + 1]

        if len(self.edit_history) >= self.edit_limit:
            self.edit_history.pop(0)
        else:
            self.edit_position += 1

        self.edit_history.append(self.displayed_image.copy())

    def undo(self):
        if not self.displayed_image or self.edit_position <= 0:
            return

        self.edit_position -= 1
        self.displayed_image = self.edit_history[self.edit_position].copy()
        self.update_image()

        self.status_message.set("Undo")

    def redo(self):
        if not self.displayed_image or self.edit_position >= len(self.edit_history) - 1:
            return

        self.edit_position += 1
        self.displayed_image = self.edit_history[self.edit_position].copy()
        self.update_image()

        self.status_message.set("Redo")

    def apply_adjustments(self, *args):
        if not self.heic_image:
            return

        try:
            self.displayed_image = self.heic_image.copy()

            brightness = self.brightness_value.get()
            contrast = self.contrast_value.get()
            sharpness = self.sharpness_value.get()

            if brightness != 1.0:
                enhancer = ImageEnhance.Brightness(self.displayed_image)
                self.displayed_image = enhancer.enhance(brightness)

            if contrast != 1.0:
                enhancer = ImageEnhance.Contrast(self.displayed_image)
                self.displayed_image = enhancer.enhance(contrast)

            if sharpness != 1.0:
                enhancer = ImageEnhance.Sharpness(self.displayed_image)
                self.displayed_image = enhancer.enhance(sharpness)

            self.update_image()
        except Exception as e:
            self.status_message.set(f"Error applying adjustments: {str(e)}")

    def filter_none(self):
        if not self.heic_image:
            return

        self.add_to_history()
        self.displayed_image = self.heic_image.copy()
        self.apply_adjustments()

    def filter_blur(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.filter(ImageFilter.BLUR)
        self.update_image()

        self.status_message.set("Applied Blur filter")

    def filter_sharpen(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.filter(ImageFilter.SHARPEN)
        self.update_image()

        self.status_message.set("Applied Sharpen filter")

    def filter_contour(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.filter(ImageFilter.CONTOUR)
        self.update_image()

        self.status_message.set("Applied Contour filter")

    def filter_detail(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.filter(ImageFilter.DETAIL)
        self.update_image()

        self.status_message.set("Applied Detail filter")

    def filter_emboss(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.filter(ImageFilter.EMBOSS)
        self.update_image()

        self.status_message.set("Applied Emboss filter")

    def filter_edge_enhance(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.filter(ImageFilter.EDGE_ENHANCE)
        self.update_image()

        self.status_message.set("Applied Edge Enhance filter")

    def filter_smooth(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = self.displayed_image.filter(ImageFilter.SMOOTH)
        self.update_image()

        self.status_message.set("Applied Smooth filter")

    def filter_grayscale(self):
        if not self.displayed_image:
            return

        self.add_to_history()
        self.displayed_image = ImageOps.grayscale(self.displayed_image.convert("RGB"))
        self.update_image()

        self.status_message.set("Applied Grayscale filter")

    def filter_sepia(self):
        if not self.displayed_image:
            return

        self.add_to_history()

        img = self.displayed_image.convert("RGB")
        sepia_palette = []
        r, g, b = (239, 224, 185)

        for i in range(256):
            sepia_palette.extend((r * i // 255, g * i // 255, b * i // 255))

        grayscale = ImageOps.grayscale(img)
        self.displayed_image = ImageOps.colorize(grayscale, "#000", "#fff")

        self.update_image()
        self.status_message.set("Applied Sepia filter")

    def toggle_theme(self):
        self.is_dark_mode.set(not self.is_dark_mode.get())
        self.update_theme()

    def toggle_info(self):
        self.update_image_info()

    def show_metadata(self):
        if not self.current_file_path:
            messagebox.showinfo("No Image", "No image is currently loaded.")
            return

        try:
            img = Image.open(self.current_file_path)

            metadata_window = tk.Toplevel(self.root)
            metadata_window.title("Image Metadata")
            metadata_window.geometry("600x400")
            metadata_window.transient(self.root)
            metadata_window.grab_set()

            if self.is_dark_mode.get():
                metadata_window.configure(bg=self.get_theme_color("bg"))

            Label(metadata_window, text="Image Metadata", font=("Helvetica", 14, "bold"),
                  bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                  fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

            text_frame = Frame(metadata_window,
                               bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            scroll = Scrollbar(text_frame)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)

            text_bg = self.get_theme_color("canvas_bg") if self.is_dark_mode.get() else "#FFFFFF"
            text_fg = self.get_theme_color("text") if self.is_dark_mode.get() else "#000000"

            text_widget = tk.Text(text_frame, width=80, height=20, bg=text_bg, fg=text_fg, wrap=tk.WORD)
            text_widget.pack(fill=tk.BOTH, expand=True)

            scroll.config(command=text_widget.yview)
            text_widget.config(yscrollcommand=scroll.set)

            text_widget.insert(tk.END, f"Filename: {os.path.basename(self.current_file_path)}\n")
            text_widget.insert(tk.END, f"Format: {img.format}\n")
            text_widget.insert(tk.END, f"Mode: {img.mode}\n")
            text_widget.insert(tk.END, f"Size: {img.width} x {img.height}\n")

            try:
                size = os.path.getsize(self.current_file_path)
                text_widget.insert(tk.END, f"File Size: {self.format_file_size(size)}\n")
            except:
                pass

            text_widget.insert(tk.END, "\nEXIF Data:\n")

            try:
                exif = img.getexif()
                if exif:
                    for tag_id, value in exif.items():
                        tag = ExifTags.TAGS.get(tag_id, tag_id)
                        if isinstance(value, bytes):
                            value = value.hex()
                        text_widget.insert(tk.END, f"{tag}: {value}\n")
                else:
                    text_widget.insert(tk.END, "No EXIF data found.\n")
            except Exception as e:
                text_widget.insert(tk.END, f"Error reading EXIF data: {str(e)}\n")

            text_widget.config(state=tk.DISABLED)

            button_frame = Frame(metadata_window,
                                 bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
            button_frame.pack(fill=tk.X, pady=10)

            close_button = tk.Button(
                button_frame, text="Close",
                command=metadata_window.destroy,
                bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
                fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
            )
            close_button.pack()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to read metadata: {str(e)}")

    def show_image_info(self):
        if not self.displayed_image:
            messagebox.showinfo("No Image", "No image is currently loaded.")
            return

        info_window = tk.Toplevel(self.root)
        info_window.title("Image Information")
        info_window.geometry("400x300")
        info_window.transient(self.root)
        info_window.grab_set()

        if self.is_dark_mode.get():
            info_window.configure(bg=self.get_theme_color("bg"))

        Label(info_window, text="Image Information", font=("Helvetica", 14, "bold"),
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        info_frame = Frame(info_window,
                           bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        info_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        width, height = self.displayed_image.size
        mode = self.displayed_image.mode

        try:
            file_size = os.path.getsize(self.current_file_path)
            size_str = self.format_file_size(file_size)
        except:
            size_str = "Unknown"

        info = [
            ("Filename", os.path.basename(self.current_file_path) if self.current_file_path else "Untitled"),
            ("Format", self.heic_image.format if self.heic_image and self.heic_image.format else "Unknown"),
            ("Dimensions", f"{width} x {height} pixels"),
            ("Resolution", f"{width * height} pixels"),
            ("Color Mode", mode),
            ("Color Depth", f"{self.get_bit_depth(mode)} bits per pixel"),
            ("File Size", size_str),
            ("Aspect Ratio", self.get_aspect_ratio(width, height)),
            ("Current Zoom", f"{int(self.zoom_level * 100)}%"),
            ("Rotation", f"{self.rotation_angle}°")
        ]

        row = 0
        for label_text, value_text in info:
            Label(info_frame, text=f"{label_text}:", anchor=tk.W, font=("Helvetica", 10, "bold"),
                  bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                  fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).grid(row=row, column=0,
                                                                                             sticky=tk.W, pady=3)

            Label(info_frame, text=value_text, anchor=tk.W,
                  bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                  fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).grid(row=row, column=1,
                                                                                             sticky=tk.W, pady=3,
                                                                                             padx=10)

            row += 1

        button_frame = Frame(info_window,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        button_frame.pack(fill=tk.X, pady=10)

        close_button = tk.Button(
            button_frame, text="Close",
            command=info_window.destroy,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        close_button.pack()

    def get_bit_depth(self, mode):
        mode_depths = {
            "1": 1,
            "L": 8,
            "P": 8,
            "RGB": 24,
            "RGBA": 32,
            "CMYK": 32,
            "YCbCr": 24,
            "LAB": 24,
            "HSV": 24,
            "I": 32,
            "F": 32
        }
        return mode_depths.get(mode, "Unknown")

    def get_aspect_ratio(self, width, height):
        def gcd(a, b):
            return a if b == 0 else gcd(b, a % b)

        if width and height:
            divisor = gcd(width, height)
            w = width // divisor
            h = height // divisor

            if w > 100 or h > 100:
                return f"{width / height:.3f}:1"
            else:
                return f"{w}:{h}"
        return "Unknown"

    def toggle_slideshow(self):
        if not self.directory_files:
            messagebox.showinfo("No Directory", "Please open an image file first to scan its directory.")
            return

        if self.is_slideshow_active:
            self.is_slideshow_active = False
            self.status_message.set("Slideshow stopped")
            return

        slideshow_settings = tk.Toplevel(self.root)
        slideshow_settings.title("Slideshow Settings")
        slideshow_settings.geometry("300x150")
        slideshow_settings.transient(self.root)
        slideshow_settings.grab_set()

        if self.is_dark_mode.get():
            slideshow_settings.configure(bg=self.get_theme_color("bg"))

        Label(slideshow_settings, text="Slideshow Settings", font=("Helvetica", 12, "bold"),
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        delay_frame = Frame(slideshow_settings,
                            bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        delay_frame.pack(fill=tk.X, padx=20, pady=5)

        Label(delay_frame, text="Delay (seconds):",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(side=tk.LEFT)

        delay_scale = Scale(delay_frame, from_=1, to=10, orient=tk.HORIZONTAL,
                            variable=self.slideshow_delay, length=150,
                            bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
                            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None,
                            troughcolor=self.get_theme_color("canvas_bg") if self.is_dark_mode.get() else None)
        delay_scale.pack(side=tk.RIGHT)

        button_frame = Frame(slideshow_settings,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        button_frame.pack(fill=tk.X, padx=20, pady=10)

        def start_slideshow():
            slideshow_settings.destroy()
            self.is_slideshow_active = True
            self.status_message.set("Slideshow started")
            self.run_slideshow()

        start_button = tk.Button(
            button_frame, text="Start",
            command=start_slideshow,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        start_button.pack(side=tk.LEFT, padx=10)

        cancel_button = tk.Button(
            button_frame, text="Cancel",
            command=slideshow_settings.destroy,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        cancel_button.pack(side=tk.RIGHT, padx=10)

    def run_slideshow(self):
        if not self.is_slideshow_active:
            return

        self.next_image()

        delay_ms = self.slideshow_delay.get() * 1000
        self.root.after(delay_ms, self.run_slideshow)

    def previous_image(self):
        if not self.directory_files or self.current_directory_index <= 0:
            return

        self.current_directory_index -= 1
        self.open_image_file(self.directory_files[self.current_directory_index])

    def next_image(self):
        if not self.directory_files or self.current_directory_index >= len(self.directory_files) - 1:
            if self.is_slideshow_active and self.directory_files:
                self.current_directory_index = 0
                self.open_image_file(self.directory_files[self.current_directory_index])
            return

        self.current_directory_index += 1
        self.open_image_file(self.directory_files[self.current_directory_index])

    def delete_current_image(self):
        if not self.current_file_path:
            return

        response = messagebox.askyesno("Confirm Delete",
                                       f"Are you sure you want to delete {os.path.basename(self.current_file_path)}?")

        if not response:
            return

        try:
            os.remove(self.current_file_path)

            self.recent_files = [f for f in self.recent_files if f != self.current_file_path]
            self.update_recent_files_menu()

            self.directory_files.remove(self.current_file_path)

            if not self.directory_files:
                self.current_file_path = None
                self.original_image = None
                self.heic_image = None
                self.displayed_image = None
                self.heic_photo = None
                self.current_directory_index = -1
                self.canvas.delete("all")
                self.status_message.set("Image deleted")
                self.image_info.set("No image loaded")
                return

            if self.current_directory_index >= len(self.directory_files):
                self.current_directory_index = len(self.directory_files) - 1

            self.open_image_file(self.directory_files[self.current_directory_index])
            self.status_message.set("Image deleted")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete image: {str(e)}")

    def toggle_fullscreen(self):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes('-fullscreen', self.is_fullscreen)

        if self.is_fullscreen:
            self.status_message.set("Press Escape to exit fullscreen")
        else:
            self.status_message.set("Exited fullscreen mode")

    def cancel_fullscreen_or_crop(self):
        if self.is_fullscreen:
            self.toggle_fullscreen()
        elif self.is_cropping:
            self.is_cropping = False
            if self.crop_rectangle:
                self.canvas.delete(self.crop_rectangle)
                self.crop_rectangle = None
            self.crop_start_x = None
            self.crop_start_y = None
            self.status_message.set("Crop canceled")

    def show_context_menu(self, event):
        if not self.displayed_image:
            return

        context_menu = Menu(self.root, tearoff=0)

        context_menu.add_command(label="Copy", command=self.copy_to_clipboard)
        context_menu.add_separator()
        context_menu.add_command(label="Save as JPEG", command=self.save_as_jpeg)
        context_menu.add_command(label="Save as PNG", command=self.save_as_png)
        context_menu.add_separator()
        context_menu.add_command(label="Rotate Left", command=self.rotate_left)
        context_menu.add_command(label="Rotate Right", command=self.rotate_right)
        context_menu.add_command(label="Flip Horizontal", command=self.flip_horizontal)
        context_menu.add_command(label="Flip Vertical", command=self.flip_vertical)
        context_menu.add_separator()
        context_menu.add_command(label="Crop", command=self.start_crop)
        context_menu.add_command(label="Resize", command=self.resize_image)
        context_menu.add_separator()
        context_menu.add_command(label="Reset Image", command=self.reset_image)

        context_menu.tk_popup(event.x_root, event.y_root)

    def copy_to_clipboard(self):
        if not self.displayed_image:
            return

        try:
            self.displayed_image.save("temp_clipboard.png", format="PNG")
            img = ImageTk.PhotoImage(file="temp_clipboard.png")
            self.root.clipboard_clear()
            self.root.clipboard_append(img)
            os.remove("temp_clipboard.png")
            self.status_message.set("Image copied to clipboard")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy to clipboard: {str(e)}")
            self.status_message.set("Error copying to clipboard")

    def show_about(self):
        about_window = tk.Toplevel(self.root)
        about_window.title("About HEIC Viewer")
        about_window.geometry("400x300")
        about_window.transient(self.root)
        about_window.grab_set()

        if self.is_dark_mode.get():
            about_window.configure(bg=self.get_theme_color("bg"))

        Label(about_window, text="HEIC Viewer and Converter", font=("Helvetica", 16, "bold"),
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        Label(about_window, text="Version 1.0.0", font=("Helvetica", 10),
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack()

        Label(about_window, text="A tool for viewing and converting HEIC/HEIF images.",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        Label(about_window, text="© 2025 HEIC Viewer Project",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=5)

        Label(about_window, text="Licensed under MIT License",
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack()

        button_frame = Frame(about_window,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        button_frame.pack(fill=tk.X, pady=20)

        close_button = tk.Button(
            button_frame, text="Close",
            command=about_window.destroy,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        close_button.pack()

    def show_shortcuts(self):
        shortcuts_window = tk.Toplevel(self.root)
        shortcuts_window.title("Keyboard Shortcuts")
        shortcuts_window.geometry("400x500")
        shortcuts_window.transient(self.root)
        shortcuts_window.grab_set()

        if self.is_dark_mode.get():
            shortcuts_window.configure(bg=self.get_theme_color("bg"))

        Label(shortcuts_window, text="Keyboard Shortcuts", font=("Helvetica", 16, "bold"),
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        text_frame = Frame(shortcuts_window,
                           bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        text_bg = self.get_theme_color("canvas_bg") if self.is_dark_mode.get() else "#FFFFFF"
        text_fg = self.get_theme_color("text") if self.is_dark_mode.get() else "#000000"

        text_widget = tk.Text(text_frame, width=40, height=20, bg=text_bg, fg=text_fg)
        scroll = Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scroll.set)

        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        shortcuts = [
            ("File Operations", [
                ("Ctrl+O", "Open Image"),
                ("Ctrl+S", "Save as JPEG"),
                ("Ctrl+P", "Save as PNG"),
                ("Ctrl+B", "Batch Convert")
            ]),
            ("Editing", [
                ("Ctrl+Z", "Undo"),
                ("Ctrl+Y", "Redo"),
                ("Ctrl+L", "Rotate Left"),
                ("Ctrl+R", "Rotate Right"),
                ("Ctrl+H", "Flip Horizontal"),
                ("Ctrl+V", "Flip Vertical"),
                ("Ctrl+X", "Crop"),
                ("Ctrl+E", "Resize"),
                ("Ctrl+0", "Reset Image")
            ]),
            ("Viewing", [
                ("Ctrl++", "Zoom In"),
                ("Ctrl+-", "Zoom Out"),
                ("Ctrl+W", "Fit to Window"),
                ("Ctrl+1", "Actual Size"),
                ("F11", "Toggle Full Screen"),
                ("Ctrl+T", "Toggle Theme")
            ]),
            ("Tools", [
                ("Ctrl+M", "Show Metadata"),
                ("Ctrl+I", "Image Info"),
                ("F5", "Slideshow")
            ]),
            ("Navigation", [
                ("Left Arrow", "Previous Image"),
                ("Right Arrow", "Next Image"),
                ("Delete", "Delete Current Image"),
                ("Escape", "Exit Full Screen/Cancel Crop")
            ])
        ]

        for category, items in shortcuts:
            text_widget.insert(tk.END, f"{category}:\n", "heading")

            for key, desc in items:
                text_widget.insert(tk.END, f"  {key:<10} - {desc}\n")

            text_widget.insert(tk.END, "\n")

        text_widget.tag_configure("heading", font=("Helvetica", 10, "bold"))
        text_widget.config(state=tk.DISABLED)

        button_frame = Frame(shortcuts_window,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        button_frame.pack(fill=tk.X, pady=10)

        close_button = tk.Button(
            button_frame, text="Close",
            command=shortcuts_window.destroy,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        close_button.pack()

    def show_credits(self):
        credits_window = tk.Toplevel(self.root)
        credits_window.title("Credits")
        credits_window.geometry("400x300")
        credits_window.transient(self.root)
        credits_window.grab_set()

        if self.is_dark_mode.get():
            credits_window.configure(bg=self.get_theme_color("bg"))

        Label(credits_window, text="Credits", font=("Helvetica", 16, "bold"),
              bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None,
              fg=self.get_theme_color("text") if self.is_dark_mode.get() else None).pack(pady=10)

        text_frame = Frame(credits_window,
                           bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        text_bg = self.get_theme_color("canvas_bg") if self.is_dark_mode.get() else "#FFFFFF"
        text_fg = self.get_theme_color("text") if self.is_dark_mode.get() else "#000000"

        text_widget = tk.Text(text_frame, width=40, height=12, bg=text_bg, fg=text_fg, wrap=tk.WORD)
        scroll = Scrollbar(text_frame, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scroll.set)

        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        credits_text = """
HEIC Viewer and Converter uses the following libraries:

- Python 3: Programming language
- Tkinter: GUI library
- Pillow (PIL Fork): Image processing library
- pillow_heif: HEIC/HEIF image support

Special thanks to:
- All contributors to the open-source libraries used
- The Python community
- Everyone who provided feedback and suggestions

Icons and UI design inspired by modern image viewers and editors.
"""

        text_widget.insert(tk.END, credits_text)
        text_widget.config(state=tk.DISABLED)

        button_frame = Frame(credits_window,
                             bg=self.get_theme_color("bg") if self.is_dark_mode.get() else None)
        button_frame.pack(fill=tk.X, pady=10)

        close_button = tk.Button(
            button_frame, text="Close",
            command=credits_window.destroy,
            bg=self.get_theme_color("button_bg") if self.is_dark_mode.get() else None,
            fg=self.get_theme_color("text") if self.is_dark_mode.get() else None
        )
        close_button.pack()

if __name__ == "__main__":
    main()
