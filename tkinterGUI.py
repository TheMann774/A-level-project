import tkinter as tk
from tkinter import ttk
from tkinter.messagebox import showinfo
import webbrowser
from Heroku_functions import postgres_execute, postgres_update, postgres_connect

root = tk.Tk()
root_width, root_height = root.winfo_screenwidth()//2, root.winfo_screenheight()//2
root.geometry(str(root_width)+'x'+str(root_height))

data_columns = ['name','rating','price','price']
tree_columns = ['Item','Rating','Price','Emissions']

def clear_window(window):
    _list = window.winfo_children()
    for item in _list :
        if item.winfo_children() :
            _list.extend(item.winfo_children())
    for item in _list:
        item.destroy()

def config_grid(row_weights, row_mins, column_weights, column_mins):
    for i in range(len(row_weights)):
        if row_weights[i]:
            root.grid_rowconfigure(i,weight=row_weights[i], minsize=row_mins[i])
    for i in range(len(column_weights)):
        if column_weights[i]:
            root.grid_columnconfigure(i,weight=column_weights[i], minsize=column_mins[i])

def search_products(search_term, sort_by, desc=True):
    sql_text = '''
    SELECT sainsburys_products.* FROM sainsburys_products
    LEFT JOIN sainsburys_sectors
    ON sainsburys_products.sector_id = sainsburys_sectors.uuid
    WHERE ***condition***
    ORDER BY ***sort_by*** ***direction***'''.replace('***condition***', ' AND '.join(["(sainsburys_products.name LIKE '%x%' OR sainsburys_sectors.path LIKE '%x%')".replace('x',x) for x in search_term.split(' ')])).replace('***sort_by***',sort_by).replace('***direction***','DESC' if desc else 'ASC')
    return postgres_execute(sql_text)

def home_page():
    clear_window(root)
    config_grid(row_weights=[1,5,1,7], row_mins=[30,0,30,0,0], column_weights=[1,10,1,1], column_mins=[50,0,40,0])
    home_button = tk.Button(root, text='Home', command=lambda:home_page)
    home_button.grid(row=0, column=0, sticky='nesw')
    search_bar = tk.Entry(root)
    search_bar.grid(row=2, column=1, sticky='ew', padx=(5,0), pady=5)
    search_button = tk.Button(root, text='Go', command=lambda:search_page(search_bar.get(), 'price'))
    search_button.grid(row=2, column=2, sticky='ew', padx=(0,5), pady=5)
    root.mainloop()

def search_page(search_term, sort_by, desc=False):

    def item_selected(event):
        curItem = tree.item(tree.focus())
        col = tree.identify_column(event.x)
        row = tree.identify_row(event.y)
        if col == '#1' and row:
            webbrowser.open_new(data.iloc[int(row[1:],16)-1]['url'])
        if event.y < 25:
            col_name = data_columns[int(col[1:])-1]
            if sort_by == col_name:
                search_page(search_term, sort_by, not desc)
            else:
                search_page(search_term, col_name)

    clear_window(root)
    config_grid(row_weights=[1,10], row_mins=[30,100], column_weights=[1,10,1], column_mins=[50,210,40])
    home_button = tk.Button(root, text='Home', command=lambda:home_page)
    home_button.grid(row=0, column=0, sticky='nesw')
    search_bar = tk.Entry(root)
    search_bar.grid(row=0, column=1, sticky='nesw', padx=(5,0), pady=5)
    search_button = tk.Button(root, text='Go', command=lambda:search_page(search_bar.get(), sort_by, desc))
    search_button.grid(row=0, column=2, sticky='nesw', padx=(0,5), pady=5)
    tree = ttk.Treeview(root, columns=data_columns, show='headings', height=(int(root.grid_bbox(1,1)[3]*10-25))//30)
    for i in range(len(data_columns)):
        tree.heading(data_columns[i], text=tree_columns[i])
    data = search_products(search_term, sort_by, desc)
    for index, row in data.iterrows():
        tree.insert('', tk.END, values=[row[x] for x in data_columns])
    tree_width = root.grid_bbox(1,1)[2]-5
    tree.bind('<ButtonRelease-1>', item_selected)
    tree.column('name', minwidth=60, anchor='w', stretch=True)
    for i in range(1,len(data_columns)):
        tree.column(data_columns[i], width=60, minwidth=40, anchor='center', stretch=False)
    tree.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
    scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=1, column=2, sticky='ns', pady=5)
    style = ttk.Style()
    style.theme_use("default")
    style.configure('Treeview',rowheight=30)
    root.mainloop()

home_page()
