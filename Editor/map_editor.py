import tkinter as tk
from tkinter import messagebox
import numpy as np, re, random, os, sys
from PIL import Image, ImageTk

# --- CONFIG ---
biome_colors = {
    0: (245, 196, 110), 1: (204, 174, 77), 2: (66, 135, 40),
    3: (184, 179, 82), 4: (119, 155, 70), 5: (70, 128, 70),
    6: (59, 108, 79), 7: (70, 128, 70), 8: (131, 160, 131),
    9: (245, 245, 255), 10: (15, 55, 100), 11: (39, 75, 116)
}
biome_names = {
    0:"Desert",1:"Savanna",2:"Jungle",3:"Grassland",4:"Woodland",5:"???", 
    6:"Swamp",7:"Taiga",8:"Hills",9:"Mountains",10:"Deep Water", 
    11:"Shallow Water"
}
column_height = 224
scale_default = 4

# --- WORLD PATHS ---
GRIM_REALMS_ROOT = os.path.dirname(os.path.abspath(__file__))
WORLDS_FOLDER = os.path.join(GRIM_REALMS_ROOT, "Worlds")

def list_worlds():
    return [f for f in os.listdir(WORLDS_FOLDER) if os.path.isdir(os.path.join(WORLDS_FOLDER,f))]

def get_world_path(world_name):
    return os.path.join(WORLDS_FOLDER, world_name)

# --- Paginated world selection ---
def select_world_popup(worlds):
    selected = {"name": None}
    current_page = {"index": 0}
    per_page = 6

    def show_page():
        for widget in popup.winfo_children():
            widget.destroy()
        start = current_page["index"] * per_page
        end = min(start + per_page, len(worlds))
        page_worlds = worlds[start:end]

        tk.Label(popup, text="Click a world to load:", font=("Arial", 12)).grid(row=0, column=0, columnspan=2, pady=10)

        for i, w in enumerate(page_worlds):
            row = i // 2 + 1
            col = i % 2
            btn = tk.Button(popup, text=w, width=20, command=lambda w=w: choose(w))
            btn.grid(row=row, column=col, padx=5, pady=5)

        nav_frame = tk.Frame(popup)
        nav_frame.grid(row=4, column=0, columnspan=2, pady=10)
        if current_page["index"] > 0:
            tk.Button(nav_frame, text="Back", command=lambda: change_page(-1)).pack(side="left", padx=5)
        if end < len(worlds):
            tk.Button(nav_frame, text="Next", command=lambda: change_page(1)).pack(side="right", padx=5)

    def change_page(delta):
        current_page["index"] += delta
        show_page()

    def choose(world_name):
        selected["name"] = world_name
        popup.destroy()

    popup = tk.Tk()
    popup.title("Select World")
    show_page()
    popup.mainloop()
    return selected["name"]

# --- Select world at startup ---
cli_world = None
if "--world" in sys.argv:
    idx = sys.argv.index("--world")
    if idx+1 < len(sys.argv):
        cli_world = sys.argv[idx+1]

if cli_world and cli_world in list_worlds():
    selected_world = cli_world
else:
    worlds = list_worlds()
    if not worlds:
        messagebox.showerror("No Worlds Found","No Worlds found in Worlds Folder")
        exit()
    selected_world = select_world_popup(worlds)
    if not selected_world:
        messagebox.showinfo("No Selection", "No world selected. Exiting.")
        exit()

WORLD_PATH = get_world_path(selected_world)

# --- File paths ---
biome_grid_path = os.path.join(WORLD_PATH, "biomeGrid.save")
region_grid_path = os.path.join(WORLD_PATH, "regionGrid.save")
greater_region_grid_path = os.path.join(WORLD_PATH, "greaterRegionGrid.save")
lore_path = os.path.join(WORLD_PATH, "Lore.save")

# --- HELPERS ---
def load_grid(path, height_override=None):
    if not os.path.exists(path):
        return np.zeros((height_override, 256), dtype=object) if height_override else np.zeros((256,256), dtype=object)
    with open(path,"r",encoding="utf-8",errors="ignore") as f:
        text = f.read().strip()
    if text.startswith("[") and text.endswith("]"):
        text=text[1:-1]
    numbers = re.findall(r'\[(\d+\.?\d*),(\d+\.?\d*)\]|(\-?\d+\.?\d*)', text)
    tiles=[]
    for a,b,c in numbers:
        if a: tiles.append( (int(float(a)), int(float(b))) )
        else: tiles.append( int(float(c)) )
    if height_override: height = height_override
    else: height = int(np.ceil(len(tiles)/256))
    width = len(tiles)//height
    arr = np.empty((height,width),dtype=object)
    for i, t in enumerate(tiles):
        y = i % height
        x = i // height
        if x < width: arr[y,x] = t
    return arr

def load_lore_titles(path):
    if not os.path.exists(path):
        return {"regions": [], "greaterRegions": []}
    with open(path,"r",encoding="utf-8",errors="ignore") as f: text=f.read()
    def extract(section):
        match = re.search(rf'"{section}"\s*:\s*\{{.*?"title"\s*:\s*\[(.*?)\]', text,re.DOTALL)
        return re.findall(r'"(.*?)"', match.group(1)) if match else []
    return {"regions": extract("regions"),"greaterRegions": extract("greaterRegions")}

def render_biome(grid):
    h,w = grid.shape
    img = Image.new("RGB",(w,h))
    pixels = img.load()
    for y in range(h):
        for x in range(w):
            cell = grid[y,x]
            if isinstance(cell,tuple): biome,mod=cell
            else: biome,mod=cell,None
            color = biome_colors.get(biome,(100,100,100))
            if mod==12:
                r,g,b=color
                color = (int(r*0.5+90*0.5),int(g*0.5+0*0.5),int(b*0.5+120*0.5))
            pixels[x,y]=color
    return img

def save_grid(grid, path):
    tiles = []
    height, width = grid.shape
    for i in range(height*width):
        y = i % height
        x = i // height
        cell = grid[y,x]
        if cell is None:
            tiles.append("-4.0")
        elif isinstance(cell, tuple):
            value, mod = cell
            if mod is None:
                tiles.append(str(value))
            else:
                tiles.append(f"[{value},{int(mod)}]")
        else:
            tiles.append(str(cell))
    with open(path,"w",encoding="utf-8") as f:
        f.write("[" + ",".join(tiles) + "]")

# --- EDITOR CLASS ---
class CombinedEditor(tk.Tk):
    def __init__(self, biome_grid, region_grid, greater_region_grid, region_names, greater_names):
        super().__init__()
        self.title(f"Grim Realms World Editor - {selected_world}")
        self.biome_grid = biome_grid
        self.region_grid = region_grid
        self.greater_region_grid = greater_region_grid
        self.region_names = region_names
        self.greater_names = greater_names
        self.scale = scale_default
        self.current_biome = None
        self.current_region = None
        self.current_biome_modifier = None
        self.current_greater_region = None
        self.brush_size = 1
        self.highlight_greater_region = None
        self.img_pos_x = 0
        self.img_pos_y = 0
        self.scroll_step = 50
        self.scroll_speed = 10
        self.pressed_keys = set()

        self.canvas = tk.Canvas(self, bg="#0F3764")
        self.canvas.pack(fill="both", expand=True)
        self.tk_img = None
        self.canvas_img = None

        # --- Keyboard scrolling ---
        for key in ["Up","Down","Left","Right","w","a","s","d","W","A","S","D"]:
            self.bind_all(f"<KeyPress-{key}>", lambda e, k=key: self.pressed_keys.add(k))
            self.bind_all(f"<KeyRelease-{key}>", lambda e, k=key: self.pressed_keys.discard(k))
        self.update_scroll()

        # --- Middle-click dragging ---
        self.middle_dragging = False
        self.last_drag_x = 0
        self.last_drag_y = 0
        self.canvas.bind("<Button-1>", self.paint)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.canvas.bind("<Button-2>", self.start_middle_drag)
        self.canvas.bind("<B2-Motion>", self.middle_drag)
        self.canvas.bind("<ButtonRelease-2>", self.end_middle_drag)

        # --- Tooltip ---
        self.tooltip = tk.Toplevel(self.canvas)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.tooltip_label = tk.Label(self.tooltip,text="",bg="white")
        self.tooltip_label.pack()
        self.canvas.bind("<Motion>", self.show_tooltip)
        self.canvas.bind("<Leave>", lambda e:self.tooltip.withdraw())

        self.update_image()
        self.create_menu()

    # --- Continuous scroll ---
    def update_scroll(self):
        dx = dy = 0
        for key in self.pressed_keys:
            if key in ["Left","a","A"]:
                dx += self.scroll_speed
            elif key in ["Right","d","D"]:
                dx -= self.scroll_speed
            elif key in ["Up","w","W"]:
                dy += self.scroll_speed
            elif key in ["Down","s","S"]:
                dy -= self.scroll_speed
        if dx != 0 or dy != 0:
            self.scroll_map(dx, dy)
        self.after(16, self.update_scroll)

    # --- Painting ---
    def _event_to_tile(self, event):
        ex = self.canvas.canvasx(event.x)
        ey = self.canvas.canvasy(event.y)
        tile_x = int((ex - self.img_pos_x) / self.scale)
        tile_y = int((ey - self.img_pos_y) / self.scale)
        return tile_x, tile_y

    def paint(self, event):
        x, y = self._event_to_tile(event)
        size = self.brush_size
        for dx in range(-size+1, size):
            for dy in range(-size+1, size):
                nx, ny = x+dx, y+dy
                if 0 <= nx < self.biome_grid.shape[1] and 0 <= ny < self.biome_grid.shape[0]:
                    if self.current_biome_modifier == "erase":
                        cell = self.biome_grid[ny, nx]
                        if isinstance(cell, tuple):
                            self.biome_grid[ny, nx] = cell[0]
                    elif self.current_biome_modifier is not None:
                        base = self.biome_grid[ny, nx]
                        base_val = base[0] if isinstance(base, tuple) else base
                        if self.current_biome is None:
                            self.biome_grid[ny, nx] = (base_val, self.current_biome_modifier)
                        else:
                            self.biome_grid[ny, nx] = (self.current_biome, self.current_biome_modifier)
                    else:
                        if self.current_biome is not None:
                            self.biome_grid[ny, nx] = self.current_biome
                    if self.current_region is not None:
                        self.region_grid[ny, nx] = self.current_region
                    if self.current_greater_region is not None:
                        self.greater_region_grid[ny, nx] = self.current_greater_region
        self.update_image()

    # --- Tooltip ---
    def show_tooltip(self, event):
        x, y = self._event_to_tile(event)
        text = ""
        if 0 <= x < self.biome_grid.shape[1] and 0 <= y < self.biome_grid.shape[0]:
            b, m = self.biome_grid[y, x] if isinstance(self.biome_grid[y, x], tuple) else (self.biome_grid[y, x], None)
            r_cell = self.region_grid[y, x]
            r = r_cell if not isinstance(r_cell, tuple) else r_cell[0]
            g = self.greater_region_grid[y, x]
            text = f"Region: {self.region_names[r]}({r})"
            text += f" | Greater Region: {self.greater_names[g]}({g})" if g != -4 else " | Greater Region: None"
            text += f" | Biome: {biome_names[b]}({b})"
            if m is not None and m == 12:
                text += f" | Biome Mod: Dreadlands"
        if text:
            self.tooltip_label.config(text=text)
            self.tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")
            self.tooltip.deiconify()
        else:
            self.tooltip.withdraw()

    # --- Zoom (mouse-centered) ---
    def zoom(self, event):
        if hasattr(event, "delta"):
            factor = 1.05 if event.delta > 0 else 0.95
        elif hasattr(event, "num"):
            factor = 1.05 if event.num == 4 else 0.95
        else:
            factor = 1.0

        mouse_x = self.canvas.canvasx(event.x)
        mouse_y = self.canvas.canvasy(event.y)

        world_x = (mouse_x - self.img_pos_x) / self.scale
        world_y = (mouse_y - self.img_pos_y) / self.scale

        self.scale *= factor

        self.img_pos_x = mouse_x - world_x * self.scale
        self.img_pos_y = mouse_y - world_y * self.scale

        self.update_image()

    # --- Update Image ---
    def update_image(self):
        img_b = render_biome(self.biome_grid)
        if self.highlight_greater_region is not None:
            h, w = self.greater_region_grid.shape
            overlay = Image.new("RGBA", (w, h), (0,0,0,0))
            pixels = overlay.load()
            for yy in range(h):
                for xx in range(w):
                    cell = self.greater_region_grid[yy, xx]
                    if cell == self.highlight_greater_region and cell != -4:
                        pixels[xx, yy] = (255,0,0,100)
            img_b = img_b.convert("RGBA")
            img_b = Image.alpha_composite(img_b, overlay)
            img_b = img_b.convert("RGB")
        w_px = int(self.biome_grid.shape[1] * self.scale)
        h_px = int(self.biome_grid.shape[0] * self.scale)
        img_b = img_b.resize((w_px, h_px), Image.Resampling.NEAREST)
        self.tk_img = ImageTk.PhotoImage(img_b)
        if self.canvas_img is None:
            self.canvas_img = self.canvas.create_image(self.img_pos_x, self.img_pos_y, anchor="nw", image=self.tk_img)
        else:
            self.canvas.itemconfig(self.canvas_img, image=self.tk_img)
            self.canvas.coords(self.canvas_img, self.img_pos_x, self.img_pos_y)
        self.canvas.config(scrollregion=(self.img_pos_x, self.img_pos_y, self.img_pos_x + w_px, self.img_pos_y + h_px))

    # --- Map movement ---
    def scroll_map(self, dx, dy):
        self.img_pos_x += dx
        self.img_pos_y += dy
        if self.canvas_img is not None:
            self.canvas.coords(self.canvas_img, self.img_pos_x, self.img_pos_y)

    # --- Middle-click drag ---
    def start_middle_drag(self, event):
        self.middle_dragging = True
        self.last_drag_x = event.x
        self.last_drag_y = event.y

    def middle_drag(self, event):
        if self.middle_dragging:
            dx = event.x - self.last_drag_x
            dy = event.y - self.last_drag_y
            self.scroll_map(dx, dy)
            self.last_drag_x = event.x
            self.last_drag_y = event.y

    def end_middle_drag(self, event):
        self.middle_dragging = False

    # --- Setters ---
    def set_biome(self, b): self.current_biome = b
    def set_region(self, r): self.current_region = r
    def set_biome_modifier(self, m): self.current_biome_modifier = m
    def set_greater_region(self, g): self.current_greater_region = g
    def set_highlight_greater(self, g): self.highlight_greater_region = g; self.update_image()

    # --- Save ---
    def save_all(self):
        save_grid(self.biome_grid, biome_grid_path)
        save_grid(self.region_grid, region_grid_path)
        save_grid(self.greater_region_grid, greater_region_grid_path)
        messagebox.showinfo("Saved", "All grids have been saved!")

    # --- Switch World ---
    def switch_world(self):
        self.destroy()
        os.execl(sys.executable, sys.executable, *sys.argv)

    # --- Menu ---
    def create_menu(self):
        menubar = tk.Menu(self)

        # Tools
        tools_menu = tk.Menu(menubar, tearoff=0)
        brush_menu = tk.Menu(tools_menu, tearoff=0)
        for s in range(1,6):
            brush_menu.add_command(label=str(s), command=lambda s=s: setattr(self,"brush_size",s))
        tools_menu.add_cascade(label="Brush Size", menu=brush_menu)

        highlight_menu = tk.Menu(tools_menu, tearoff=0)
        for i,name in enumerate(self.greater_names):
            highlight_menu.add_command(label=name, command=lambda g=i: self.set_highlight_greater(g))
        highlight_menu.add_command(label="Clear Highlight", command=lambda: self.set_highlight_greater(None))
        tools_menu.add_cascade(label="Highlight Greater Region", menu=highlight_menu)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        # Regions
        regions_menu = tk.Menu(menubar, tearoff=0)
        regions_menu.add_command(label="No Selection", command=lambda:self.set_region(None))
        for i,name in enumerate(self.region_names):
            regions_menu.add_command(label=name, command=lambda r=i:self.set_region(r))
        menubar.add_cascade(label="Regions", menu=regions_menu)

        # Greater Regions
        greater_menu = tk.Menu(menubar, tearoff=0)
        greater_menu.add_command(label="No Selection", command=lambda:self.set_greater_region(None))
        for i,name in enumerate(self.greater_names):
            greater_menu.add_command(label=name, command=lambda g=i:self.set_greater_region(g))
        greater_menu.add_command(label="Clear Greater Region", command=lambda:self.set_greater_region(-4))
        menubar.add_cascade(label="Greater Regions", menu=greater_menu)

        # Biomes
        biomes_menu = tk.Menu(menubar, tearoff=0)
        biomes_menu.add_command(label="No Selection", command=lambda:self.set_biome(None))
        for b,name in biome_names.items():
            biomes_menu.add_command(label=name, command=lambda b=b:self.set_biome(b))
        menubar.add_cascade(label="Biomes", menu=biomes_menu)

        # Biome Modifiers
        biome_mod_menu = tk.Menu(menubar, tearoff=0)
        biome_mod_menu.add_command(label="No Selection", command=lambda:self.set_biome_modifier(None))
        biome_mod_menu.add_command(label="Dreadlands", command=lambda:self.set_biome_modifier(12))
        biome_mod_menu.add_separator()
        biome_mod_menu.add_command(label="Erase Modifier", command=lambda:self.set_biome_modifier("erase"))
        menubar.add_cascade(label="Biome Modifiers", menu=biome_mod_menu)

        # File
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save", command=self.save_all)
        file_menu.add_command(label="Switch World", command=self.switch_world)
        menubar.add_cascade(label="File", menu=file_menu)

        self.config(menu=menubar)

# --- RUN ---
biome_grid = load_grid(biome_grid_path)
region_grid = load_grid(region_grid_path, column_height)
greater_region_grid = load_grid(greater_region_grid_path, column_height)
lore_data = load_lore_titles(lore_path)
region_names = lore_data["regions"]
greater_names = lore_data["greaterRegions"]

app = CombinedEditor(biome_grid, region_grid, greater_region_grid, region_names, greater_names)
app.mainloop()
