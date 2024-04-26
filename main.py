import tkinter as tk
from tkinter import filedialog, messagebox, Scrollbar, Canvas
from PIL import Image, ImageTk
from pillow_heif import register_heif_opener

register_heif_opener()


def open_heic():
    file_path = filedialog.askopenfilename(filetypes=[("HEIC files", "*.heic")])
    if not file_path:
        return
    global heic_image, heic_photo
    heic_image = Image.open(file_path)
    heic_photo = ImageTk.PhotoImage(heic_image)
    canvas.config(scrollregion=(0, 0, heic_image.width, heic_image.height))
    canvas.delete("all")
    canvas.create_image(0, 0, image=heic_photo, anchor='nw')
    adjust_window_size(heic_image.width, heic_image.height)


def adjust_window_size(img_width, img_height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    new_width = min(img_width, screen_width)
    new_height = min(img_height, screen_height)
    root.geometry(f"{new_width}x{new_height}")


def save_as_jpeg():
    if 'heic_image' in globals():
        file_path = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG files", "*.jpg")])
        if file_path:
            heic_image.save(file_path, format='JPEG')


def save_as_png():
    if 'heic_image' in globals():
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if file_path:
            heic_image.save(file_path, format='PNG')


def batch_convert(target_format):
    file_paths = filedialog.askopenfilenames(filetypes=[("HEIC files", "*.heic")])
    if not file_paths:
        return
    save_folder = filedialog.askdirectory()
    if not save_folder:
        return
    for file_path in file_paths:
        image = Image.open(file_path)
        file_name = file_path.split("/")[-1].split(".")[0]
        save_path = f"{save_folder}/{file_name}.{target_format}"
        image.save(save_path, format="JPEG" if target_format == "jpg" else "PNG")
    messagebox.showinfo("Batch Conversion", "Conversion Completed Successfully!")


def show_credits():
    messagebox.showinfo("Credits", "Developed by Hayden Dunlap")


def on_mousewheel(event):
    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


def on_canvas_drag(event):
    canvas.scan_dragto(event.x, event.y, gain=1)


def on_canvas_press(event):
    canvas.scan_mark(event.x, event.y)


root = tk.Tk()
root.title("HEIC Viewer and Converter")

root.configure(bg='#2B2B2B')
button_color = '#3C3F41'
text_color = '#CCCCCC'
font_spec = ('Helvetica', 10)

root.geometry("800x600")

canvas = Canvas(root, width=600, height=400, bg='#313335', bd=0, highlightthickness=0)
vbar = Scrollbar(root, orient='vertical', command=canvas.yview)
hbar = Scrollbar(root, orient='horizontal', command=canvas.xview)
canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

canvas.grid(row=0, column=0, sticky='nsew')
vbar.grid(row=0, column=1, sticky='ns')
hbar.grid(row=1, column=0, sticky='ew')

root.bind_all("<MouseWheel>", on_mousewheel)

canvas.bind("<ButtonPress-1>", on_canvas_press)
canvas.bind("<B1-Motion>", on_canvas_drag)

root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

button_frame = tk.Frame(root, bg='#2B2B2B')
button_frame.grid(row=2, column=0, columnspan=2, sticky='ew')

buttons = [
    ("Open HEIC", open_heic),
    ("Save as JPEG", save_as_jpeg),
    ("Save as PNG", save_as_png),
    ("Batch Convert to JPEG", lambda: batch_convert("jpg")),
    ("Batch Convert to PNG", lambda: batch_convert("png")),
    ("Show Credits", show_credits)
]

for text, command in buttons:
    btn = tk.Button(button_frame, text=text, command=command, bg=button_color, fg=text_color, font=font_spec,
                    relief='flat')
    btn.pack(side=tk.LEFT, padx=10, pady=5)

root.mainloop()
