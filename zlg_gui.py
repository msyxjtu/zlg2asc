import tkinter as tk

from zlg_func import *


class Gui:
    def __init__(self):
        self.root = tk.Tk()
        self.main_window = tk.Frame(self.root, width=450, height=200)
        self.main_window.pack(expand='YES')

        self.input = tk.Entry()
        self.input.pack(side='left', expand='YES')

        self.convert = tk.Button(text='Convert', command=self.convert_dir)
        self.convert.pack()
        self.action = tk.Label(text='unknown')
        self.action.pack()

    def convert_dir(self):
        self.action.configure(text=self.input.get().replace('\\', '/'))
        zlg_folder_2_asc(self.input.get())


if __name__ == '__main__':
    Gui().root.mainloop()
