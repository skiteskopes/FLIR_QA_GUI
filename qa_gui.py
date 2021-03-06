import json
import sys
import os
import cv2
from datetime import datetime
from pytz import timezone
import pytz
from tkinter import *
from tkinter import ttk
from threading import Thread
import subprocess
from tkinter import filedialog
from tkinter import messagebox
import queue
import PIL.Image, PIL.ImageTk

def center_screen_finder(root,w,h):
    ws = root.winfo_screenwidth()
    hs = root.winfo_screenheight()
    x = (ws/2)-(w/2)
    y = (hs/2)- (h/2)
    return '%dx%d+%d+%d' % (w,h,x,y)

class QA_GUI_tool(Frame):
    def __init__(self,master):
        self.master = master
        self.master.configure(bg='navy blue')
        master.title("FLIR QA Flagger")
        master.iconbitmap("flir.ico")
        #master.iconbitmap('flam.ico')
        self.w = 1200 # width for the Tk root
        self.h = 1000# height for the Tk root
        self.token = 0
        master.geometry(center_screen_finder(self.master,self.w,self.h))
        '''WIDGETS'''
        self.control = ttk.Frame(self.master)
        self.navigate = ttk.Frame(self.master)
        self.imagepanel = Canvas(self.master,width=612,height=512,bg='navy blue')
        self.blank = Canvas(self.master,width=1200,height=70)
        self.nextb = ttk.Frame(self.master)
        self.prog_label = Label(self.navigate,text="")
        self.menubar = Menubutton(self.control,text= "File", bg = "navy blue", fg = 'white',height=1,width=6,relief=RAISED,highlightthickness=2)
        self.menubar.menu = Menu(self.menubar,tearoff=0)
        self.menubar["menu"] = self.menubar.menu
        self.menubar.menu.add_command(label="Select Directory",command =self.directory_select)
        self.menubar.menu.add_command(label="Save Changes",command =self.save_changes)
        self.menubar.menu.add_command(label="Hotkeys",command=self.help)
        '''BUILD WIDGET'''
        self.menubar.pack(side=LEFT)
        self.control.pack(side=TOP,fill=X)
        self.prog_label.pack(side=BOTTOM,pady=(0,20))
        self.navigate.pack(side=BOTTOM, fill = X)
        self.nextb.pack(side = BOTTOM, fill = X)
        self.blank.pack(side=TOP,fill=X)
        self.imagepanel.pack(side=TOP,pady=(25,0))

    def convert_int(self,number):
        size = len(number)
        for x in range(size,6):
            number = "0"+number
        return number

    def help(self):
        answer = messagebox.showinfo(title = "Hotkeys", message ="LEFT and RIGHT arrow: Next & Back"+'\n'+"Control+A: Approve"+ '\n' "Control+R: Require Changes" + '\n' + "Control+F: Toggle Flag Frame" + '\n' + "Control+M: Toggle Mark Empty" +'\n'+ "Control+S: Save"+'\n'+ "Control+J: Jump"+'\n'+ "Control+H: Help")

    def clean(self):
        try:
            self.imagepanel.delete('all')
            self.prog_bar.destroy()
            self.next.destroy()
            self.back.destroy()
            self.isflag.destroy()
            self.isempty.destroy()
            self.qaApprove.destroy()
            self.reqchange.destroy()
            self.jump.destroy()
            self.dataset_label.destroy()
            self.dataset_id.destroy()
            self.factpanel.destroy()
            self.framelabel.destroy()
            self.countlabel.destroy()
            self.savelabel.destroy()
        except:
            print('first run no need to destroy')

    def progress(self):
        self.clean()
        self.prog_bar = ttk.Progressbar(self.navigate,orient='horizontal',length=1000, mode="determinate")
        self.prog_bar.pack(side=BOTTOM,pady=20)
        self.prog_var = IntVar()
        self.prog_val = 0
        self.prog_var.set(self.prog_val)
        self.prog_bar['variable'] = self.prog_var

    def directory_select(self):
        self.directory = filedialog.askdirectory()
        os.chdir(self.directory)
        self.qu = queue.Queue()
        self.qutable = queue.Queue()
        self.table = {}
        # run tests to confirm all necessary Conservator Files are present
        if os.path.isfile("index.json") != True:
            print('IO Error: index file missing')
            self.directory = "NULL"
        if os.path.isdir("data") != True:
            print('IO Error: data directory missing')
            self.directory = "NULL"
        if self.directory != "NULL":
            self.progress()
            self.progthread=Thread(target=self.load_json,args=(self.directory,))
            self.progthread.start()
            self.master.after(5,self.check_queue())
            self.master.after(20,self.check_table())

    def check_queue(self):
        while True:
            try: x = self.qu.get_nowait()
            except queue.Empty:
                self.master.after(2,self.check_queue)
                break
            else:
                self.prog_var.set(x)
                self.prog_label.config(text="{0}/{1} images processed".format(self.prog_val,self.datalength))
                if x == self.datalength:
                    break

    def Process_image(self):
        self.rgbimage = PIL.ImageTk.PhotoImage(PIL.Image.fromarray(self.imagehash[self.curr_image]))
        dimensions=self.imagehash[self.curr_image].shape
        self.imagepanel.config(width=dimensions[1],height=dimensions[0])
        self.imagepanel.create_image(dimensions[1]/2,dimensions[0]/2,image=self.rgbimage)


    def Check_status(self,keyword):
        try:
            return self.data["frames"][self.token][keyword]
        except:
            return 'No Entry'

    def genLabeldata(self):
        qaStatus = self.Check_status('qaStatus')
        flagStatus = self.Check_status('isFlagged')
        emptyStatus = self.Check_status('isEmpty')
        self.framelabel.configure(state="normal")
        self.framelabel.delete('1.0',END)
        self.framelabel.tag_configure("center",justify='center')
        self.framelabel.insert(1.0,self.curr_image,'center')
        self.framelabel.configure(state="disabled")
        self.countlabel.config(text="{0}/{1} image".format(self.token+1,self.datalength))
        if qaStatus == 'approved':
            self.QaLabel.config(text = 'QA Status: {0}'.format(qaStatus),bg = 'green', fg = 'white')
        elif qaStatus == 'changesRequested':
            self.QaLabel.config(text = 'QA Status: {0}'.format(qaStatus),bg='red',fg= 'white')
        else:
            self.QaLabel.config(text = 'QA Status: {0}'.format(qaStatus),bg='gray',fg='black')

        if flagStatus == False:
            self.FlagLabel.config(text= 'Flag Status: {0}'.format(flagStatus),bg = 'gray',fg= 'black')
        else:
            self.FlagLabel.config(text= 'Flag Status: {0}'.format(flagStatus),bg = 'orange',fg= 'white')

        if emptyStatus == False:
            self.EmptyLabel.config(text= 'Empty Status: {0}'.format(emptyStatus),bg = 'gray',fg= 'black')
        else:
            self.EmptyLabel.config(text= 'Empty Status: {0}'.format(emptyStatus),bg = 'purple',fg = 'white')

    def check_table(self):
        if self.qutable.empty() != True:
            self.datalength = self.table["datalength"]
            self.datalist = self.table["datalist"]
            self.datahash = self.table["datahash"]
            self.imagehash = self.table["imagehash"]
            self.curr_image = self.table["curr_image"]
            self.datasetID = self.table["datasetID"]
            self.datasetName = self.table["datasetName"]
            self.data = self.table["file"]
            subprocess.call("cd ..", shell = True)
            '''Generate New Widgets After File Processing'''
            self.qaApprove = Button(self.control,command = self.qapp, text="Approve Frame", bg='green',fg='white',height=1)
            self.reqchange = Button(self.control, command = self. qdapp, text="Require Changes", bg='red',fg='white',height=1)
            self.next = Button(self.nextb, text ="Next", bg = 'navy', fg = 'white',command = lambda x="next" : self.Change(x),height=1)
            self.back = Button(self.nextb, text = "Back",bg='navy',fg = 'white',command = lambda x = "back" : self.Change(x),height=1)
            self.isflag = Button(self.control,text = "Toggle Flagging",  bg = 'orange', fg = 'white',command=self.togflag,height=1)
            self.isempty = Button(self.control,text="Toggle Empty",bg='purple',fg='white',command=self.togempty,height=1)
            self.jump = Button(self.control,text = "Jump Frame", bg = 'steel blue',fg = 'white',command = self.frame_jump,height = 1)
            self.master.bind("<Left>",self.process_key)
            self.master.bind("<Right>",self.process_key)
            self.master.bind("<Control-a>",self.process_key)
            self.master.bind("<Control-r>",self.process_key)
            self.master.bind("<Control-s>",self.process_key)
            self.master.bind("<Control-e>", self.process_key)
            self.master.bind("<Control-f>",self.process_key)
            self.master.bind("<Control-h>",self.process_key)
            self.master.bind("<Control-j>",self.process_key)
            '''fact panel building'''
            self.factpanel = ttk.Frame(self.navigate)
            self.factpanel['borderwidth'] = 2
            self.factpanel['relief'] = 'sunken'
            self.framelabel = Text(self.navigate,height=1,borderwidth=2)
            self.countlabel = Label(self.nextb)
            self.QaLabel = Label(self.factpanel)
            self.FlagLabel = Label(self.factpanel)
            self.EmptyLabel= Label(self.factpanel)
            self.savelabel = Label(self.control,fg='green')
            self.QaLabel.pack(side=TOP,pady=5,padx=5)
            self.FlagLabel.pack(side=TOP,pady=5,padx=5)
            self.EmptyLabel.pack(side=TOP,pady=5,padx=5)
            self.factpanel.pack(side=BOTTOM)
            self.countlabel.pack(side=TOP,pady=(5,0))
            self.framelabel.pack(side=TOP)
            '''QA BUTTON'''
            self.jump.pack(side=LEFT)
            self.qaApprove.pack(side=LEFT)
            self.reqchange.pack(side=LEFT)
            self.isflag.pack(side=LEFT)
            self.isempty.pack(side=LEFT)
            self.savelabel.pack(side=RIGHT,padx= 10)
            self.next.pack(side=RIGHT,padx=50,pady=(5,5),ipady=5,ipadx=5)
            self.back.pack(side=LEFT,padx=50,pady=(5,5),ipady=5,ipadx=5)
            self.dataset_label = Label(self.blank,text = self.datasetName,font='Helvetica 12 bold')
            self.dataset_id = Label(self.blank,text= self.datasetID,font='Helvetica 12 bold')
            self.dataset_label.pack(side=TOP,pady=15)
            self.dataset_id.pack(side=TOP,pady=(0,5))
            self.Process_image()
            self.genLabeldata()
        else:
            self.master.after(20,self.check_table)

    def image_manipulation(self,imagename):
        image = cv2.imread(imagename)
        dimensions = image.shape
        current = self.datahash[imagename]["annotations"]
        for annotation in current:
            if annotation["source"]["type"] == "human":
                image = cv2.rectangle(image, (annotation["boundingBox"]["x"],annotation["boundingBox"]["y"]), (annotation["boundingBox"]["x"] + annotation["boundingBox"]["w"],annotation["boundingBox"]["y"]+annotation["boundingBox"]["h"]),(0,255,0),1)
        resize = self.dimension_calculator(dimensions[1],dimensions[0])
        return cv2.resize(cv2.cvtColor(image, cv2.COLOR_BGR2RGB),(int(resize[0]),int(resize[1])),interpolation =cv2.INTER_AREA)

    def dimension_calculator(self,width,height):
        self.standard = 525
        if height > self.standard:
            factor = height/self.standard
            return width/factor,height/factor
        else:
            return width,height

    def load_json(self,directory):
        with open('index.json') as file:
            self.data = json.load(file)
            self.frames,self.datasetID,self.datasetName = self.data["frames"], self.data["datasetId"],self.data["datasetName"]
            self.datalength = len(self.frames)
            #start progressbar threading here
            self.prog_bar["maximum"] = self.datalength
            self.datahash = {}
            self.imagehash = {}
            self.datalist = list()
            os.chdir(directory+"/data")
            for x in self.frames:
                self.imagename = "video-"+x["videoMetadata"]["videoId"]+"-frame-"+self.convert_int(str(x["videoMetadata"]["frameIndex"]))+"-"+x["datasetFrameId"]+".jpg"
                self.datahash[self.imagename]=x
                self.imagehash[self.imagename]=self.image_manipulation(self.imagename)
                self.datalist.append(self.imagename)
                self.prog_val = self.prog_val +1
                self.prog_var.set(self.prog_val)
                self.qu.put(self.prog_var)
            self.table["datalength"] = self.datalength
            self.table["datalist"] = self.datalist
            self.table["datahash"] = self.datahash
            self.table["imagehash"] = self.imagehash
            self.table["curr_image"] = self.datalist[0]
            self.table["datasetID"] = self.datasetID
            self.table["datasetName"] = self.datasetName
            self.table["file"] = self.data
            self.qutable.put(self.table)
            subprocess.call("cd ..", shell=True)

    def Change(self,string):
        if string == "next":
            if self.token == self.datalength-1:
                self.token = 0
            else:
                self.token += 1
        elif string == "back":
            if self.token == 0:
                self.token = self.datalength-1
            else:
                self.token -= 1
        self.curr_image = self.datalist[self.token]
        self.imagepanel.delete('all')
        self.Process_image()
        self.genLabeldata()

    def qapp(self):
        os.chdir(os.path.dirname(os.getcwd()))
        print(os.path.dirname(os.getcwd()))
        frame = self.data["frames"][self.token]
        frame["qaStatus"] = "approved"
        self.data["frames"][self.token]=frame
        print('approved frame {0}'.format(self.datalist[self.token]))
        self.genLabeldata()

    def qdapp(self):
        os.chdir(os.path.dirname(os.getcwd()))
        frame = self.data["frames"][self.token]
        frame["qaStatus"] = "changesRequested"
        self.data["frames"][self.token]=frame
        print('change_requested for frame {0}'.format(self.datalist[self.token]))
        self.genLabeldata()

    def togflag(self):
        os.chdir(os.path.dirname(os.getcwd()))
        frame = self.data["frames"][self.token]
        if frame['isFlagged'] == False:
            frame["isFlagged"] = True
        elif frame['isFlagged'] == True:
            frame["isFlagged"] = False
        self.data["frames"][self.token]=frame
        print('toggled flag for frame {0}'.format(self.datalist[self.token]))
        self.genLabeldata()

    def togempty(self):
        os.chdir(os.path.dirname(os.getcwd()))
        frame = self.data["frames"][self.token]
        if frame['isEmpty'] == False:
            frame["isEmpty"] = True
        elif frame['isEmpty'] == True:
            frame["isEmpty"] = False
        self.data["frames"][self.token]=frame
        print('toggled empty for frame {0}'.format(self.datalist[self.token]))
        self.genLabeldata()

    def frame_jump(self):
        self.pop = Popup_Entry(self.master,self.datalength)
        self.jump["state"] = "disabled"
        self.master.wait_window(self.pop.entry_frame)
        self.jump["state"] = "normal"
        value = int(self.pop.value)
        if value <= 0:
            value = 1
        elif value > self.datalength:
            value = self.datalength
        self.token = value - 1
        self.Change("")


    def save_changes(self):
        self.savelabel.config(text="Saving Changes...")
        self.sthread = Thread(target=self.save_thread)
        self.sthread.start()

    def save_thread(self):
        os.chdir(self.directory)
        self.change_rights("index.json")
        with open("index.json","w+") as edit:
            json.dump(self.data,edit,sort_keys=True,indent=4)
        print('changes saved')
        date_format="%H:%M:%S %Z"
        date = datetime.now(tz=pytz.utc)
        self.savelabel.config(text="Saved last at {0}".format(date.astimezone(timezone('US/Pacific')).strftime(date_format)))

    def change_rights(self,file):
        subprocess.call("chmod 777 {0}".format(file),shell=True)

    def process_key(self,event):
        if event.keysym == "Right":
            self.Change("next")
        elif event.keysym == "Left":
            self.Change("back")
        elif event.keysym == "a":
            self.qapp()
        elif event.keysym == "r":
            self.qdapp()
        elif event.keysym == "f":
            self.togflag()
        elif event.keysym == "e":
            self.togempty()
        elif event.keysym == "s":
            self.save_changes()
        elif event.keysym == "h":
            self.help()
        elif event.keysym == "j":
            self.frame_jump()

class Popup_Entry(Frame):
    def __init__(self,master,datalength):
        self.entry_frame = Toplevel(master)
        self.entry_frame.title("Jump")
        self.entry_frame.geometry(center_screen_finder(self.entry_frame,200,100))
        self.enter = Entry(self.entry_frame)
        self.enterlabel= Label(self.entry_frame,text="Pick frame x with 1 <= x <= {0} :".format(datalength))
        self.enterbutton= Button(self.entry_frame,text="OK",command = self.activate,bg="steel blue",fg='white')
        self.enterlabel.pack(side=TOP,pady=5)
        self.enter.pack(side=TOP,pady=5)
        self.enterbutton.pack(side=TOP,pady=5)
        self.entry_frame.bind("<Return>",self.process_key)
        self.enter.focus_set()
    def activate(self):
        self.value = self.enter.get()
        self.entry_frame.destroy()
    def process_key(self,event):
        self.activate()


if __name__ == '__main__':
    root = Tk()
    my_gui = QA_GUI_tool(root)
    root.mainloop()
