import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from scipy.signal import find_peaks, windows
try:
    import sounddevice as sd
except ImportError:
    sd = None
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

class AudioSpectrumAnalyzer:
    def __init__(self, root):
        self.root=root
        root.title("Audio Spectrum Analyzer | v2.5")
        root.geometry("1250x850")
        root.minsize(950,680)
        self.audio=None; self.fs=None; self.file_path=None
        self.start=tk.StringVar(value="0.0")
        self.nfft=tk.StringVar(value="4096")
        self.window=tk.StringVar(value="Hann")
        self.scale=tk.StringVar(value="Logarítmica")
        self.info=tk.StringVar(value="Abre un archivo WAV para comenzar.")
        self.metrics=tk.StringVar(value="")
        self.status=tk.StringVar(value="Preparado.")
        self.play_seconds=tk.StringVar(value="5")
        self.threshold=tk.DoubleVar(value=-40.0)
        self.threshold_label=tk.StringVar(value="-40 dBFS")
        self.freqs=None
        self.dbfs=None
        self.rms_dbfs=None
        self.peak_dbfs=None
        self.live_stream=None
        self.live_data=None
        self.live_fs=None
        self.live_running=False
        self.recording=False
        self.recorded_chunks=[]
        self.recording_fs=None
        self.input_devices=[]
        self.input_device_var=tk.StringVar(value="")
        self.harmonic_rows=[]
        self.build()
        self.refresh_input_devices()
        self.draw_empty()
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    def build(self):
        top=ttk.Frame(self.root,padding=10); top.pack(fill=tk.X)
        ttk.Button(top,text="Abrir archivo WAV...",command=self.open_wav).pack(side=tk.LEFT)
        ttk.Button(top,text="▶ Reproducir",command=self.play_audio).pack(side=tk.LEFT,padx=(8,3))
        ttk.Button(top,text="■ Detener",command=self.stop_audio).pack(side=tk.LEFT,padx=3)
        ttk.Separator(top,orient=tk.VERTICAL).pack(side=tk.LEFT,fill=tk.Y,padx=8)
        ttk.Button(top,text="● Iniciar directo",command=self.start_live).pack(side=tk.LEFT,padx=3)
        ttk.Button(top,text="■ Parar directo",command=self.stop_live).pack(side=tk.LEFT,padx=3)
        ttk.Button(top,text="● Grabar WAV",command=self.start_recording).pack(side=tk.LEFT,padx=3)
        ttk.Button(top,text="■ Fin grabación",command=self.stop_recording).pack(side=tk.LEFT,padx=3)
        ttk.Label(top,text="Duración (s):").pack(side=tk.LEFT,padx=(10,3))
        ttk.Combobox(top,textvariable=self.play_seconds,state="readonly",width=5,
                     values=("2","5","10","15","30")).pack(side=tk.LEFT)
        self.file_label=ttk.Label(top,text="Ningún archivo seleccionado",width=60)
        self.file_label.pack(side=tk.LEFT,padx=10)
        ctl=ttk.LabelFrame(self.root,text="Parámetros del análisis FFT",padding=9)
        ctl.pack(fill=tk.X,padx=10,pady=(0,7))
        ttk.Label(ctl,text="Inicio (s):").pack(side=tk.LEFT)
        ttk.Entry(ctl,textvariable=self.start,width=9).pack(side=tk.LEFT,padx=(5,14))
        ttk.Label(ctl,text="Tamaño FFT:").pack(side=tk.LEFT)
        ttk.Combobox(ctl,textvariable=self.nfft,state="readonly",width=8,
                     values=("1024","2048","4096","8192","16384")).pack(side=tk.LEFT,padx=5)
        ttk.Label(ctl,text="Ventana:").pack(side=tk.LEFT,padx=(12,0))
        ttk.Combobox(ctl,textvariable=self.window,state="readonly",width=10,
                     values=("Rectangular","Hann","Hamming","Blackman")).pack(side=tk.LEFT,padx=5)
        ttk.Label(ctl,text="Escala:").pack(side=tk.LEFT,padx=(12,0))
        ttk.Combobox(ctl,textvariable=self.scale,state="readonly",width=13,
                     values=("Lineal","Logarítmica")).pack(side=tk.LEFT,padx=5)
        ttk.Button(ctl,text="Analizar",command=self.analyze).pack(side=tk.LEFT,padx=12)

        threshold_box=ttk.Frame(self.root,padding=(12,0,12,5))
        threshold_box.pack(fill=tk.X)
        ttk.Label(threshold_box,text="Umbral visual:").pack(side=tk.LEFT)
        self.threshold_scale=tk.Scale(
            threshold_box,from_=-90,to=0,orient=tk.HORIZONTAL,
            resolution=1,variable=self.threshold,showvalue=False,
            length=260,command=self.on_threshold_change
        )
        self.threshold_scale.pack(side=tk.LEFT,padx=8)
        ttk.Label(threshold_box,textvariable=self.threshold_label,width=10).pack(side=tk.LEFT)
        ttk.Label(threshold_box,text="La línea horizontal marca el nivel mínimo de referencia.",
                  foreground="gray").pack(side=tk.LEFT,padx=10)

        box=ttk.LabelFrame(self.root,text="Información del archivo",padding=7)
        box.pack(fill=tk.X,padx=10,pady=(0,7))
        ttk.Label(box,textvariable=self.info).pack(anchor="w")
        box=ttk.LabelFrame(self.root,text="Resultados principales",padding=7)
        box.pack(fill=tk.X,padx=10,pady=(0,7))
        ttk.Label(box,textvariable=self.metrics,font=("Consolas",10),wraplength=1180).pack(fill=tk.X)
        self.tabs=ttk.Notebook(self.root); self.tabs.pack(fill=tk.BOTH,expand=True,padx=10,pady=5)
        t_analysis=ttk.Frame(self.tabs); t_peaks=ttk.Frame(self.tabs)
        t_live=ttk.Frame(self.tabs)
        t_harm=ttk.Frame(self.tabs)
        t_spect=ttk.Frame(self.tabs)
        self.tabs.add(t_analysis,text="Análisis WAV: señal + espectro")
        self.tabs.add(t_peaks,text="Picos espectrales")
        self.tabs.add(t_harm,text="Armónicos")
        self.tabs.add(t_spect,text="Espectrograma")
        self.tabs.add(t_live,text="Tiempo real")
        # Una figura con dos gráficas apiladas: forma de onda arriba y FFT abajo.
        self.fig=Figure(figsize=(11,7.0),dpi=100)
        self.ax1=self.fig.add_subplot(211)
        self.ax2=self.fig.add_subplot(212)
        self.fig.subplots_adjust(left=.085,right=.98,top=.94,bottom=.09,hspace=.42)
        self.canvas=FigureCanvasTkAgg(self.fig,master=t_analysis)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH,expand=True)
        self.can1=self.canvas
        self.can2=self.canvas
        self.tree=ttk.Treeview(t_peaks,columns=("f","db"),show="headings")
        self.tree.heading("f",text="Frecuencia (Hz)"); self.tree.heading("db",text="Nivel (dBFS)")
        self.tree.column("f",width=200,anchor="center"); self.tree.column("db",width=200,anchor="center")
        self.tree.pack(fill=tk.BOTH,expand=True,padx=15,pady=15)
        ttk.Label(t_harm,text="Estimación de la fundamental y sus armónicos a partir del espectro WAV.",
                  padding=10).pack(anchor="w")
        self.harmonic_tree=ttk.Treeview(t_harm,columns=("order","freq","level","delta"),
                                        show="headings",height=12)
        for col,title,width in (("order","Componente",150),("freq","Frecuencia (Hz)",180),
                                ("level","Nivel (dBFS)",180),("delta","Desviación respecto al ideal (Hz)",260)):
            self.harmonic_tree.heading(col,text=title)
            self.harmonic_tree.column(col,width=width,anchor="center")
        self.harmonic_tree.pack(fill=tk.BOTH,expand=True,padx=15,pady=10)
        ttk.Label(t_spect,text="Evolución del contenido frecuencial del archivo WAV.",
                  padding=8).pack(anchor="w")
        self.spec_fig=Figure(figsize=(11,5.5),dpi=100)
        self.spec_ax=self.spec_fig.add_subplot(111)
        self.spec_canvas=FigureCanvasTkAgg(self.spec_fig,master=t_spect)
        self.spec_canvas.get_tk_widget().pack(fill=tk.BOTH,expand=True)
        ttk.Button(t_spect,text="Actualizar espectrograma",
                   command=self.update_spectrogram).pack(anchor="e",padx=10,pady=5)

        device_bar=ttk.Frame(t_live,padding=(10,8,10,2))
        device_bar.pack(fill=tk.X)
        ttk.Label(device_bar,text="Dispositivo de entrada:").pack(side=tk.LEFT)
        self.device_combo=ttk.Combobox(
            device_bar,textvariable=self.input_device_var,state="readonly",width=62
        )
        self.device_combo.pack(side=tk.LEFT,padx=7)
        ttk.Button(device_bar,text="↻ Actualizar dispositivos",
                   command=self.refresh_input_devices).pack(side=tk.LEFT,padx=4)
        live_info=ttk.Label(t_live,text="Selecciona el micrófono o la interfaz de audio y pulsa «Iniciar directo».")
        live_info.pack(anchor="w",padx=10,pady=5)
        self.live_metrics=tk.StringVar(value="Esperando entrada de audio.")
        ttk.Label(t_live,textvariable=self.live_metrics,font=("Consolas",10)).pack(anchor="w",padx=10)
        self.live_fig=Figure(figsize=(11,6.5),dpi=100)
        self.live_ax_time=self.live_fig.add_subplot(211)
        self.live_ax_spec=self.live_fig.add_subplot(212)
        self.live_fig.subplots_adjust(left=.085,right=.98,top=.94,bottom=.09,hspace=.42)
        self.live_canvas=FigureCanvasTkAgg(self.live_fig,master=t_live)
        self.live_canvas.get_tk_widget().pack(fill=tk.BOTH,expand=True)
        ttk.Label(self.root,textvariable=self.status,relief=tk.SUNKEN,anchor="w",padding=5).pack(fill=tk.X,side=tk.BOTTOM)

    def draw_empty(self):
        for ax,title,x,y in ((self.ax1,"Forma de onda","Tiempo (s)","Amplitud"),
                             (self.ax2,"Espectro de amplitud","Frecuencia (Hz)","Nivel (dBFS)")):
            ax.clear(); ax.set_title(title); ax.set_xlabel(x); ax.set_ylabel(y); ax.grid(True,alpha=.25)
        self.canvas.draw_idle()

    @staticmethod
    def to_float(data):
        if np.issubdtype(data.dtype,np.integer):
            info=np.iinfo(data.dtype); return data.astype(float)/max(abs(info.min),abs(info.max))
        return np.asarray(data,dtype=float)

    def open_wav(self):
        name=filedialog.askopenfilename(filetypes=[("Archivos WAV","*.wav"),("Todos","*.*")])
        if not name: return
        try:
            fs,data=wavfile.read(name)
            if fs<=0 or data.size==0: raise ValueError("El archivo no contiene audio válido.")
            audio=np.nan_to_num(self.to_float(data)); channels="Mono"
            if audio.ndim==2:
                if audio.shape[1]!=2: raise ValueError("Solo se admiten WAV mono o estéreo.")
                audio=audio.mean(axis=1); channels="Estéreo convertido a mono (L+R)/2"
            elif audio.ndim!=1: raise ValueError("Formato de canales no compatible.")
            peak=np.max(np.abs(audio))
            if peak>1: audio=audio/peak
            self.audio=audio; self.fs=int(fs); self.file_path=Path(name)
            duration=len(audio)/fs; self.start.set("0.0"); self.file_label.config(text=self.file_path.name)
            self.info.set(f"{channels} | Fs: {fs:,} Hz | Muestras: {len(audio):,} | Duración: {duration:.2f} s | Pico: {np.max(np.abs(audio)):.3f}")
            self.analyze()
        except Exception as e: messagebox.showerror("Error al abrir WAV",str(e))

    def analyze(self):
        if self.audio is None:
            self.status.set("Primero abre un archivo WAV.")
            return
        try:
            start=max(0.0,float(self.start.get().replace(",",".")))
            n=int(self.nfft.get())
            idx=int(round(start*self.fs))
            if idx>=len(self.audio):
                raise ValueError("El instante inicial supera la duración del WAV.")
            segment=self.audio[idx:idx+n]
            used=len(segment)
            if used<n:
                segment=np.pad(segment,(0,n-used))

            wname=self.window.get()
            if wname=="Hann": win=windows.hann(n,sym=False)
            elif wname=="Hamming": win=windows.hamming(n,sym=False)
            elif wname=="Blackman": win=windows.blackman(n,sym=False)
            else: win=np.ones(n)

            spectrum=np.fft.rfft(segment*win)
            amplitude=np.abs(spectrum)/max(float(np.sum(win)),1e-15)
            if n%2==0: amplitude[1:-1]*=2.0
            else: amplitude[1:]*=2.0
            dbfs=20*np.log10(np.maximum(amplitude,1e-10))
            freqs=np.fft.rfftfreq(n,d=1.0/self.fs)
            self.freqs=freqs
            self.dbfs=dbfs
            resolution=self.fs/n

            peaks,_=find_peaks(dbfs,prominence=3)
            peaks=[i for i in peaks if freqs[i]>0]
            peaks=sorted(peaks,key=lambda i:dbfs[i],reverse=True)[:15]
            # Medidas temporales del fragmento real (sin padding).
            measured=self.audio[idx:idx+used]
            peak_value=float(np.max(np.abs(measured))) if used else 0.0
            rms_value=float(np.sqrt(np.mean(measured**2))) if used else 0.0
            peak_db=20*np.log10(max(peak_value,1e-12))
            rms_db=20*np.log10(max(rms_value,1e-12))
            self.peak_dbfs=peak_db
            self.rms_dbfs=rms_db
            self.metrics.set(
                f"Fs: {self.fs:,} Hz | FFT: {n:,} puntos | Resolución: {resolution:.2f} Hz | "
                f"Ventana: {n/self.fs*1000:.2f} ms | Muestras: {used:,}\\n"
                f"Pico: {peak_value:.4f} ({peak_db:.2f} dBFS) | "
                f"RMS: {rms_value:.4f} ({rms_db:.2f} dBFS)"
            )

            self.ax1.clear()
            t=idx/self.fs+np.arange(used)/self.fs
            self.ax1.plot(t,self.audio[idx:idx+used],lw=.85)
            self.ax1.set_title(f"Fragmento temporal — inicio {idx/self.fs:.4f} s · {used} muestras")
            self.ax1.set_xlabel("Tiempo (s)"); self.ax1.set_ylabel("Amplitud")
            self.ax1.grid(True,alpha=.25); self.can1.draw()

            self.ax2.clear()
            self.ax2.plot(freqs[1:],dbfs[1:],lw=.9,label="Espectro")
            level=float(self.threshold.get())
            self.ax2.axhline(level,color="tab:red",linestyle="--",linewidth=1.2,
                             label=f"Umbral: {level:.0f} dBFS")
            self.ax2.set_title(f"Espectro FFT — {wname} · Δf = {resolution:.2f} Hz")
            self.ax2.set_xlabel("Frecuencia (Hz)"); self.ax2.set_ylabel("Nivel (dBFS)")
            self.ax2.set_ylim(-120,5); self.ax2.set_xlim(max(1.0,freqs[1]),self.fs/2)
            self.ax2.set_xscale("log" if self.scale.get()=="Logarítmica" else "linear")
            self.ax2.grid(True,which="both",alpha=.25)
            self.ax2.legend(loc="upper right",fontsize=8)
            self.can2.draw()

            for item in self.tree.get_children(): self.tree.delete(item)
            for i in peaks:
                self.tree.insert("",tk.END,values=(f"{freqs[i]:.2f}",f"{dbfs[i]:.2f}"))
            self.update_harmonics(freqs,dbfs,peaks)
            self.update_spectrogram()
            main_idx=int(np.argmax(dbfs[1:])+1) if len(dbfs)>1 else 0
            self.tabs.select(0)
            self.status.set(f"Análisis completado | Pico principal: {freqs[main_idx]:.2f} Hz "
                            f"({dbfs[main_idx]:.1f} dBFS) | Resolución: {resolution:.2f} Hz")
        except Exception as exc:
            self.status.set(f"Error durante el análisis: {exc}")
            messagebox.showerror("Error de análisis FFT",str(exc))

    def update_spectrogram(self):
        if self.audio is None or not hasattr(self, "spec_ax"):
            return
        try:
            from scipy.signal import spectrogram
            n=int(self.nfft.get())
            segment=self.audio
            nperseg=min(n,len(segment))
            if nperseg < 64:
                raise ValueError("El WAV es demasiado corto para calcular un espectrograma.")
            noverlap=min(int(nperseg*0.75),nperseg-1)
            f,t,power=spectrogram(segment,fs=self.fs,window="hann",
                                  nperseg=nperseg,noverlap=noverlap,
                                  scaling="spectrum",mode="magnitude")
            db=20*np.log10(np.maximum(power,1e-10))
            self.spec_ax.clear()
            mesh=self.spec_ax.pcolormesh(t,f,db,shading="auto",vmin=-100,vmax=0,
                                         cmap="magma")
            self.spec_ax.set_ylim(0,min(self.fs/2,12000))
            self.spec_ax.set_title("Espectrograma del archivo WAV")
            self.spec_ax.set_xlabel("Tiempo (s)")
            self.spec_ax.set_ylabel("Frecuencia (Hz)")
            self.spec_ax.grid(False)
            if not getattr(self,"spec_colorbar",None):
                self.spec_colorbar=self.spec_fig.colorbar(mesh,ax=self.spec_ax,pad=.01)
                self.spec_colorbar.set_label("Nivel relativo (dB)")
            else:
                self.spec_colorbar.update_normal(mesh)
            self.spec_canvas.draw_idle()
        except Exception as exc:
            self.status.set(f"No se pudo calcular el espectrograma: {exc}")

    def update_harmonics(self, freqs, dbfs, peaks):
        for item in self.harmonic_tree.get_children():
            self.harmonic_tree.delete(item)
        if not peaks:
            self.harmonic_tree.insert("",tk.END,values=("No detectada","—","—","—"))
            return
        # La fundamental se estima como el pico más intenso del espectro.
        fundamental_index=max(peaks,key=lambda i: dbfs[i])
        fundamental=float(freqs[fundamental_index])
        self.harmonic_tree.insert("",tk.END,values=("Fundamental",f"{fundamental:.2f}",
                                                    f"{dbfs[fundamental_index]:.2f}","0.00"))
        resolution=float(freqs[1]-freqs[0]) if len(freqs)>1 else 0
        for order in range(2,11):
            target=order*fundamental
            if target >= freqs[-1]:
                break
            lo=max(1,int(round((target-resolution)/resolution)))
            hi=min(len(freqs)-1,int(round((target+resolution)/resolution)))
            idx=lo+int(np.argmax(dbfs[lo:hi+1]))
            deviation=float(freqs[idx]-target)
            self.harmonic_tree.insert("",tk.END,values=(
                f"Armónico {order}",f"{freqs[idx]:.2f}",f"{dbfs[idx]:.2f}",f"{deviation:+.2f}"))

    def on_threshold_change(self, value=None):
        level=float(self.threshold.get())
        self.threshold_label.set(f"{level:.0f} dBFS")
        if self.freqs is None or self.dbfs is None:
            return
        self.ax2.clear()
        self.ax2.plot(self.freqs[1:],self.dbfs[1:],lw=.9,label="Espectro")
        self.ax2.axhline(level,color="tab:red",linestyle="--",linewidth=1.2,
                         label=f"Umbral: {level:.0f} dBFS")
        self.ax2.set_title("Espectro FFT — umbral ajustable")
        self.ax2.set_xlabel("Frecuencia (Hz)")
        self.ax2.set_ylabel("Nivel (dBFS)")
        self.ax2.set_ylim(-120,5)
        self.ax2.set_xlim(max(1.0,self.freqs[1]),self.fs/2)
        self.ax2.set_xscale("log" if self.scale.get()=="Logarítmica" else "linear")
        self.ax2.grid(True,which="both",alpha=.25)
        self.ax2.legend(loc="upper right",fontsize=8)
        self.canvas.draw_idle()

    def refresh_input_devices(self):
        """Carga los dispositivos que ofrecen al menos un canal de entrada."""
        if sd is None:
            self.input_devices=[]
            if hasattr(self, "device_combo"):
                self.device_combo["values"]=()
            self.input_device_var.set("sounddevice no está instalado")
            return
        try:
            devices=sd.query_devices()
            self.input_devices=[]
            labels=[]
            default_input=sd.default.device[0]
            for index, device in enumerate(devices):
                if int(device.get("max_input_channels",0))>0:
                    hostapi=""
                    try:
                        hostapi=sd.query_hostapis(device["hostapi"])["name"]
                    except Exception:
                        pass
                    label=f"{index}: {device['name']} ({hostapi})"
                    self.input_devices.append((index,device,label))
                    labels.append(label)
            self.device_combo["values"]=labels
            selected=None
            for pos,(index,device,label) in enumerate(self.input_devices):
                if index==default_input:
                    selected=pos
                    break
            if selected is None and self.input_devices:
                selected=0
            if selected is not None:
                self.device_combo.current(selected)
                self.input_device_var.set(labels[selected])
            else:
                self.input_device_var.set("No se encontraron entradas de audio")
        except Exception as exc:
            self.input_device_var.set("No se pudieron consultar los dispositivos")
            self.status.set(f"Error al enumerar entradas: {exc}")

    def start_live(self):
        if sd is None:
            messagebox.showerror("Falta una dependencia",
                "Instala sounddevice con: python -m pip install sounddevice")
            return
        if self.live_running:
            return
        try:
            selected_label=self.input_device_var.get()
            selected=next((item for item in self.input_devices if item[2]==selected_label),None)
            if selected is None:
                raise RuntimeError("Selecciona un dispositivo de entrada válido.")
            device_index,device,_=selected
            if int(device.get("max_input_channels",0))<1:
                raise RuntimeError("El dispositivo seleccionado no tiene canales de entrada.")
            samplerate=int(device["default_samplerate"])
            self.live_device_index=device_index
            self.live_fs=samplerate
            self.live_data=np.zeros(int(self.nfft.get()),dtype=np.float32)
            self.live_running=True

            def audio_callback(indata, frames, time_info, status):
                # El callback solo copia datos; la interfaz se actualiza desde el hilo Tk.
                chunk=indata[:,0].copy()
                self.live_data=chunk
                if self.recording:
                    self.recorded_chunks.append(chunk)

            self.live_stream=sd.InputStream(
                device=device_index, channels=1, samplerate=samplerate,
                blocksize=int(self.nfft.get()), callback=audio_callback
            )
            self.live_stream.start()
            self.tabs.select(4)
            self.status.set(f"Analizador en tiempo real activo · {device['name']} · {samplerate:,} Hz")
            self.root.after(120,self.update_live_display)
        except Exception as exc:
            self.live_running=False
            self.live_stream=None
            messagebox.showerror("No se pudo iniciar la entrada de audio",
                                 f"{exc}\\n\\nComprueba que el dispositivo está conectado y que admite entrada de audio. "
                                 "Si usas una interfaz USB, prueba su frecuencia de muestreo predeterminada.")

    def update_live_display(self):
        if not self.live_running or self.live_data is None:
            return
        try:
            n=int(self.nfft.get())
            data=np.asarray(self.live_data,dtype=float)
            if len(data)<n:
                data=np.pad(data,(n-len(data),0))
            else:
                data=data[-n:]
            if self.window.get()=="Hann": win=windows.hann(n,sym=False)
            elif self.window.get()=="Hamming": win=windows.hamming(n,sym=False)
            elif self.window.get()=="Blackman": win=windows.blackman(n,sym=False)
            else: win=np.ones(n)

            spec=np.fft.rfft(data*win)
            amp=np.abs(spec)/max(float(np.sum(win)),1e-15)
            if n%2==0: amp[1:-1]*=2
            else: amp[1:]*=2
            db=20*np.log10(np.maximum(amp,1e-10))
            freq=np.fft.rfftfreq(n,1/self.live_fs)
            t=np.arange(n)/self.live_fs
            peak=float(np.max(np.abs(data)))
            rms=float(np.sqrt(np.mean(data**2)))
            peak_db=20*np.log10(max(peak,1e-12))
            rms_db=20*np.log10(max(rms,1e-12))
            # Frecuencia dominante: máximo espectral por encima de 20 Hz.
            valid=np.where(freq>=20.0)[0]
            if len(valid):
                dominant_index=int(valid[np.argmax(db[valid])])
                dominant_hz=float(freq[dominant_index])
                dominant_level=float(db[dominant_index])
                dominant_text=f"{dominant_hz:.1f} Hz ({dominant_level:.1f} dBFS)"
            else:
                dominant_text="—"
            self.live_metrics.set(
                f"Entrada: {self.live_fs:,} Hz | FFT: {n} | Δf: {self.live_fs/n:.2f} Hz | "
                f"Frecuencia dominante: {dominant_text} | Pico: {peak_db:.1f} dBFS | RMS: {rms_db:.1f} dBFS"
            )

            self.live_ax_time.clear()
            self.live_ax_time.plot(t,data,lw=.75)
            self.live_ax_time.set_title("Señal de entrada — tiempo real")
            self.live_ax_time.set_xlabel("Tiempo (s)")
            self.live_ax_time.set_ylabel("Amplitud")
            self.live_ax_time.grid(True,alpha=.22)

            self.live_ax_spec.clear()
            self.live_ax_spec.plot(freq[1:],db[1:],lw=.8)
            level=float(self.threshold.get())
            self.live_ax_spec.axhline(level,color="tab:red",linestyle="--",lw=1)
            self.live_ax_spec.set_title("Espectro FFT en tiempo real")
            self.live_ax_spec.set_xlabel("Frecuencia (Hz)")
            self.live_ax_spec.set_ylabel("dBFS")
            self.live_ax_spec.set_ylim(-120,5)
            self.live_ax_spec.set_xlim(max(1,freq[1]),self.live_fs/2)
            self.live_ax_spec.set_xscale("log" if self.scale.get()=="Logarítmica" else "linear")
            self.live_ax_spec.grid(True,which="both",alpha=.22)
            self.live_canvas.draw_idle()
        except Exception as exc:
            self.status.set(f"Error en análisis en directo: {exc}")
            self.stop_live()
            return
        self.root.after(120,self.update_live_display)

    def start_recording(self):
        if not self.live_running or self.live_stream is None:
            messagebox.showinfo("Grabación WAV",
                "Primero inicia la entrada en la pestaña Tiempo real.")
            return
        if self.recording:
            return
        self.recorded_chunks=[]
        self.recording_fs=self.live_fs
        self.recording=True
        self.status.set("Grabando entrada de audio… Pulsa «Fin grabación» para terminar.")

    def stop_recording(self):
        if not self.recording:
            return
        self.recording=False
        if not self.recorded_chunks:
            messagebox.showinfo("Grabación WAV","No se han recibido muestras.")
            return
        audio=np.concatenate(self.recorded_chunks).astype(np.float32)
        path=filedialog.asksaveasfilename(
            title="Guardar grabación",
            defaultextension=".wav",
            filetypes=[("Audio WAV","*.wav")],
            initialfile="grabacion_analizador.wav")
        if not path:
            self.status.set("Grabación descartada.")
            self.recorded_chunks=[]
            return
        try:
            # PCM de 16 bits compatible con reproductores habituales.
            pcm=np.clip(audio,-1.0,1.0)
            pcm16=(pcm*32767.0).astype(np.int16)
            wavfile.write(path,int(self.recording_fs),pcm16)
            self.status.set(f"Grabación WAV guardada: {Path(path).name}")
            messagebox.showinfo("Grabación guardada",
                                f"Archivo guardado correctamente:\n{path}")
        except Exception as exc:
            messagebox.showerror("Error al guardar WAV",str(exc))
        finally:
            self.recorded_chunks=[]

    def stop_live(self):
        if self.recording:
            self.stop_recording()
        self.live_running=False
        if self.live_stream is not None:
            try:
                self.live_stream.stop()
                self.live_stream.close()
            except Exception:
                pass
            self.live_stream=None
        self.status.set("Analizador en tiempo real detenido.")

    def play_audio(self):
        if self.audio is None:
            messagebox.showinfo("Reproducción","Primero abre un archivo WAV.")
            return
        if sd is None:
            messagebox.showerror("Falta una dependencia",
                "Para reproducir audio instala sounddevice:\\n\\npython -m pip install sounddevice")
            return
        try:
            start=max(0.0,float(self.start.get().replace(",",".")))
            seconds=float(self.play_seconds.get())
            i0=min(len(self.audio),int(start*self.fs))
            i1=min(len(self.audio),i0+int(seconds*self.fs))
            if i1<=i0: raise ValueError("No hay audio disponible desde ese instante.")
            sd.stop()
            sd.play(self.audio[i0:i1],self.fs)
            self.status.set(f"Reproduciendo desde {i0/self.fs:.2f} s ({(i1-i0)/self.fs:.1f} s).")
        except Exception as exc:
            messagebox.showerror("Error de reproducción",str(exc))
            self.status.set(f"Error de reproducción: {exc}")

    def close_app(self):
        self.stop_live()
        self.stop_audio()
        self.root.destroy()

    def stop_audio(self):
        if sd is not None:
            try: sd.stop()
            except Exception: pass
        self.status.set("Reproducción detenida.")

def main():
    root=tk.Tk(); AudioSpectrumAnalyzer(root); root.mainloop()

if __name__=="__main__": main()
