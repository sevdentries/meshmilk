#This is an example program which has a button, label, and an entry object.
#Play around with things to see how they work.
#Also look up tkinter docs if confused

from tkinter import *
from tkinter import ttk
import tkinter as tk
root = Tk()
root.geometry("600x400+100+100")
root.title("Meshmilk")

label1 = Label(root, text="This is a test of the tkinter system, enter name below.")
button1 = Button(root, text="greet button", command=lambda:print("Hello, "+entry1.get()+"!"))
entry1 = Entry(root, text="What is your name?")

def selectclear(event):
    if entry1.get() == "What is your name?":
        entry1.configure(text="")

entry1.bind("<Button-1>", selectclear)

label1.pack()
button1.pack()
entry1.pack()

#pack is a simple system for building in tkinter, it works for now but you guys should
#use .grid instead cuz its more neat, ask me if y'all need help with that  thanks
#altonius felonius bolus


root.mainloop()