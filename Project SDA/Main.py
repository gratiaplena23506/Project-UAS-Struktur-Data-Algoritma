import heapq
import tkinter as tk
from tkinter import messagebox
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import networkx as nx
import numpy as np

# Membaca Data dari file
FILE_SPBU = "Data SPBU.xlsx"
FILE_LAMPU_MERAH = "Lampu Merah.xlsx"

graph_waktu = {}
graph_jarak = {}
info_jalan = {}                 
status_jalur_dua_arah = set()   
edges_terdaftar = set() 

try:
    # Membaca Hambatan Lampu Merah
    banyak_lampu_merah = {}
    try:
        df_lampu = pd.read_excel(FILE_LAMPU_MERAH, engine='openpyxl')
        df_lampu.columns = df_lampu.columns.str.strip()
        
        df_lampu = df_lampu.rename(columns={
            'Sisi Asal (i)': 'asal', 'Sisi Tujuan (j)': 'tujuan', 'Waktu (Menit)': 'bobot_lampu'
        })
        
        for _, row in df_lampu.iterrows():
            try:
                if pd.isna(row['asal']) or pd.isna(row['tujuan']): continue
                i_node = int(float(row['asal']))
                j_node = int(float(row['tujuan']))
                waktu_lampu = float(row['bobot_lampu'])
                banyak_lampu_merah[(i_node, j_node)] = waktu_lampu
            except:
                continue
    except Exception as e:
        print(f"Catatan: Hambatan lampu merah dilewati karena: {e}")

    simpul_lampu_merah = set()
    for _, row in df_lampu.iterrows():
        if pd.notna(row.get('Simpul Lampu Merah')):
            simpul_lampu_merah.add(int(float(row['Simpul Lampu Merah'])))
        # Membaca Jarak & Durasi Utama SPBU
        df_spbu = pd.read_excel(FILE_SPBU, engine='openpyxl')
        df_spbu.columns = df_spbu.columns.str.strip()
        
    df_spbu = df_spbu.rename(columns={
        'Simpul Asal (i)': 'source', 'Simpul Tujuan (j)': 'target',
        'Bobot Jarak (meter)': 'jarak', 'Durasi Perjalanan (menit)': 'waktu',
        'Nama Jalan Sesuai Gambar': 'jalan', 'Jalur': 'jalur'
    })

    for index, row in df_spbu.iterrows():
        try:
            if pd.isna(row['source']) or pd.isna(row['target']): continue
            u = int(float(row['source']))
            v = int(float(row['target']))
            jarak = float(row['jarak'])
            waktu_dasar = float(row['waktu'])
            
            nama_jalan = str(row['jalan']).strip() if 'jalan' in df_spbu.columns else ""
            if nama_jalan.lower() in ["nan", "none", "null"]: nama_jalan = ""
                
            tipe_jalur = str(row['jalur']).strip() if 'jalur' in df_spbu.columns else ""
            
            hambatan_uv = banyak_lampu_merah.get((u, v), 0.0)
            waktu_total_uv = waktu_dasar + hambatan_uv
            
            if u not in graph_waktu: graph_waktu[u] = {}
            if u not in graph_jarak: graph_jarak[u] = {}
            
            graph_waktu[u][v] = waktu_total_uv
            graph_jarak[u][v] = jarak
            edges_terdaftar.add((u, v))
            
            if "tidak" not in tipe_jalur.lower() and "bolak" in tipe_jalur.lower():
                status_jalur_dua_arah.add((u, v))
                status_jalur_dua_arah.add((v, u))
                
                if v not in graph_waktu: graph_waktu[v] = {}
                if v not in graph_jarak: graph_jarak[v] = {}
                
                hambatan_vu = banyak_lampu_merah.get((v, u), 0.0)
                waktu_total_vu = waktu_dasar + hambatan_vu
                
                graph_waktu[v][u] = waktu_total_vu
                graph_jarak[v][u] = jarak
                edges_terdaftar.add((v, u))
            
            key_tunggal = (min(u, v), max(u, v))
            if key_tunggal not in info_jalan:
                info_jalan[key_tunggal] = {"nama": nama_jalan, "jarak": jarak}
                
            if v not in graph_waktu: graph_waktu[v] = {}
            if v not in graph_jarak: graph_jarak[v] = {}
            
        except Exception as e:
            continue

except Exception as e:
    messagebox.showerror("File Error", f"Gagal total membaca file Excel (.xlsx): {e}")


# Logika Algoritma Djikstra 

def dijkstra(graph, start, target):
    all_nodes = set(graph.keys())
    for node_edges in graph.values():
        all_nodes.update(node_edges.keys())
        
    distances = {node: float('inf') for node in all_nodes}
    distances[start] = 0
    previous_nodes = {node: None for node in all_nodes}
    priority_queue = [(0, start)]

    while priority_queue:
        current_dist, current_node = heapq.heappop(priority_queue)

        if current_dist > distances[current_node]: continue
        if current_node == target: break

        for neighbor, weight in graph.get(current_node, {}).items():
            distance = current_dist + weight
            if distance < distances[neighbor]:
                distances[neighbor] = distance
                previous_nodes[neighbor] = current_node
                heapq.heappush(priority_queue, (distance, neighbor))

    if distances[target] == float('inf'): return float('inf'), []

    path = []
    current = target
    while current is not None:
        path.append(current)
        current = previous_nodes[current]
    path.reverse()
    return distances[target], path

def hitung_total_dari_jalur(path, graph_sumber):
    if not path or len(path) < 2: return 0.0
    total = 0.0
    for i in range(len(path) - 1):
        total += graph_sumber.get(path[i], {}).get(path[i+1], 0.0)
    return total


# GUI Interface

class AppVisualisasiDijkstra:
    def __init__(self, window):
        self.window = window
        self.window.title("Sistem Komparasi Jalur SPBU & Hambatan Lampu Merah")
        self.window.geometry("1400x850")
        self.window.state('zoomed')
        self.window.configure(bg="#1e272e")
        
        panel_atas = tk.Frame(self.window, bg="#2f3640", height=60)
        panel_atas.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        tk.Label(panel_atas, text="Simpul Awal (i):", fg="white", bg="#2f3640", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10, pady=15)
        self.input_awal = tk.Entry(panel_atas, width=6, font=("Arial", 11), justify="center")
        self.input_awal.insert(0, "1")
        self.input_awal.pack(side=tk.LEFT, padx=5)
        
        tk.Label(panel_atas, text="Simpul Tujuan (j):", fg="white", bg="#2f3640", font=("Arial", 11, "bold")).pack(side=tk.LEFT, padx=10)
        self.input_tujuan = tk.Entry(panel_atas, width=6, font=("Arial", 11), justify="center")
        self.input_tujuan.insert(0, "44")
        self.input_tujuan.pack(side=tk.LEFT, padx=5)
        
        btn_hitung = tk.Button(panel_atas, text="Kalkulasi Rute", command=self.proses_dan_gambar, bg="#4cd137", fg="white", font=("Arial", 11, "bold"), padx=10)
        btn_hitung.pack(side=tk.LEFT, padx=20)
        
        self.panel_info = tk.Frame(self.window, bg="#1e272e")
        self.panel_info.pack(side=tk.TOP, fill=tk.X, padx=15, pady=5)
        
        self.lbl_tercepat = tk.Label(self.panel_info, text="", fg="#4cd137", bg="#1e272e", font=("Consolas", 11, "bold"), anchor="w", justify=tk.LEFT)
        self.lbl_tercepat.pack(fill=tk.X, pady=2)
        
        self.lbl_terpendek = tk.Label(self.panel_info, text="", fg="#ff9f43", bg="#1e272e", font=("Consolas", 11, "bold"), anchor="w", justify=tk.LEFT)
        self.lbl_terpendek.pack(fill=tk.X, pady=2)
        
        self.frame_grafik = tk.Frame(self.window, bg="#1e272e")
        self.frame_grafik.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.G = nx.DiGraph()
        for u, edges in graph_waktu.items():
            for v in edges.keys():
                self.G.add_edge(u, v)
                
        # Koordinat
        self.posisi_nodes = {
            1:  (11.0, 1.0), 2:  (9.5,  1.0), 3:  (6.0,  1.0),
            4:  (9.5,  2.5), 5:  (6.0,  2.5),
            6:  (9.5,  3.8), 7:  (8.5,  3.2), 8:  (6.0,  3.5), 9:  (5.0,  3.8),
            10: (8.5,  4.2),
            11: (6.0,  4.5), 12: (5.0,  4.5), 13: (2.0,  4.5),
            14: (9.5,  5.5), 15: (8.5,  5.5), 16: (7.5,  5.5), 17: (6.0,  5.5), 18: (5.0,  5.5), 19: (4.0,  5.5), 20: (3.0,  5.5), 21: (2.0,  5.5),
            22: (7.5,  6.5), 23: (6.0,  6.5),
            24: (8.5,  7.5), 25: (7.5,  7.5), 26: (6.0,  7.5),
            27: (9.5,  7.8),
            28: (6.0,  8.5), 29: (5.0,  8.5), 30: (4.0,  8.5), 31: (3.0,  8.5), 32: (2.0,  8.5),
            33: (9.5,  9.5), 34: (8.5,  9.5), 35: (6.0,  9.5), 36: (5.0,  9.5), 37: (4.0,  9.5), 38: (2.0,  9.5),
            39: (9.5,  10.8), 40: (5.5,  10.5), 41: (3.0,  10.5),
            42: (9.5,  11.8), 43: (4.0,  11.8), 44: (2.0,  11.8)
        }

        self.proses_dan_gambar()

    def draw_rute_lurus_dan_label(self, ax, edges, color, width, arrowsize, gambar_label=False):
        label_tergambar = set()
        for u, v in edges:
            if u not in self.posisi_nodes or v not in self.posisi_nodes: continue
            x1, y1 = self.posisi_nodes[u]
            x2, y2 = self.posisi_nodes[v]
            
            dx, dy = x2 - x1, y2 - y1
            dist = np.hypot(dx, dy)
            if dist == 0: continue
            dx, dy = dx / dist, dy / dist
            
            if (u, v) in status_jalur_dua_arah:
                offset_dist = 0.14
                offset_x, offset_y = -dy * offset_dist, dx * offset_dist
            else:
                offset_x, offset_y = 0, 0
                
            gap = 0.28  
            x1_f, y1_f = x1 + offset_x + dx * gap, y1 + offset_y + dy * gap
            x2_f, y2_f = x2 + offset_x - dx * gap, y2 + offset_y - dy * gap
            
            ax.annotate("", xy=(x2_f, y2_f), xytext=(x1_f, y1_f),
                        arrowprops=dict(arrowstyle="->", color=color, lw=width,
                                        mutation_scale=arrowsize, shrinkA=0, shrinkB=0))
            
            if gambar_label:
                key_tunggal = (min(u, v), max(u, v))
                if key_tunggal in info_jalan and key_tunggal not in label_tergambar:
                    nama = info_jalan[key_tunggal]["nama"]
                    jarak = info_jalan[key_tunggal]["jarak"]
                    label_text = f"{nama}\n({jarak:,.0f}m)" if nama else f"({jarak:,.0f}m)"
                    
                    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
                    angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
                    
                    sudut_norm = angle
                    if sudut_norm > 90: sudut_norm -= 180
                    elif sudut_norm < -90: sudut_norm += 180
                    
                    # Logika penentuan posisi dan rotasi
                    if abs(sudut_norm) < 10: 
                        offset_x = 0
                        offset_y = 0.35
                        rotasi_final = 0 
                    elif abs(sudut_norm) > 80:
                        offset_x = 0.35
                        offset_y = 0
                        rotasi_final = 90 
                    else:
                        # Jalur miring
                        offset_x = -0.15 * np.sign(np.sin(np.radians(angle)))
                        offset_y = 0.15 * np.sign(np.cos(np.radians(angle)))
                        rotasi_final = sudut_norm + 5

                    t = ax.text(cx + offset_x, cy + offset_y, label_text, 
                                color="#f1f2f6", 
                                fontsize=5, 
                                ha="center", 
                                va="center", 
                                rotation=rotasi_final,
                                fontweight="bold",
                                clip_on=True)
                    
                    t.set_path_effects([PathEffects.withStroke(linewidth=3, foreground='#1e272e')])
                    
                    label_tergambar.add(key_tunggal)

    def proses_dan_gambar(self):
        if len(self.G.nodes()) == 0:
            messagebox.showerror("Error Graf", "Graf kosong! Periksa lokasi file Excel.")
            return
        try:
            awal = int(self.input_awal.get())
            tujuan = int(self.input_tujuan.get())
        except ValueError:
            messagebox.showerror("Gagal", "Simpul input harus angka!")
            return

        if awal not in self.G or tujuan not in self.G:
            messagebox.showerror("Gagal", f"Simpul tidak ada! Rentang: {min(self.G.nodes())} s/d {max(self.G.nodes())}")
            return
            
        waktu_tercepat, rute_tercepat = dijkstra(graph_waktu, awal, tujuan)
        jarak_rute_tercepat = hitung_total_dari_jalur(rute_tercepat, graph_jarak)
        
        jarak_terpendek, rute_terpendek = dijkstra(graph_jarak, awal, tujuan)
        waktu_rute_terpendek = hitung_total_dari_jalur(rute_terpendek, graph_waktu)
        
        rute_edges_tercepat = [(rute_tercepat[i], rute_tercepat[i+1]) for i in range(len(rute_tercepat)-1)]
        rute_edges_terpendek = [(rute_terpendek[i], rute_terpendek[i+1]) for i in range(len(rute_terpendek)-1)]

        if waktu_tercepat == float('inf'):
            self.lbl_tercepat.config(text="STATUS: Jalur terputus.")
            self.lbl_terpendek.config(text="")
        else:
            self.lbl_tercepat.config(text=f"🟢 LINTASAN TERCEPAT: {' -> '.join(map(str, rute_tercepat))} \n   ➔ TOTAL WAKTU: {waktu_tercepat:.2f} Menit | Jarak: {jarak_rute_tercepat:,.0f} Meter")
            self.lbl_terpendek.config(text=f"🟠 LINTASAN TERPENDEK: {' -> '.join(map(str, rute_terpendek))} \n   ➔ TOTAL JARAK : {jarak_terpendek:,.0f} Meter | Waktu: {waktu_rute_terpendek:.2f} Menit")

        for widget in self.frame_grafik.winfo_children(): widget.destroy()

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
        fig.patch.set_facecolor('#1e272e')
        
        ax1.set_facecolor('#1e272e')
        ax1.set_title("1. Jalur Distribusi Tercepat (Waktu + Lampu Merah)", color="white", fontsize=11, fontweight="bold")
        node_colors_1 = [
            "#ff4d4d" if nd in (awal, tujuan) else 
            ("#f1c40f" if nd in simpul_lampu_merah else ("#00ff7f" if nd in rute_tercepat else "#2f3542")) 
            for nd in self.G.nodes()]
        nx.draw_networkx_nodes(self.G, self.posisi_nodes, node_color=node_colors_1, node_size=350, ax=ax1)
        nx.draw_networkx_labels(self.G, self.posisi_nodes, font_size=8, font_color="white", font_weight="bold", ax=ax1)
        self.draw_rute_lurus_dan_label(ax1, [ed for ed in self.G.edges() if ed not in rute_edges_tercepat], "#485460", 3, 10, True)
        self.draw_rute_lurus_dan_label(ax1, rute_edges_tercepat, "#00ff7f", 4.0, 14, False)
        ax1.axis('off')

        ax2.set_facecolor('#1e272e')
        ax2.set_title("2. Jalur Distribusi Terpendek (Jarak Minimum)", color="white", fontsize=11, fontweight="bold")
        node_colors_2 = node_colors_2 = [
            "#ff4d4d" if nd in (awal, tujuan) else 
            ("#f1c40f" if nd in simpul_lampu_merah else ("#00ffff" if nd in rute_terpendek else "#2f3542")) 
            for nd in self.G.nodes()]
        nx.draw_networkx_nodes(self.G, self.posisi_nodes, node_color=node_colors_2, node_size=350, ax=ax2)
        nx.draw_networkx_labels(self.G, self.posisi_nodes, font_size=8, font_color="white", font_weight="bold", ax=ax2)
        self.draw_rute_lurus_dan_label(ax2, [ed for ed in self.G.edges() if ed not in rute_edges_terpendek], "#485460", 3, 10, True)
        self.draw_rute_lurus_dan_label(ax2, rute_edges_terpendek, "#00ffff", 4, 14, False)
        ax2.axis('off')

        plt.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.frame_grafik)
        canvas.draw()
        
        # Interaksi Zoom Scroll & Geser
        self.is_dragging = False
        self.press_xyz = None  

        def zoom_pake_scroll(event):
            if event.inaxes is None: return
            ax = event.inaxes
            scale_factor = 0.9 if event.button == 'up' else 1.1
            
            cur_xlim = ax.get_xlim()
            cur_ylim = ax.get_ylim()
            xdata, ydata = event.xdata, event.ydata
            
            new_width = (cur_xlim[1] - cur_xlim[0]) * scale_factor
            new_height = (cur_ylim[1] - cur_ylim[0]) * scale_factor

            relx = (cur_xlim[1] - xdata) / (cur_xlim[1] - cur_xlim[0])
            rely = (cur_ylim[1] - ydata) / (cur_ylim[1] - cur_ylim[0])
            
            ax.set_xlim([xdata - new_width * (1 - relx), xdata + new_width * relx])
            ax.set_ylim([ydata - new_height * (1 - rely), ydata + new_height * rely])

            canvas.draw_idle()

        # Logika Menyimpan Koordinat Layar
        def on_press(event):
            if event.inaxes is None: return
            self.is_dragging = True
            ax = event.inaxes
            self.press_xyz = (ax, ax.get_xlim(), ax.get_ylim(), event.x, event.y)

        # Logika Geser/Drag Mulus
        def on_motion(event):
            if not self.is_dragging or self.press_xyz is None: return
            ax, xlim_start, ylim_start, x_pixel_start, y_pixel_start = self.press_xyz
            
            dx_pixel = event.x - x_pixel_start
            dy_pixel = event.y - y_pixel_start
            
            lebar_peta_x = xlim_start[1] - xlim_start[0]
            tinggi_peta_y = ylim_start[1] - ylim_start[0]
            
            lebar_bbox = ax.bbox.width
            tinggi_bbox = ax.bbox.height
            
            dx_peta = (dx_pixel / ax.bbox.width) * lebar_peta_x
            dy_peta = (dy_pixel / ax.bbox.height) * tinggi_peta_y
            
            ax.set_xlim([xlim_start[0] - dx_peta, xlim_start[1] - dx_peta])
            ax.set_ylim([ylim_start[0] - dy_peta, ylim_start[1] - dy_peta])
            
            canvas.draw_idle()

        def on_release(event):
            self.is_dragging = False
            self.press_xyz = None

        fig.canvas.mpl_connect('scroll_event', zoom_pake_scroll)
        fig.canvas.mpl_connect('button_press_event', on_press)
        fig.canvas.mpl_connect('motion_notify_event', on_motion)
        fig.canvas.mpl_connect('button_release_event', on_release)
        
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

if __name__ == "__main__":
    root = tk.Tk()
    app = AppVisualisasiDijkstra(root)
    root.mainloop()