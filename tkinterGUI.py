import tkinter as tk
from tkinter import ttk
import webbrowser
from Heroku_functions import postgres_execute

root = tk.Tk()
root_width, root_height = root.winfo_screenwidth() // 2, root.winfo_screenheight() // 2
root.geometry(str(root_width) + 'x' + str(root_height))

data_columns = ['name', 'rating', 'price', 'mass', 'emissions']
tree_columns = ['Item', 'Rating', 'Price', 'Mass', 'Emissions']

choice_data_columns = ['emissions_per_kg', 'emissions_per_portion', 'emissions_per_calorie']
choice_tree_columns = ['per kg', 'per portion', 'per calorie']
choice = 0


def clear_window(window):
    _list = window.winfo_children()
    for item in _list:
        if item.winfo_children():
            _list.extend(item.winfo_children())
    for item in _list:
        item.destroy()


def config_grid(row_weights, row_mins, column_weights, column_mins):
    for i in range(len(row_weights)):
        if row_weights[i]:
            root.grid_rowconfigure(i, weight=row_weights[i], minsize=row_mins[i])
    for i in range(len(column_weights)):
        if column_weights[i]:
            root.grid_columnconfigure(i, weight=column_weights[i], minsize=column_mins[i])


def search_products(search_term, sort_by, desc=True):
    sql_text = '''
    SELECT sainsburys_products.* FROM sainsburys_products
    LEFT JOIN sainsburys_sectors
    ON sainsburys_products.sector_id = sainsburys_sectors.uuid
    WHERE ***condition***
    AND sainsburys_products.emissions IS NOT NULL
    AND sainsburys_products.emissions != 0
    ORDER BY ***sort_by*** ***direction***
    '''.replace('***condition***', ' AND '.join(
        ["(LOWER(sainsburys_products.name) LIKE '%x%' OR LOWER(sainsburys_sectors.path) LIKE '%x%')".replace(
            'x', str.lower(x)) for x in search_term.split(' ')])).replace(
        '***sort_by***', sort_by).replace('***direction***', 'DESC' if desc else 'ASC')
    result = postgres_execute(sql_text)
    for column in ['emissions', 'mass', 'emissions_per_kg', 'emissions_per_portion', 'emissions_per_calorie']:
        result[column] = round(result[column], 2)
    result['mass'] = result['mass'].apply(lambda x: (str(x)+'kg') if x >= 1 else (str(int(x*1000))) + 'g')
    result['price'] = result['price'].apply(lambda x: "£{:.2f}".format(x) if x >= 1 else (str(int(x*100)) + 'p'))
    return result


def home_page():
    clear_window(root)
    config_grid(row_weights=[1, 5, 1, 7], row_mins=[30, 0, 30, 0, 0], column_weights=[1, 10, 1, 1],
                column_mins=[50, 0, 40, 0])
    home_button = tk.Button(root, text='Home', command=home_page)
    home_button.grid(row=0, column=0, sticky='nesw')
    search_bar = tk.Entry(root)
    search_bar.grid(row=2, column=1, sticky='ew', padx=(5, 0), pady=5)
    search_button = tk.Button(root, text='Go', command=lambda: search_page(search_bar.get(), choice_data_columns[choice]))
    search_button.grid(row=2, column=2, sticky='ew', padx=(0, 5), pady=5)
    root.mainloop()


def search_page(search_term, sort_by, desc=False):
    def item_selected(event):
        col = tree.identify_column(event.x)
        row = tree.identify_row(event.y)
        if col == '#1' and row:
            webbrowser.open_new(data.iloc[int(row[1:], 16) - 1]['url'])
        if event.y < 25:
            col_num = int(col[1:]) - 1
            if col_num < len(data_columns):
                col_name = data_columns[col_num]
            else:
                col_name = choice_data_columns[choice]
            if sort_by == col_name:
                search_page(search_term, sort_by, not desc)
            else:
                search_page(search_term, col_name)

    clear_window(root)
    config_grid(row_weights=[1, 10], row_mins=[30, 100], column_weights=[1, 10, 1], column_mins=[50, 210, 40])
    home_button = tk.Button(root, text='Home', command=home_page)
    home_button.grid(row=0, column=0, sticky='nesw')
    search_bar = tk.Entry(root)
    search_bar.grid(row=0, column=1, sticky='nesw', padx=(5, 0), pady=5)
    search_button = tk.Button(root, text='Go', command=lambda: search_page(search_bar.get(), sort_by, desc))
    search_button.grid(row=0, column=2, sticky='nesw', padx=(0, 5), pady=5)
    tree = ttk.Treeview(root, columns=data_columns + [choice_data_columns[choice]], show='headings',
                        height=(int(root.grid_bbox(1, 1)[3] * 10 - 25)) // 30)
    for i in range(len(data_columns)):
        tree.heading(data_columns[i], text=tree_columns[i])
    tree.heading(choice_data_columns[choice], text=choice_tree_columns[choice])
    data = search_products(search_term, sort_by, desc)
    choice_data = list(data[choice_data_columns[choice]])
    min_metric, max_metric = min(choice_data), max(choice_data)
    for index, row in data.iterrows():
        tree.insert('', tk.END, values=[row[x] for x in data_columns + [choice_data_columns[choice]]], tags=(str(index),))
        relative_metric = (row[choice_data_columns[choice]]-min_metric)/(max_metric-min_metric)
        print(relative_metric)
        tree.tag_configure(str(index), background=(('#' + "{:-2X}".format(int(511 * relative_metric))[-2:]
                                                   + "{:-2X}".format(int(511 * (1-relative_metric)))[-2:] + '00').replace(' ','0')))
    tree.bind('<ButtonRelease-1>', item_selected)
    tree.column('name', minwidth=60, anchor='w', stretch=True)
    for i in range(1, len(data_columns)):
        tree.column(data_columns[i], width=60, minwidth=40, anchor='center', stretch=False)
    tree.column(choice_data_columns[choice], width=60, minwidth=40, anchor='center', stretch=False)
    tree.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
    scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=1, column=2, sticky='ns', pady=5)
    style = ttk.Style()
    style.theme_use("default")
    style.configure('Treeview', rowheight=30)
    root.mainloop()


home_page()
