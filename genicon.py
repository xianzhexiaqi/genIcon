"""
Icon Generator - Generate icons in multiple sizes and formats from any image.
Supports: PNG, ICO, JPG input/output. Sizes: 16, 32, 48, 64, 128, 256.
Includes interactive crop tool (1:1 crop, square or circle, with black dashed border).
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
import math
import os

# Pillow compatibility
try:
    _LANCZOS = Image.Resampling.LANCZOS
except AttributeError:
    _LANCZOS = getattr(Image, "LANCZOS", getattr(Image, "ANTIALIAS", 1))

SIZES = [16, 32, 48, 64, 128, 256]
FORMATS = {"PNG": "png", "ICO": "ico", "JPG": "jpg"}
CANVAS_MAX = 512


class IconGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Icon Generator")
        self.root.resizable(True, True)
        self.root.minsize(700, 550)

        self.original_img = None
        self.photo_img = None
        self._crop_active = False
        self.crop_shape_var = tk.StringVar(value="Square")
        self._preview_frame = None
        self._img_canvas = None
        self._disp_w = 0
        self._disp_h = 0

        # Crop state (display coords)
        self._crop_x1 = 0
        self._crop_y1 = 0
        self._crop_x2 = 0
        self._crop_y2 = 0
        self._drag_data = None
        self._resize_edge = None

        self._build_ui()

    def _build_ui(self):
        main = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # === Left panel ===
        left = ttk.Frame(main, width=280)
        main.add(left, weight=0)

        # File
        file_frame = ttk.LabelFrame(left, text="Input Image", padding=8)
        file_frame.pack(fill=tk.X, padx=5, pady=(5, 3))
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, state="readonly").pack(fill=tk.X)
        ttk.Button(file_frame, text="Browse...", command=self._browse).pack(fill=tk.X, pady=(4, 0))
        self.img_info_var = tk.StringVar(value="No image loaded")
        ttk.Label(file_frame, textvariable=self.img_info_var, foreground="gray").pack(anchor=tk.W)

        # Crop
        crop_frame = ttk.LabelFrame(left, text="Crop", padding=8)
        crop_frame.pack(fill=tk.X, padx=5, pady=3)
        shape_row = ttk.Frame(crop_frame)
        shape_row.pack(fill=tk.X)
        ttk.Label(shape_row, text="Shape:").pack(side=tk.LEFT)
        ttk.Radiobutton(
            shape_row, text="Square", value="Square",
            variable=self.crop_shape_var, command=self._on_shape_change,
        ).pack(side=tk.LEFT, padx=(4, 6))
        ttk.Radiobutton(
            shape_row, text="Circle", value="Circle",
            variable=self.crop_shape_var, command=self._on_shape_change,
        ).pack(side=tk.LEFT)
        self.crop_btn = ttk.Button(crop_frame, text="Start Crop (Square)", command=self._toggle_crop)
        self.crop_btn.pack(fill=tk.X, pady=(4, 0))
        self.crop_info_var = tk.StringVar(value="Click to enable square crop")
        ttk.Label(crop_frame, textvariable=self.crop_info_var, foreground="gray").pack(anchor=tk.W, pady=(4, 0))

        # Sizes
        size_frame = ttk.LabelFrame(left, text="Sizes", padding=8)
        size_frame.pack(fill=tk.X, padx=5, pady=3)
        self.size_vars = {}
        row, col = 0, 0
        for s in SIZES:
            var = tk.BooleanVar(value=True)
            self.size_vars[s] = var
            ttk.Checkbutton(size_frame, text=f"{s}×{s}", variable=var).grid(row=row, column=col, sticky=tk.W, padx=4, pady=2)
            col += 1
            if col >= 3:
                col = 0
                row += 1

        # Formats
        fmt_frame = ttk.LabelFrame(left, text="Formats", padding=8)
        fmt_frame.pack(fill=tk.X, padx=5, pady=3)
        self.fmt_vars = {}
        for i, name in enumerate(FORMATS):
            var = tk.BooleanVar(value=True)
            self.fmt_vars[name] = var
            ttk.Checkbutton(fmt_frame, text=name, variable=var).grid(row=0, column=i, sticky=tk.W, padx=8)

        # Quality
        q_frame = ttk.Frame(left)
        q_frame.pack(fill=tk.X, padx=13, pady=2)
        ttk.Label(q_frame, text="JPG Quality:").pack(side=tk.LEFT)
        self.quality_var = tk.IntVar(value=95)
        ttk.Spinbox(q_frame, from_=10, to=100, textvariable=self.quality_var, width=5).pack(side=tk.LEFT, padx=4)

        # Output
        out_frame = ttk.LabelFrame(left, text="Output", padding=8)
        out_frame.pack(fill=tk.X, padx=5, pady=3)
        self.output_var = tk.StringVar()
        ttk.Entry(out_frame, textvariable=self.output_var).pack(fill=tk.X)
        ttk.Button(out_frame, text="Choose Folder...", command=self._choose_output).pack(fill=tk.X, pady=(4, 0))

        # Generate
        ttk.Button(left, text="Generate Icons", command=self._generate).pack(fill=tk.X, padx=13, pady=8)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(left, textvariable=self.status_var, foreground="blue").pack(padx=8, anchor=tk.W)

        # === Right panel: preview ===
        right = ttk.Frame(main)
        main.add(right, weight=1)
        self.canvas_frame = ttk.LabelFrame(right, text="Preview", padding=4)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.canvas_container = ttk.Frame(self.canvas_frame)
        self.canvas_container.pack(fill=tk.BOTH, expand=True)
        self.placeholder = ttk.Label(self.canvas_container, text="Load an image to preview", foreground="gray", font=("", 12))
        self.placeholder.pack(expand=True)

    # ── File ──────────────────────────────────────────────

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[
                ("All supported", "*.png *.ico *.jpg *.jpeg *.bmp *.gif *.tiff"),
                ("PNG", "*.png"), ("ICO", "*.ico"), ("JPEG", "*.jpg *.jpeg"), ("All files", "*.*"),
            ],
        )
        if not path:
            return
        try:
            img = Image.open(path)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open image:\n{e}")
            return

        self.original_img = img.convert("RGBA")
        self.file_var.set(path)
        w, h = img.size
        ratio = "1:1" if w == h else f"{w}:{h} ({w/h:.2f})"
        self.img_info_var.set(f"Size: {w}×{h} | Ratio: {ratio}")
        if not self.output_var.get():
            self.output_var.set(os.path.dirname(path))

        # Reset crop (keep the selected shape)
        self._crop_active = False
        self.crop_btn.config(text=f"Start Crop ({self.crop_shape_var.get()})")
        self.crop_info_var.set(f"Click to enable {self.crop_shape_var.get().lower()} crop")

        self._show_preview()

    # ── Preview ───────────────────────────────────────────

    def _show_preview(self):
        if self.original_img is None:
            return
        for w in self.canvas_container.winfo_children():
            w.destroy()
        self._img_canvas = None

        img = self.original_img
        w, h = img.size
        cw = min(CANVAS_MAX, w)
        ch = min(CANVAS_MAX, h)
        scale = min(cw / w, ch / h) if w > cw or h > ch else 1.0
        self._disp_w = int(w * scale)
        self._disp_h = int(h * scale)

        self._preview_frame = tk.Frame(self.canvas_container, width=self._disp_w, height=self._disp_h)
        self._preview_frame.pack(expand=True)
        self._preview_frame.pack_propagate(False)

        preview = img.resize((self._disp_w, self._disp_h), _LANCZOS)
        self.photo_img = ImageTk.PhotoImage(preview)

        self._img_canvas = tk.Canvas(
            self._preview_frame, width=self._disp_w, height=self._disp_h,
            highlightthickness=0, bd=0, cursor="crosshair"
        )
        self._img_canvas.place(x=0, y=0)
        self._img_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo_img, tags="bg")

        # Bind mouse events for crop
        self._img_canvas.bind("<ButtonPress-1>", self._on_press)
        self._img_canvas.bind("<B1-Motion>", self._on_drag)
        self._img_canvas.bind("<ButtonRelease-1>", self._on_release)

        if self._crop_active:
            self._init_crop_box()
            self._draw_crop_overlay()

    # ── Crop toggle ───────────────────────────────────────

    def _crop_is_circle(self):
        return self.crop_shape_var.get().strip().lower() == "circle"

    def _on_shape_change(self):
        shape = self.crop_shape_var.get()
        if self._crop_active:
            self._draw_crop_overlay()
        else:
            self.crop_btn.config(text=f"Start Crop ({shape})")
            self.crop_info_var.set(f"Click to enable {shape.lower()} crop")

    def _toggle_crop(self):
        if self.original_img is None:
            messagebox.showwarning("Warning", "Please load an image first.")
            return
        if self._crop_active:
            self._crop_active = False
            self.crop_btn.config(text=f"Start Crop ({self.crop_shape_var.get()})")
            self.crop_info_var.set(f"Click to enable {self.crop_shape_var.get().lower()} crop")
            self._remove_crop_overlay()
        else:
            self._crop_active = True
            self.crop_btn.config(text="Cancel Crop")
            self._init_crop_box()
            self._draw_crop_overlay()

    def _init_crop_box(self):
        """Initialize crop box as a centered square (80% of canvas)."""
        sq = int(min(self._disp_w, self._disp_h) * 0.8)
        cx, cy = self._disp_w // 2, self._disp_h // 2
        self._crop_x1 = cx - sq // 2
        self._crop_y1 = cy - sq // 2
        self._crop_x2 = self._crop_x1 + sq
        self._crop_y2 = self._crop_y1 + sq

    def _get_crop_box_original(self):
        """Return (x1, y1, x2, y2) in original image coordinates."""
        if self._disp_w == 0 or self._disp_h == 0:
            return (0, 0, 0, 0)
        ow, oh = self.original_img.size
        sx = ow / self._disp_w
        sy = oh / self._disp_h
        return (
            int(self._crop_x1 * sx),
            int(self._crop_y1 * sy),
            int(self._crop_x2 * sx),
            int(self._crop_y2 * sy),
        )

    # ── Crop drawing ──────────────────────────────────────

    def _draw_crop_overlay(self):
        """Draw crop mask, dashed border, handles, and label on the image canvas."""
        if not self._img_canvas or not self._crop_active:
            return

        self._img_canvas.delete("crop")

        x1, y1, x2, y2 = self._crop_x1, self._crop_y1, self._crop_x2, self._crop_y2
        dw, dh = self._disp_w, self._disp_h

        # Darken outside regions (semi-transparent mask)
        regions = [
            (0, 0, dw, y1),        # top
            (0, y2, dw, dh),       # bottom
            (0, y1, x1, y2),       # left
            (x2, y1, dw, y2),      # right
        ]
        for rx1, ry1, rx2, ry2 in regions:
            if rx2 > rx1 and ry2 > ry1:
                self._img_canvas.create_rectangle(
                    rx1, ry1, rx2, ry2,
                    fill="black", stipple="gray50", outline="", tags="crop"
                )

        if self._crop_is_circle():
            # Darken the four corner slivers inside the box but outside the circle
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            r = (x2 - x1) / 2
            corners = [
                ((x1, y1), 180, 270),
                ((x2, y1), 270, 360),
                ((x2, y2), 0, 90),
                ((x1, y2), 90, 180),
            ]
            for (px, py), a0, a1 in corners:
                pts = []
                for i in range(25):
                    a = math.radians(a0 + (a1 - a0) * i / 24)
                    pts.extend([cx + r * math.cos(a), cy + r * math.sin(a)])
                pts.extend([px, py])
                self._img_canvas.create_polygon(
                    pts, fill="black", stipple="gray50", outline="", tags="crop"
                )
            # Black dashed circular border
            self._img_canvas.create_oval(
                x1, y1, x2, y2,
                outline="black", width=2, dash=(6, 4), tags="crop"
            )
        else:
            # Black dashed border
            self._img_canvas.create_rectangle(
                x1, y1, x2, y2,
                outline="black", width=2, dash=(6, 4), tags="crop"
            )

        # Corner handles
        hs = 5
        for cx, cy in [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]:
            self._img_canvas.create_rectangle(
                cx - hs, cy - hs, cx + hs, cy + hs,
                fill="black", outline="white", width=1, tags="crop"
            )

        # Dimension label
        box = self._get_crop_box_original()
        w, h = box[2] - box[0], box[3] - box[1]
        dim = f"Ø{w}" if self._crop_is_circle() else f"{w}×{h}"
        lx = x2 + 8 if x2 + 80 < dw else x1 - 8
        anchor = "nw" if x2 + 80 < dw else "ne"
        self._img_canvas.create_text(
            lx, y1, text=dim, fill="black",
            anchor=anchor, font=("Consolas", 10, "bold"), tags="crop"
        )

        self.crop_info_var.set(f"Crop: {dim} @ ({box[0]},{box[1]})")

    def _remove_crop_overlay(self):
        if self._img_canvas:
            self._img_canvas.delete("crop")

    # ── Crop interaction ──────────────────────────────────

    def _hit_edge(self, x, y):
        hs = 8
        x1, y1, x2, y2 = self._crop_x1, self._crop_y1, self._crop_x2, self._crop_y2
        # Corners
        for name, cx, cy in [("tl", x1, y1), ("tr", x2, y1), ("bl", x1, y2), ("br", x2, y2)]:
            if abs(x - cx) < hs and abs(y - cy) < hs:
                return name
        # Edges
        if y1 - hs < y < y1 + hs and x1 < x < x2:
            return "top"
        if y2 - hs < y < y2 + hs and x1 < x < x2:
            return "bottom"
        if x1 - hs < x < x1 + hs and y1 < y < y2:
            return "left"
        if x2 - hs < x < x2 + hs and y1 < y < y2:
            return "right"
        return None

    def _point_in_crop(self, x, y):
        """Whether (x, y) is inside the crop region; a circle only counts its inscribed disc."""
        if self._crop_is_circle():
            cx = (self._crop_x1 + self._crop_x2) / 2
            cy = (self._crop_y1 + self._crop_y2) / 2
            r = (self._crop_x2 - self._crop_x1) / 2
            return (x - cx) ** 2 + (y - cy) ** 2 <= r * r
        return self._crop_x1 <= x <= self._crop_x2 and self._crop_y1 <= y <= self._crop_y2

    def _on_press(self, event):
        if not self._crop_active:
            return
        edge = self._hit_edge(event.x, event.y)
        if edge:
            self._resize_edge = edge
            self._drag_data = (event.x, event.y)
        elif self._point_in_crop(event.x, event.y):
            self._drag_data = (event.x, event.y)
        else:
            # Click outside → start new square crop from click point
            self._crop_x1 = event.x
            self._crop_y1 = event.y
            self._crop_x2 = event.x
            self._crop_y2 = event.y
            self._resize_edge = "br"
            self._drag_data = (event.x, event.y)

    def _on_drag(self, event):
        if not self._crop_active or not self._drag_data:
            return
        if self._resize_edge:
            self._resize_crop(event.x, event.y)
        else:
            self._move_crop(event.x - self._drag_data[0], event.y - self._drag_data[1])
        self._drag_data = (event.x, event.y)
        self._draw_crop_overlay()

    def _on_release(self, event):
        self._drag_data = None
        self._resize_edge = None

    def _move_crop(self, dx, dy):
        w = self._crop_x2 - self._crop_x1
        h = self._crop_y2 - self._crop_y1
        nx1 = self._crop_x1 + dx
        ny1 = self._crop_y1 + dy
        nx1 = max(0, min(nx1, self._disp_w - w))
        ny1 = max(0, min(ny1, self._disp_h - h))
        self._crop_x1 = nx1
        self._crop_y1 = ny1
        self._crop_x2 = nx1 + w
        self._crop_y2 = ny1 + h

    def _resize_crop(self, mx, my):
        edge = self._resize_edge
        min_sz = 10
        x1, y1, x2, y2 = self._crop_x1, self._crop_y1, self._crop_x2, self._crop_y2
        dw, dh = self._disp_w, self._disp_h

        if edge == "br":
            sz = min(max(mx - x1, min_sz), max(my - y1, min_sz), dw - x1, dh - y1)
            x2 = x1 + sz
            y2 = y1 + sz
        elif edge == "tl":
            sz = min(max(x2 - mx, min_sz), max(y2 - my, min_sz), x2, y2)
            x1 = x2 - sz
            y1 = y2 - sz
        elif edge == "tr":
            sz = min(max(mx - x1, min_sz), max(y2 - my, min_sz), dw - x1, y2)
            x2 = x1 + sz
            y1 = y2 - sz
        elif edge == "bl":
            sz = min(max(x2 - mx, min_sz), max(my - y1, min_sz), x2, dh - y1)
            x1 = x2 - sz
            y2 = y1 + sz
        elif edge == "top":
            sz = min(max(y2 - my, min_sz), y2)
            cx = (x1 + x2) // 2
            half = sz // 2
            x1 = max(0, cx - half)
            x2 = x1 + sz
            y1 = y2 - sz
        elif edge == "bottom":
            sz = min(max(my - y1, min_sz), dh - y1)
            cx = (x1 + x2) // 2
            half = sz // 2
            x1 = max(0, cx - half)
            x2 = x1 + sz
            y2 = y1 + sz
        elif edge == "left":
            sz = min(max(x2 - mx, min_sz), x2)
            cy = (y1 + y2) // 2
            half = sz // 2
            y1 = max(0, cy - half)
            y2 = y1 + sz
            x1 = x2 - sz
        elif edge == "right":
            sz = min(max(mx - x1, min_sz), dw - x1)
            cy = (y1 + y2) // 2
            half = sz // 2
            y1 = max(0, cy - half)
            y2 = y1 + sz
            x2 = x1 + sz

        self._crop_x1, self._crop_y1, self._crop_x2, self._crop_y2 = x1, y1, x2, y2

    # ── Output ────────────────────────────────────────────

    def _choose_output(self):
        d = filedialog.askdirectory(title="Select Output Folder")
        if d:
            self.output_var.set(d)

    def _get_selected_sizes(self):
        return [s for s, v in self.size_vars.items() if v.get()]

    def _get_selected_formats(self):
        return [FORMATS[n] for n, v in self.fmt_vars.items() if v.get()]

    def _apply_circular_mask(self, img):
        """Keep an inscribed, anti-aliased circle; make everything outside transparent."""
        size = img.size[0]
        ss = 4  # supersample factor so the circle edge stays smooth at small sizes
        mask = Image.new("L", (size * ss, size * ss), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size * ss - 1, size * ss - 1), fill=255)
        img.putalpha(mask.resize((size, size), _LANCZOS))

    def _generate(self):
        if self.original_img is None:
            messagebox.showwarning("Warning", "Please load an image first.")
            return
        sizes = self._get_selected_sizes()
        formats = self._get_selected_formats()
        if not sizes:
            messagebox.showwarning("Warning", "Please select at least one size.")
            return
        if not formats:
            messagebox.showwarning("Warning", "Please select at least one format.")
            return
        out_dir = self.output_var.get()
        if not out_dir or not os.path.isdir(out_dir):
            messagebox.showwarning("Warning", "Please select a valid output folder.")
            return

        img = self.original_img.copy()
        if self._crop_active:
            box = self._get_crop_box_original()
            if box[2] > box[0] and box[3] > box[1]:
                img = img.crop(box)
        elif self._crop_is_circle():
            # No crop box: take the centered square so the circle isn't distorted
            w, h = img.size
            side = min(w, h)
            left, top = (w - side) // 2, (h - side) // 2
            img = img.crop((left, top, left + side, top + side))

        circular = self._crop_is_circle()
        count = 0
        errors = []
        base_name = os.path.splitext(os.path.basename(self.file_var.get()))[0]

        for fmt in formats:
            for size in sizes:
                resized = img.resize((size, size), _LANCZOS)
                if circular:
                    self._apply_circular_mask(resized)
                fname = f"{base_name}_{size}x{size}.{fmt}"
                fpath = os.path.join(out_dir, fname)
                try:
                    if fmt == "ico":
                        if circular:
                            # Keep the alpha channel so the area outside the circle stays transparent
                            resized.save(fpath, format="ICO", sizes=[(size, size)])
                        else:
                            resized.convert("RGB").save(fpath, format="ICO", sizes=[(size, size)])
                    elif fmt == "jpg":
                        bg = Image.new("RGB", resized.size, (255, 255, 255))
                        bg.paste(resized, mask=resized.split()[3] if resized.mode == "RGBA" else None)
                        bg.save(fpath, format="JPEG", quality=self.quality_var.get())
                    else:
                        resized.save(fpath, format="PNG")
                    count += 1
                except Exception as e:
                    errors.append(f"{fname}: {e}")

        if errors:
            messagebox.showerror("Errors", f"Generated {count} icons.\n\nErrors:\n" + "\n".join(errors))
        else:
            self.status_var.set(f"Generated {count} icons in {out_dir}")
            messagebox.showinfo("Done", f"Successfully generated {count} icons.")


def main():
    root = tk.Tk()
    IconGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
