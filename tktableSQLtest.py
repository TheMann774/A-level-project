import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo
import webbrowser

def callback(url):
    webbrowser.open_new(url)

root = tk.Tk()
root.title('Treeview demo')
width = 600
height = 600
root.geometry(str(width)+'x'+str(height))

# define columns
columns = ('name', 'price', 'rating')

tree = ttk.Treeview(root, columns=columns, show='headings', height=(height-65)//30)

# define headings
tree.heading('name', text='Product Name')
tree.heading('price', text='Price')
tree.heading('rating', text='Rating')

# generate sample data
items = [['https://www.sainsburys.co.uk/gol-ui/Product/hovis-soft-white-bread--medium-sliced-800g',1.10,5],
         ['https://www.sainsburys.co.uk/shop/gb/groceries/product/details/kingsmill-50-50-bread--medium-800g',1.00,4],
         ['https://www.sainsburys.co.uk/shop/gb/groceries/product/details/hovis-seed-sensations-7-seeds-bread-800g',1.70,5]]

# add data to the treeview
for item in items:
    tree.insert('', tk.END, values=item)


def item_selected(event):
    print(event)
    curItem = tree.item(tree.focus())
    col = tree.identify_column(event.x)
    row = tree.identify_row(event.y)
    if col == '#1' and row:
        callback(curItem['values'][0])
    if event.x < 25:
        pass

tree.bind('<ButtonRelease-1>', item_selected)
tree.column('name', width=int(width*0.6))
tree.column('price', width=int(width*0.2))
tree.column('rating', width=int(width*0.2))
tree.grid(row=0, column=0, sticky='nsew')

# add a scrollbar
scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=tree.yview)
tree.configure(yscroll=scrollbar.set)
scrollbar.grid(row=0, column=1, sticky='ns')

style = ttk.Style()
style.theme_use("default")
style.configure('Treeview',rowheight=30)

button1 = tk.Button(root, text='Clear', command=lambda:, height=40)
button1.grid(row=1, column=0, sticky='nsew')

# run the app
root.mainloop()
