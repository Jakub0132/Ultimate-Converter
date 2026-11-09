import os
from pathlib import Path
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from converter import MODES, accepts, convert
from youtube_downloader import DownloadCancelled, download_youtube, normalize_url

APP_MODES = {**MODES, 'YouTube': ('MP4', 'MP3')}


class ConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Ultimate Converter')
        self.geometry('1000x720')
        self.minsize(850, 640)
        self.configure(bg='#101522')
        self.files = []
        self.busy = False
        self.events = queue.Queue()
        self.cancel_download = threading.Event()
        self.youtube_url = tk.StringVar()
        self.mode = tk.StringVar(value='Images')
        self.target = tk.StringVar(value='PNG')
        self.destination = tk.StringVar(value=str(Path.home() / 'Downloads' / 'Ultimate Converter'))
        self.status = tk.StringVar(value='Add files and select an output format.')
        from retro_ui import build_ui
        build_ui(self, APP_MODES)
        self.change_mode()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.poll)

    def change_mode(self, event=None):
        for name, button in self.tab_buttons.items():
            button.configure(relief='sunken' if name == self.mode.get() else 'raised')
        self.format_box.configure(values=APP_MODES[self.mode.get()])
        self.target.set(APP_MODES[self.mode.get()][0])
        self.files.clear()
        self.table.delete(*self.table.get_children())
        youtube = self.mode.get() == 'YouTube'
        self.add_button.configure(state='disabled' if youtube else 'normal')
        self.remove_button.configure(state='disabled' if youtube else 'normal')
        self.start_button.configure(text='Download and convert' if youtube else 'Convert')
        self.input_group.configure(text='1. YouTube video' if youtube else '1. Files')
        self.progress.configure(value=0)
        if youtube:
            self.table_frame.grid_remove()
            self.file_actions.grid_remove()
            self.youtube_panel.grid(row=0, column=0, columnspan=2, sticky='nsew')
            self.note.configure(text='MP4: choose an available resolution before downloading. MP3: 192 kb/s audio. One link = one video.')
            self.status.set('Paste a link and select MP4 or MP3.')
            return
        self.youtube_panel.grid_remove()
        self.file_actions.grid()
        self.table_frame.grid()
        self.status.set('Add files and select an output format.')
        self.note.configure(text={'Images': 'JPG, PNG, WEBP, BMP, TIFF • JPG replaces transparency with white. Multi-frame files: first frame only.', 'Documents': 'PDF → Word (.docx) • Simplified text and image layout. No OCR or table reconstruction.', 'Audio': 'WAV, MP3, FLAC, OGG, M4A, AAC • MP3 at 192 kb/s.'}[self.mode.get()])

    def add_files(self):
        patterns = {'Images': '*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff', 'Documents': '*.pdf', 'Audio': '*.wav *.mp3 *.flac *.ogg *.m4a *.aac'}
        paths = filedialog.askopenfilenames(filetypes=[('Supported files', patterns[self.mode.get()])])
        for value in paths:
            path = Path(value)
            if path not in self.files and accepts(path, self.mode.get()):
                self.files.append(path)
                self.table.insert('', 'end', iid=str(path), values=(path.name, f'{path.stat().st_size / 1024 / 1024:.2f} MB', 'Ready'))
        self.status.set(f'Files ready: {len(self.files)}. Select a format and folder, then click Convert.')

    def remove_files(self):
        for item in self.table.selection():
            self.files.remove(Path(item))
            self.table.delete(item)
        self.status.set(f'Files: {len(self.files)}')

    def choose_folder(self):
        folder = filedialog.askdirectory(title='Choose where to save converted files', initialdir=self.destination.get() if Path(self.destination.get()).is_dir() else str(Path.home()))
        if folder:
            self.destination.set(folder)

    def open_folder(self):
        path = Path(self.destination.get())
        if path.is_dir():
            os.startfile(str(path))
        else:
            messagebox.showinfo('Output', 'The folder will be created after the first conversion.')

    def start(self):
        if self.busy:
            return
        if self.mode.get() == 'YouTube':
            self.start_youtube()
            return
        if not self.files:
            messagebox.showinfo('Files', 'Add files to convert first.')
            return
        if not self.destination.get().strip():
            messagebox.showerror('Folder', 'Select an output folder.')
            return
        self.busy = True
        for widget in [self.add_button, self.remove_button, self.folder_button, self.folder_entry, self.start_button, self.mode_box, self.format_box]:
            widget.configure(state='disabled')
        self.progress.configure(maximum=len(self.files), value=0)
        self.status.set('Converting…')
        threading.Thread(target=self.worker, args=(list(self.files), self.destination.get(), self.target.get()), daemon=True).start()

    def start_youtube(self):
        try:
            url = normalize_url(self.youtube_url.get())
            if not self.destination.get().strip():
                raise ValueError('Select an output folder.')
        except ValueError as exc:
            messagebox.showerror('YouTube', str(exc))
            return
        self.busy = True
        self.cancel_download.clear()
        for widget in [self.add_button, self.remove_button, self.folder_button, self.folder_entry, self.start_button, self.mode_box, self.format_box, self.url_entry]:
            widget.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.progress.configure(mode='indeterminate', maximum=100, value=0)
        self.progress.start(12)
        self.status.set('Connecting to YouTube…')
        threading.Thread(target=self.youtube_worker, args=(url, self.destination.get(), self.target.get()), daemon=True).start()

    def request_cancel(self):
        self.cancel_download.set()
        self.cancel_button.configure(state='disabled')
        self.status.set('Cancelling download… waiting for the current operation to finish.')

    def youtube_worker(self, url, destination, target):
        def report(message, percent):
            self.events.put(('download_progress', message, percent))
        def choose_quality(title, qualities):
            ready = threading.Event()
            selection = []
            self.events.put(('choose_quality', title, qualities, ready, selection))
            while not ready.wait(0.1):
                if self.cancel_download.is_set():
                    raise DownloadCancelled()
            if not selection or self.cancel_download.is_set():
                raise DownloadCancelled()
            return selection[0]
        try:
            output = download_youtube(url, destination, target, report, self.cancel_download, choose_quality)
            self.events.put(('done', 1, 0, f'Saved to:\n{output}'))
        except DownloadCancelled:
            self.events.put(('done', 0, 0, 'Download cancelled. Temporary files have been removed.'))
        except Exception as exc:
            if self.cancel_download.is_set():
                detail = 'Download cancelled.'
            else:
                detail = f'Download failed:\n{exc}\n\nCheck your connection and video availability. Videos that require signing in are not supported.'
            self.events.put(('done', 0, 0 if self.cancel_download.is_set() else 1, detail))

    def show_quality_dialog(self, title, qualities, ready, selection):
        self.progress.stop()
        self.status.set('Choose a video resolution in the dialog.')
        dialog = tk.Toplevel(self)
        dialog.title('YouTube video quality')
        dialog.transient(self)
        dialog.resizable(False, False)
        frame = ttk.Frame(dialog, padding=20)
        frame.pack(fill='both', expand=True)
        ttk.Label(frame, text=title, wraplength=440).pack(anchor='w', pady=(0, 12))
        ttk.Label(frame, text='Which resolution would you like to download?').pack(anchor='w')
        choice = tk.StringVar(value=f'{qualities[0]}p')
        box = ttk.Combobox(frame, state='readonly', textvariable=choice,
                           values=[f'{height}p' for height in qualities], width=24)
        box.pack(fill='x', pady=12)
        ttk.Label(frame, text='Only resolutions available for this video are shown.\nHigher resolutions require more storage and time.',
                  style='Muted.TLabel').pack(anchor='w')
        buttons = ttk.Frame(frame)
        buttons.pack(fill='x', pady=(16, 0))
        def finish(accept):
            if accept:
                selection.append(qualities[box.current()])
            else:
                self.cancel_download.set()
            ready.set()
            dialog.grab_release()
            dialog.destroy()
        ttk.Button(buttons, text='Cancel', command=lambda: finish(False)).pack(side='left')
        ttk.Button(buttons, text='Download selected quality', style='Accent.TButton',
                   command=lambda: finish(True)).pack(side='right', padx=(12, 0))
        dialog.protocol('WM_DELETE_WINDOW', lambda: finish(False))
        dialog.grab_set()
        box.focus_set()

    def worker(self, paths, destination, target):
        details, errors = [], 0
        for index, path in enumerate(paths):
            self.events.put(('row', str(path), 'Converting…'))
            try:
                output, warning = convert(path, destination, target)
                self.events.put(('row', str(path), 'Done' + (' • warning' if warning else '')))
                details.append(f'{path.name}\nSaved to: {output.resolve()}' + (f'\n{warning}' if warning else ''))
            except Exception as exc:
                errors += 1
                self.events.put(('row', str(path), 'Error'))
                details.append(f'{path.name}: {exc}')
            self.events.put(('progress', index + 1))
        self.events.put(('done', len(paths) - errors, errors, '\n\n'.join(details)))

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == 'row':
                    self.table.set(event[1], 'status', event[2])
                elif event[0] == 'progress':
                    self.progress.configure(value=event[1])
                elif event[0] == 'choose_quality':
                    if self.cancel_download.is_set():
                        event[3].set()
                    else:
                        self.show_quality_dialog(*event[1:])
                elif event[0] == 'download_progress':
                    if not self.cancel_download.is_set():
                        self.status.set(event[1])
                    self.progress.stop()
                    if event[2] is None:
                        self.progress.configure(mode='indeterminate')
                        self.progress.start(12)
                    else:
                        self.progress.configure(mode='determinate', maximum=100, value=event[2])
                else:
                    self.busy = False
                    self.progress.stop()
                    self.progress.configure(mode='determinate')
                    self.cancel_button.configure(state='disabled')
                    self.url_entry.configure(state='normal')
                    for widget in [self.add_button, self.remove_button, self.folder_button, self.folder_entry, self.start_button]:
                        widget.configure(state='normal')
                    self.mode_box.configure(state='readonly')
                    self.format_box.configure(state='readonly')
                    if self.mode.get() == 'YouTube':
                        self.add_button.configure(state='disabled')
                        self.remove_button.configure(state='disabled')
                        self.progress.configure(value=100 if event[1] else 0)
                    self.status.set(f'Completed: {event[1]}  •  Errors: {event[2]}')
                    dialog = tk.Toplevel(self)
                    dialog.title('Conversion results')
                    dialog.geometry('650x420')
                    ttk.Button(dialog, text='Open output folder', command=self.open_folder).pack(side='bottom', pady=10)
                    text = tk.Text(dialog, wrap='word', padx=18, pady=18, font=('Segoe UI', 10))
                    text.pack(fill='both', expand=True)
                    text.insert('1.0', event[3])
                    text.configure(state='disabled')
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('Conversion in progress', 'Please wait for the conversion to finish before closing.')
        else:
            self.destroy()


if __name__ == '__main__':
    ConverterApp().mainloop()
