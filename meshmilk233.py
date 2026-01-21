import tkinter as tk

root = tk.Tk()
root.geometry('350x200')
root.title("Meshmilk")

def onClick():
    input = txtbox.get()
    if input == "meshmilk":
        label.configure(text = "meshmilk!!!")
    else:
        result = f"You inputted {input}."
        label.configure(text = result) 

label = tk.Label(root, text='Type something')
label.grid(column=0, row=1)

txtbox = tk.Entry(root, width=10)
txtbox.grid(column=0, row=2)

startbtn = tk.Button(root, text='Start', command=onClick)
startbtn.grid(column=0, row=3)

root.mainloop()