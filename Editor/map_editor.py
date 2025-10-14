import tkinter as tk
from tkinter import messagebox
import numpy as np, re, random, os
from PIL import Image, ImageTk

# --- CONFIG ---
biome_colors = {
    0: (245, 196, 110), 1: (204, 174, 77), 2: (66, 135, 40),
    3: (184, 179, 82), 4: (119, 155, 70), 5: (70, 128, 70),
    6: (59, 108, 79), 7: (70, 128, 70), 8: (131, 160, 131),
    9: (245, 245, 255), 10: (15, 55, 100), 11: (39, 75, 116)
}
biome_names = {
    0:"Desert",1:"Savanna",2:"Jungle",3:"Grassland",4:"Woodland",5:"Lush Forest",
    6:"Swamp",7:"Boreal Forest",8:"Hills",9:"Mountains",10:"Deep Water",
    11:"Shallow Water"
}

region_grid_path = "regionGrid.save"
biome_grid_path = "biomeGrid.save"
greater_region_grid_path = "greaterRegionGrid.save"
lore_path = "Lore.save"
column_height = 224
scale_default = 4

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

def generate_colors(num):
    return {i:(random.randint(50,255),random.randint(50,255),random.randint(50,255)) for i in range(max(1,num))}

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

# --- EDITOR ---
class CombinedEditor(tk.Tk):
    def __init__(self, biome_grid, region_grid, greater_region_grid, region_names, greater_names):
        super().__init__()
        self.title("Grim Realms World Editor")  # updated app name

        self.biome_grid = biome_grid
        self.region_grid = region_grid
        self.greater_region_grid = greater_region_grid
        self.region_names = region_names
        self.greater_names = greater_names

        self.scale = scale_default

        # --- Startup selections: No Selection by default ---
        self.current_biome = None
        self.current_region = None
        self.current_biome_modifier = None
        self.current_greater_region = None

        self.brush_size = 1
        self.highlight_greater_region = None

        self.img_pos_x = 0
        self.img_pos_y = 0

        self.canvas = tk.Canvas(self,bg="black")
        self.canvas.pack(fill="both",expand=True)
        self.tk_img = None
        self.canvas_img = None

        self.scroll_step = 50

        self.update_image()

        # Bindings (reversed)
        self.canvas.bind("<Button-1>", self.paint)
        self.canvas.bind("<B1-Motion>", self.paint)
        self.canvas.bind("<MouseWheel>", self.zoom)
        self.bind_all("<Up>", lambda e: self.scroll_map(0, self.scroll_step))
        self.bind_all("<Down>", lambda e: self.scroll_map(0, -self.scroll_step))
        self.bind_all("<Left>", lambda e: self.scroll_map(self.scroll_step, 0))
        self.bind_all("<Right>", lambda e: self.scroll_map(-self.scroll_step, 0))

        self.tooltip = tk.Toplevel(self.canvas)
        self.tooltip.withdraw()
        self.tooltip.overrideredirect(True)
        self.tooltip_label = tk.Label(self.tooltip,text="",bg="white")
        self.tooltip_label.pack()
        self.canvas.bind("<Motion>", self.show_tooltip)
        self.canvas.bind("<Leave>", lambda e:self.tooltip.withdraw())

        self.create_menu()

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
        menubar.add_cascade(label="File", menu=file_menu)

        self.config(menu=menubar)

    # --- Map movement ---
    def scroll_map(self, dx, dy):
        self.img_pos_x += dx
        self.img_pos_y += dy
        if self.canvas_img is not None:
            self.canvas.coords(self.canvas_img, self.img_pos_x, self.img_pos_y)

    # --- Setters ---
    def set_biome(self,b): self.current_biome=b
    def set_region(self,r): self.current_region=r
    def set_biome_modifier(self,m): self.current_biome_modifier=m
    def set_greater_region(self,g): self.current_greater_region=g
    def set_highlight_greater(self,g): self.highlight_greater_region=g; self.update_image()

    # --- Convert mouse event to tile coords ---
    def _event_to_tile(self, event):
        ex = self.canvas.canvasx(event.x)
        ey = self.canvas.canvasy(event.y)
        tile_x = int((ex - self.img_pos_x) / self.scale)
        tile_y = int((ey - self.img_pos_y) / self.scale)
        return tile_x, tile_y

    # --- Painting ---
    def paint(self,event):
        x, y = self._event_to_tile(event)
        size = self.brush_size
        for dx in range(-size+1,size):
            for dy in range(-size+1,size):
                nx,ny = x+dx, y+dy
                if 0<=nx<self.biome_grid.shape[1] and 0<=ny<self.biome_grid.shape[0]:
                    # Biome Modifier logic
                    if self.current_biome_modifier == "erase":
                        cell = self.biome_grid[ny,nx]
                        if isinstance(cell, tuple):
                            self.biome_grid[ny,nx] = cell[0]
                    elif self.current_biome_modifier is not None:
                        base = self.biome_grid[ny,nx]
                        base_val = base[0] if isinstance(base, tuple) else base
                        if self.current_biome is None:
                            self.biome_grid[ny,nx] = (base_val, self.current_biome_modifier)
                        else:
                            self.biome_grid[ny,nx] = (self.current_biome, self.current_biome_modifier)
                    else:
                        if self.current_biome is not None:
                            self.biome_grid[ny,nx] = self.current_biome

                    # Regions
                    if self.current_region is not None:
                        self.region_grid[ny,nx] = self.current_region

                    # Greater Regions
                    if self.current_greater_region is not None:
                        self.greater_region_grid[ny,nx] = self.current_greater_region
        self.update_image()

    # --- Tooltip ---
    def show_tooltip(self,event):
        x, y = self._event_to_tile(event)
        text = ""
        if 0<=x<self.biome_grid.shape[1] and 0<=y<self.biome_grid.shape[0]:
            b,m = self.biome_grid[y,x] if isinstance(self.biome_grid[y,x],tuple) else (self.biome_grid[y,x],None)
            r_cell = self.region_grid[y,x]
            if isinstance(r_cell, tuple):
                r, r_mod = r_cell
            else:
                r, r_mod = r_cell, None
            g = self.greater_region_grid[y,x]
            text = f"Region: {self.region_names[r]}({r})"
            if r_mod is not None:
                text += f" | Region Mod: {r_mod}"
            text += f" | Greater Region: {self.greater_names[g]}({g})" if g!=-4 else " | Greater Region: None"
            text += f" | Biome: {biome_names[b]}({b})"
            if m is not None and m==12:
                text += f" | Biome Mod: Dreadlands"
        if text:
            self.tooltip_label.config(text=text)
            self.tooltip.geometry(f"+{event.x_root+10}+{event.y_root+10}")
            self.tooltip.deiconify()
        else:
            self.tooltip.withdraw()

    # --- Zoom & Image update ---
    def zoom(self,event):
        factor = 1.1 if getattr(event,'delta',1)>0 else 0.9
        self.scale *= factor
        self.update_image()

    def update_image(self):
        img_b = render_biome(self.biome_grid)
        if self.highlight_greater_region is not None:
            h, w = self.greater_region_grid.shape
            overlay = Image.new("RGBA",(w,h),(0,0,0,0))
            pixels = overlay.load()
            for yy in range(h):
                for xx in range(w):
                    cell = self.greater_region_grid[yy,xx]
                    if cell == self.highlight_greater_region and cell != -4:
                        pixels[xx,yy] = (255,0,0,100)
            img_b = img_b.convert("RGBA")
            img_b = Image.alpha_composite(img_b, overlay)
            img_b = img_b.convert("RGB")
        w_px = int(self.biome_grid.shape[1]*self.scale)
        h_px = int(self.biome_grid.shape[0]*self.scale)
        img_b = img_b.resize((w_px, h_px), Image.Resampling.NEAREST)
        self.tk_img = ImageTk.PhotoImage(img_b)
        if self.canvas_img is None:
            self.canvas_img = self.canvas.create_image(self.img_pos_x, self.img_pos_y, anchor="nw", image=self.tk_img)
        else:
            self.canvas.itemconfig(self.canvas_img, image=self.tk_img)
            self.canvas.coords(self.canvas_img, self.img_pos_x, self.img_pos_y)
        self.canvas.config(scrollregion=(self.img_pos_x, self.img_pos_y, self.img_pos_x + w_px, self.img_pos_y + h_px))

    # --- Save ---
    def save_all(self):
        save_grid(self.biome_grid, biome_grid_path)
        save_grid(self.region_grid, region_grid_path)
        save_grid(self.greater_region_grid, greater_region_grid_path)
        messagebox.showinfo("Saved","All three grids have been saved!")

# --- RUN ---
biome_grid = load_grid(biome_grid_path)
region_grid = load_grid(region_grid_path,column_height)
greater_region_grid = load_grid(greater_region_grid_path,column_height)
lore_data = load_lore_titles(lore_path)
region_names = lore_data["regions"]
greater_names = lore_data["greaterRegions"]

app = CombinedEditor(biome_grid, region_grid, greater_region_grid, region_names, greater_names)
app.mainloop()
