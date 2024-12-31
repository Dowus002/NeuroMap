import tkinter as tk
from tkinter import filedialog, messagebox
import pydicom
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import os

class MRIViewer:
    def __init__(self, master):
        self.master = master
        self.master.title("NeuroMAP")
        self.master.geometry("1200x800")
        self.master.configure(bg="black")

        self.image_data = None
        self.slice_index = 0
        self.history = []  # Stack to store previous image states
        self.redo_stack = []  # Stack for redo functionality
        self.bookmarks = {}  # Dictionary to store bookmarked slices
        self.dicom_files = []  # List to store DICOM files
        self.slice_count = 0  # Count of slices in the loaded 3D dataset

        self.create_menu()
        self.create_landing_screen()
        self.bind_shortcuts()

    def create_menu(self):
        menu = tk.Menu(self.master)
        self.master.config(menu=menu)

        # File Menu
        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Tab", command=self.new_tab)
        file_menu.add_command(label="Open", command=self.load_mri_image)
        file_menu.add_command(label="Save", command=self.save_image)
        file_menu.add_command(label="Exit", command=self.master.quit)

        # Edit Menu
        edit_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo)
        edit_menu.add_command(label="Redo", command=self.redo)

        # View Menu
        view_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Dark Mode", command=self.toggle_dark_mode)
        view_menu.add_command(label="Light Mode", command=self.toggle_light_mode)

        # Bookmarks Menu
        bookmarks_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Bookmarks", menu=bookmarks_menu)
        bookmarks_menu.add_command(label="Add Bookmark", command=self.add_bookmark)
        bookmarks_menu.add_command(label="View Bookmarks", command=self.view_bookmarks)

    def create_landing_screen(self):
        self.landing_frame = tk.Frame(self.master, bg="darkgrey", width=800, height=600)
        self.landing_frame.place(relx=0.5, rely=0.5, anchor="center")

        welcome_label = tk.Label(self.landing_frame, text="Welcome to the MRI Viewer", font=("Helvetica", 24), fg="black", bg="lightblue")
        welcome_label.pack(pady=50)

        start_button = tk.Button(self.landing_frame, text="Start", font=("Helvetica", 14), command=self.show_main_window)
        start_button.pack(pady=10)

    def show_main_window(self):
        self.landing_frame.place_forget()  # Remove landing screen
        self.create_widgets()

    def create_widgets(self):
        self.slice_slider = tk.Scale(self.master, from_=0, to=100, orient="horizontal", label="Slice Index", command=self.update_slice)
        self.slice_slider.pack(padx=10, pady=10)

        self.load_button = tk.Button(self.master, text="Load MRI Image", command=self.load_mri_image, bg="blue", fg="black", font=("Helvetica", 12))
        self.load_button.pack(pady=20)

        self.canvas_frame = tk.Frame(self.master)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True)

    def load_mri_image(self):
        file_paths = filedialog.askopenfilenames(filetypes=[("DICOM files", "*.dcm")])
        if file_paths:
            self.dicom_files = sorted(file_paths)  # Sort the files to load slices in order
            self.image_data = self.load_dicom_series(self.dicom_files)  # Load 3D DICOM data
            self.push_to_history(self.image_data)  # Push current image to history
            self.slice_count = len(self.image_data)  # Update slice count
            self.slice_slider.config(to=self.slice_count - 1)  # Set slider range to number of slices
            self.display_image(self.image_data)

    def load_dicom_series(self, dicom_files):
        """Load and return the 3D volume from the DICOM series."""
        slices = []
        for file in dicom_files:
            dicom_data = pydicom.dcmread(file)
            slices.append(dicom_data.pixel_array)
        return np.stack(slices, axis=0)  # Stack slices into a 3D volume

    def display_image(self, image_data):
        if len(image_data.shape) == 3:
            image_data = image_data[self.slice_index]  # Select the slice based on the slider

        fig = plt.Figure(figsize=(8, 6))
        ax = fig.add_subplot(111)
        ax.imshow(image_data, cmap='gray')  # Display image in grayscale
        ax.axis('off')  # Hide axis

        for widget in self.canvas_frame.winfo_children():
            widget.destroy()  # Clear previous canvas

        canvas = FigureCanvasTkAgg(fig, master=self.canvas_frame)
        canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
        canvas.draw()

    def update_slice(self, val):
        if self.image_data is not None:
            self.slice_index = int(val)
            if len(self.image_data.shape) == 3:
                self.display_image(self.image_data)  # Display the selected slice

    def save_image(self):
        if self.image_data is not None:
            file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg")])
            if file_path:
                if len(self.image_data.shape) == 3:
                    image_data = self.image_data[self.slice_index]  # Get the current slice
                else:
                    image_data = self.image_data  # For 2D images, just use the image as is

                img = Image.fromarray(image_data)
                img.save(file_path)
                messagebox.showinfo("Save Image", "Image saved successfully.")
        else:
            messagebox.showerror("Error", "No MRI image loaded to save.")

    def undo(self):
        if len(self.history) > 1:
            self.redo_stack.append(self.history.pop())  # Move last state to redo stack
            self.image_data = self.history[-1]  # Revert to previous state
            self.display_image(self.image_data)

    def redo(self):
        if self.redo_stack:
            self.image_data = self.redo_stack.pop()  # Get the last state from redo stack
            self.push_to_history(self.image_data)  # Push it back to history
            self.display_image(self.image_data)

    def add_bookmark(self):
        if self.image_data is not None:
            bookmark_name = f"Slice {self.slice_index}"
            self.bookmarks[bookmark_name] = self.slice_index
            messagebox.showinfo("Bookmark", f"Bookmark added for {bookmark_name}")
        else:
            messagebox.showerror("Error", "No image loaded to bookmark.")

    def view_bookmarks(self):
        if self.bookmarks:
            bookmarks_list = "\n".join([f"{name}: Slice {index}" for name, index in self.bookmarks.items()])
            messagebox.showinfo("Bookmarks", bookmarks_list)
        else:
            messagebox.showinfo("Bookmarks", "No bookmarks available.")

    def push_to_history(self, image_data):
        self.history.append(image_data.copy())

    def toggle_dark_mode(self):
        self.master.configure(bg="black")
        self.load_button.configure(bg="white", fg="black")

    def toggle_light_mode(self):
        self.master.configure(bg="white")
        self.load_button.configure(bg="blue", fg="black")

    def new_tab(self):
        new_window = tk.Toplevel(self.master)
        app = MRIViewer(new_window)

    def bind_shortcuts(self):
        self.master.bind("<Command-o>", lambda event: self.load_mri_image())
        self.master.bind("<Command-s>", lambda event: self.save_image())
        self.master.bind("<Command-n>", lambda event: self.new_tab())
        self.master.bind("<Command-z>", lambda event: self.undo())
        self.master.bind("<Command-y>", lambda event: self.redo())
        self.master.bind("<Command-b>", lambda event: self.add_bookmark())
        self.master.bind("<Command-Shift-B>", lambda event: self.view_bookmarks())

# Create and run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = MRIViewer(root)
    root.mainloop()

def load_image(self):
    file_paths = filedialog.askopenfilenames(filetypes=[("DICOM files", "*.dcm"), ("Image files", "*.png;*.jpg;*.jpeg")])
    if file_paths:
        self.image_files = sorted(file_paths)  # Sort the files to load images in order
        self.push_to_history(self.image_files)  # Push current state to history
        self.display_image(self.image_files[self.slice_index])  # Display first image

def display_image(self, image_file):
    """Display the image on the canvas."""
    if image_file.lower().endswith('.dcm'):
        # Load DICOM file
        dicom_data = pydicom.dcmread(image_file)
        image_data = dicom_data.pixel_array  # Get pixel array for DICOM
        if len(image_data.shape) == 3:  # If it's a 3D DICOM, use the selected slice
            image_data = image_data[self.slice_index]
        img = Image.fromarray(image_data)
    else:
        # Load regular image file (PNG/JPG)
        img = Image.open(image_file)
    
    img.thumbnail((800, 800))  # Resize the image to fit the window

    img_tk = ImageTk.PhotoImage(img)
    for widget in self.canvas_frame.winfo_children():
        widget.destroy()  # Clear previous canvas

    label = tk.Label(self.canvas_frame, image=img_tk)
    label.image = img_tk  # Keep a reference to avoid garbage collection
    label.pack(side=tk.TOP, fill=tk.BOTH, expand=1)

def save_image(self):
    if self.image_files:
        file_path = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png"), ("JPEG files", "*.jpg"), ("DICOM files", "*.dcm")])
        if file_path:
            image_file = self.image_files[self.slice_index]
            if image_file.lower().endswith('.dcm'):
                # Save DICOM file
                dicom_data = pydicom.dcmread(image_file)
                dicom_data.PixelData = dicom_data.pixel_array.tobytes()  # Save pixel data
                dicom_data.save_as(file_path)  # Save as DICOM
                messagebox.showinfo("Save Image", "DICOM file saved successfully.")
            else:
                # Save regular image file (PNG/JPG)
                img = Image.open(image_file)
                img.save(file_path)
                messagebox.showinfo("Save Image", "Image saved successfully.")
    else:
        messagebox.showerror("Error", "No image loaded to save.")

def update_slice(self, val):
    if self.image_files:
        image_file = self.image_files[self.slice_index]
        if image_file.lower().endswith('.dcm'):
            dicom_data = pydicom.dcmread(image_file)
            image_data = dicom_data.pixel_array
            if len(image_data.shape) == 3:
                self.slice_index = int(val)
                self.display_image(self.image_files[self.slice_index])
            else:
                self.display_image(image_file)  # If it's a 2D DICOM or non-DICOM
        else:
            self.display_image(image_file)  # For regular image files (PNG/JPG)

class MRIApp:
    def __init__(self, master):
        self.master = master
        self.master.title("MRI Analysis Tool")
        self.master.geometry("800x600")  # Adjust window size
        self.create_navigationbar()

    def create_navigationbar(self):
        # Create a menu bar
        menu = Menu(self.master)
        self.master.config(menu=menu)

        # Add navigation menu items
        file_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open File", command=self.open_file)
        file_menu.add_command(label="Save File", command=self.save_file)

        view_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Zoom In", command=self.zoom_in)
        view_menu.add_command(label="Zoom Out", command=self.zoom_out)

        tools_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Slice Navigation", command=self.slice_navigation)
        tools_menu.add_command(label="Adjust Brightness/Contrast", command=self.adjust_brightness_contrast)

        help_menu = Menu(menu, tearoff=0)
        menu.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.show_help)

    # Placeholder functions for menu commands
    def open_file(self):
        print("Open File clicked")

    def save_file(self):
        print("Save File clicked")

    def zoom_in(self):
        print("Zoom In clicked")

    def zoom_out(self):
        print("Zoom Out clicked")

    def slice_navigation(self):
        print("Slice Navigation clicked")

    def adjust_brightness_contrast(self):
        print("Adjust Brightness/Contrast clicked")

    def show_help(self):
        print("Help clicked")

# Main loop
if __name__ == "__main__":
    root = tk.Tk()
    app = MRIApp(root)
    root.mainloop()

  