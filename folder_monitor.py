from time import sleep
from threading import Thread, Event
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from infi.systray import SysTrayIcon
from win11toast import notify
import tkinter as tk
from tkinter import filedialog
import os, shutil, sys, json, queue
from sys import exit

folder_to_monitor=''
monitoring_thread = Thread()
copied_files=[]
message=''
restart_event=Event()
stop_event=Event()
queue_empty=Event()
app_name="FolderMonitor"
bg_colour1="#f2b33d"
settings_folder=os.path.join(os.path.expanduser("~"), "AppData", "Local", app_name)
cwd=os.getcwd()
processing_file=False

# CONFIG --------------------------------------------------

def app_folder(prog: str) -> str:
	def createFolder(directory):
		try:
			if not os.path.exists(directory):
				os.makedirs(directory)
		except OSError:
			raise

	if sys.platform == "win32":
		folder = os.path.join(os.path.expanduser("~"), "AppData", "Local", prog)
		createFolder(folder)
	return folder

def read_config():
	global folder_to_monitor

	try:
		with open(os.path.join(app_folder(app_name),'config.ini'), 'r') as f:
			config=json.load(f)
		folder_to_monitor=config['folder']

	except FileNotFoundError:
		settings_window(folder_to_monitor)
	
	if folder_to_monitor:
		if not os.path.exists(folder_to_monitor):
			settings_window(folder_to_monitor)
			if not os.path.exists(folder_to_monitor):
				read_config()


def write_config(config):
	global cwd
	with open(os.path.join(app_folder(app_name),'config.ini'), 'w') as f:
		json.dump(config, f)
	
	if not os.path.exists(os.path.join(settings_folder, 'folder_monitor_notification_icon.png')):
		try:
			shutil.copyfile(os.path.join(cwd, 'folder_monitor_notification_icon.png'), os.path.join(settings_folder, 'folder_monitor_notification_icon.png'))
		except:
			pass

# GUI --------------------------------------------------

def notification_window(systray):
	global message
	notify('New files', str(message), icon=f"file:///{os.path.join(cwd, 'folder_monitor_notification_icon.png')}", on_click=str(message))
	# notify('New files', str(message), icon=f"file:///{os.path.join(settings_folder,'folder_monitor_notification_icon.png')}", on_click=str(message))

def on_quit_callback(systray):
	stop_event.set()

class Frame(tk.Frame):
	def __init__(self, master, **kwargs):
		super().__init__(master)
		global bg_colour1
		self["bg"]=bg_colour1
		self.config(**kwargs)

class Button(tk.Button):
	def __init__(self, master, text, command, **kwargs):
		super().__init__(master, text=text, command=command)
		self['padx']=15
		self['cursor']="hand2"
		self["bg"]="white"
		self.config(**kwargs)

def settings_window(systray):
	global bg_colour1, folder_to_monitor, window

	def on_closing():
		global window
		window.destroy()

	wdth=500
	hght=120
	window=tk.Tk()
	x=window.winfo_screenwidth() // 2 - wdth // 2
	y=window.winfo_screenheight() // 2 - hght // 2
	window.geometry(f"{wdth}x{hght}+{int(x)}+{int(y)}")
	window.title("Folder Monitor")
	window.iconbitmap("folder_monitor.ico")
	window.columnconfigure(0, weight=1)
	window.rowconfigure(0, weight=1)
	window.rowconfigure(1, weight=1)
	frame1=Frame(window)
	frame1.grid(row=0, column=0, rowspan=2, sticky="nsew")
	
	if folder_to_monitor:
		label_text=folder_to_monitor
		button_text='Change'
	else:
		label_text='Choose a folder to monitor'
		button_text='Choose folder'

	working_folder=tk.Label(frame1,
		width=55,
		text=label_text,
		wraplength=460,
		bg=bg_colour1,
		fg="black",
		font=("TkTextFont", 12),
		anchor="center")
	working_folder.grid(row=0, column=0, sticky="ew", pady=(15, 15))

	change_folder_button = Button(frame1, text=button_text, command=lambda: change_folder(working_folder, change_folder_button, folder_to_monitor))
	change_folder_button.grid(row=1, column=0, sticky='s')
	window.protocol("WM_DELETE_WINDOW", on_closing)
	window.mainloop()

def about_window(systray):
	global bg_colour1

	def on_closing():
		window.destroy()

	wdth=400
	hght=200
	window=tk.Tk()
	x=window.winfo_screenwidth() // 2 - wdth // 2
	y=window.winfo_screenheight() // 2 - hght // 2
	window.geometry(f"{wdth}x{hght}+{int(x)}+{int(y)}")
	window.title("Folder Monitor")
	window.iconbitmap("folder_monitor.ico")
	window.columnconfigure(0, weight=1)
	window.rowconfigure(0, weight=1)
	frame1=Frame(window)
	frame1.columnconfigure(0, weight=1)
	frame1.rowconfigure(0, weight=2)
	frame1.rowconfigure(1, weight=1)
	frame1.rowconfigure(2, weight=5)
	frame1.grid(row=0, column=0, sticky='nsew')

	about_text=tk.Label(frame1,
		width=44,
		text='Folder Monitor v1.0 by Mihai Părpălea\nCredits:\nMircea Constantinescu',
		wraplength=360,
		bg=bg_colour1,
		fg='black',
		font=('TkTextFont', 12),
		anchor='center')
	about_text.grid(row=0, column=0, sticky='ew', pady=(15, 15))

	close_button = Button(frame1, text='Close', command=on_closing)
	close_button.grid(row=2, column=0)

	# window.bind(stop_event, lambda event: on_closing)
	window.protocol('WM_DELETE_WINDOW', on_closing)
	window.mainloop()

# MONITORING FOLDER --------------------------------------------------

class CustomHandler(FileSystemEventHandler):
	def on_created(self, event):
		if event.is_directory:
			return
		copied_files.append(event.src_path)
		files_beeing_transfered.put(event.src_path)
		# print(f'put -> {files_beeing_transfered.qsize()}')

def start_monitoring():
	event_handler = CustomHandler()
	observer = Observer()
	observer.schedule(event_handler, folder_to_monitor, recursive=True)
	observer.start()
	try:
		while not restart_event.is_set():
			sleep(1)
	except KeyboardInterrupt:
		pass
	observer.stop()
	observer.join()

def extract_folder(list):
	#finding common folder for all new files
	temp1=list[0].split('\\')
	del temp1[-1]
	result=temp2=[]

	for i in range(len(list)):
		result=[]
		temp2=list[i].split('\\')
		for j in range(len(temp2)):
			try:
				if temp1[j]==temp2[j]:
					result.append(temp2[j])
			except:
				pass
		temp1=result
	result[0]+='/'
	return (os.path.join(*result))

def start_monitoring_thread():
	global monitoring_thread
	if monitoring_thread.is_alive():
		restart_event.set()
		monitoring_thread.join()
		restart_event.clear()

	monitoring_thread = Thread(target=start_monitoring)
	monitoring_thread.daemon = True  # This will allow the program to exit even if the thread is still running
	monitoring_thread.start()


def check_file_copyied(queue):
	global copied_files, processing_file
	while not stop_event.is_set():
		is_ready=False
		path = queue.get()
		queue_empty.clear()
		processing_file=True
		while True:
			try:
				with open(path) as f:
					is_ready=True
			except:
				sleep(0.1)
			if is_ready:
				print(path)
				break
		copied_files.append(path)
		processing_file=False
		if queue.empty():
			queue_empty.set()

def notify_worker(queue):
	global message, copied_files, processing_file

	while not stop_event.is_set():
		if queue_empty.is_set():
			print('queue empty')
			queue_empty.clear()
			counter=5
			while counter>0:
				sleep(1)
				counter=-1
				if queue_empty.is_set():
					print('queue restart')
					counter=3
					queue_empty.clear()
				if processing_file:
					counter=3
					print('processing file')
			message=extract_folder(copied_files)
			notification_window(message)
			copied_files=[]
			queue_empty.clear()
		sleep(5)

def change_folder(label, button, folder):
	global folder_to_monitor

	if folder_to_monitor:
		initial = folder_to_monitor
	else:
		initial = folder = os.path.join(os.path.expanduser("~"), "Documents")
	folder=filedialog.askdirectory(initialdir = initial)
	if (folder):
		label.config(text=folder)
		folder_to_monitor=folder
		write_config({"folder": folder_to_monitor})
		button.configure(text='Change')
		start_monitoring_thread()

# BEGIN --------------------------------------------------

read_config()

menu_options = (('Settings', None, settings_window), ('About', None, about_window))
systray = SysTrayIcon(r'.\folder_monitor.ico', 'Folder Monitor', menu_options, on_quit=on_quit_callback)
systray.start()

files_beeing_transfered = queue.Queue()

collector_thread = Thread(target=check_file_copyied, args=(files_beeing_transfered,))
collector_thread.daemon=True
collector_thread.start()

notifier_thread=Thread(target=notify_worker, args=(files_beeing_transfered,))
notifier_thread.daemon=True
notifier_thread.start()

start_monitoring_thread()

exit(0)
