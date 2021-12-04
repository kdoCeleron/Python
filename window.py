import tkinter as tk
from tkinter import messagebox


def event_01():
    label["text"] = "button is clicked"
    messagebox.showinfo("this is title", txt.get())


root = tk.Tk()
root.title("サンプル画面")
root.geometry("1000x800")

label = tk.Label(root, text="this is label sample", padx=5, pady=5, relief=tk.SUNKEN, foreground="red")
label.pack(padx=50, pady=100)

button = tk.Button(root, text="ボタン", command=event_01)
button.pack(padx=60, pady=100)

txt = tk.Entry(width=50)
txt.pack(padx=70, pady=100)

root.mainloop()
