import tkinter as tk
from tkinter import ttk
import webbrowser
from Heroku_functions import postgres_execute

root = tk.Tk()
root_width, root_height = root.winfo_screenwidth() // 2, root.winfo_screenheight() // 2
root.geometry(str(root_width) + 'x' + str(root_height))

# Column names
data_columns = ['name', 'rating', 'price', 'mass', 'emissions']
tree_columns = ['Item', 'Rating', 'Price', 'Mass', 'Emissions']

#Choice metric names
choice_data_columns = ['emissions_per_kg', 'emissions_per_portion', 'emissions_per_calorie']
choice_tree_columns = ['per kg', 'per portion', 'per calorie']


def clear_window(window):
    """Clear window"""
    _list = window.winfo_children()
    for item in _list:
        if item.winfo_children():
            _list.extend(item.winfo_children())
    for item in _list:
        item.destroy()


def config_grid(row_weights, row_mins, column_weights, column_mins):
    """Configure the grid with lists of column and row weights and minimum values"""
    for i in range(len(row_weights)):
        if row_weights[i]:
            root.grid_rowconfigure(i, weight=row_weights[i], minsize=row_mins[i])
    for i in range(len(column_weights)):
        if column_weights[i]:
            root.grid_columnconfigure(i, weight=column_weights[i], minsize=column_mins[i])


def search_products(search_term, sort_by, desc=True, choice=0):
    """Search for products from the products database matching a search term, sorted by a chosen column"""
    sector = []
    if '/product/' in search_term:
        # Search by URL to find relevant sector:
        sql_text = """
        SELECT sainsburys_sectors.path AS sector
        FROM sainsburys_products
        LEFT JOIN sainsburys_sectors
        ON sainsburys_products.sector_id = sainsburys_sectors.uuid
        WHERE sainsburys_products.url = '**url**'
        """.replace('**url**', 'https://www.sainsburys.co.uk/shop/gb/groceries/product/details/'+search_term.split('/product/')[1])
        sector = list(postgres_execute(sql_text)['sector'])
    if sector:
        # If sector found, get all proucts from this sector
        sql_text = '''
        SELECT sainsburys_products.* FROM sainsburys_products
        LEFT JOIN sainsburys_sectors
        ON sainsburys_products.sector_id = sainsburys_sectors.uuid
        WHERE sainsburys_sectors.path = '**sector_path**'
        AND sainsburys_products.emissions IS NOT NULL
        AND sainsburys_products.emissions != 0
        ORDER BY ***sort_by*** ***direction***
        '''.replace('**sector_path**', sector[0]).replace(
            '***sort_by***', sort_by).replace('***direction***', 'DESC' if desc else 'ASC')
    else:
        # If sector not found, search by keyword
        sql_text = '''
        SELECT sainsburys_products.* FROM sainsburys_products
        LEFT JOIN sainsburys_sectors
        ON sainsburys_products.sector_id = sainsburys_sectors.uuid
        WHERE ***condition***
        AND sainsburys_products.**choice** IS NOT NULL
        AND sainsburys_products.**choice** <> 0
        ORDER BY ***sort_by*** ***direction***
        '''.replace('***condition***', ' AND '.join(
            ["(LOWER(sainsburys_products.name) LIKE '%x%' OR LOWER(sainsburys_sectors.path) LIKE '%x%')".replace(
                'x', str.lower(x)) for x in search_term.split(' ')])).replace(
            '***sort_by***', sort_by).replace('***direction***', 'DESC' if desc else 'ASC').replace('**choice**', choice_data_columns[choice])
    result = postgres_execute(sql_text)
    # Round the columns to 2 decimal places:
    for column in ['emissions', 'mass', 'emissions_per_kg', 'emissions_per_portion', 'emissions_per_calorie']:
        result[column] = round(result[column], 2)
    # Format mass and price with correct units:
    result['mass'] = result['mass'].apply(lambda x: (str(x) + 'kg') if x >= 1 else (str(int(x * 1000))) + 'g')
    result['price'] = result['price'].apply(lambda x: "£{:.2f}".format(x) if x >= 1 else (str(int(x * 100)) + 'p'))
    return result


def home_page():
    """Run the home page"""
    clear_window(root)
    config_grid(row_weights=[1, 5, 1, 7], row_mins=[30, 0, 30, 0, 0], column_weights=[1, 10, 1, 1],
                column_mins=[50, 0, 40, 0])
    # Create the home button:
    home_button = tk.Button(root, text='Home', command=home_page)
    home_button.grid(row=0, column=0, sticky='nesw')
    # Create the search bar
    search_bar = tk.Entry(root)
    search_bar.grid(row=2, column=1, sticky='ew', padx=(5, 0), pady=5)
    # Create the 'Go' button
    search_button = tk.Button(root, text='Go',
                              command=lambda: search_page(search_bar.get(), choice_data_columns[0]))
    search_button.grid(row=2, column=2, sticky='ew', padx=(0, 5), pady=5)
    # Create the instruction text:
    instruction_label = tk.Label(root, text="Enter a search term or a link to a Sainsbury's product, then press Go to search")
    instruction_label.grid(row=3, column=1, sticky='nw', padx=5)
    root.mainloop()


def search_page(search_term, sort_by, desc=False, choice=0):
    """Run the search page"""
    def item_selected(event):
        """Function to be run if a cell is clicked"""
        # Get column and row of click
        col = tree.identify_column(event.x)
        row = tree.identify_row(event.y)
        if col == '#1' and row:
            # If a product name is clicked, open the link to that product in a chrome browser
            webbrowser.open_new(data.iloc[int(row[1:], 16) - 1]['url'])
        if event.y < 25:
            # If a column heading is clicked, sort by that column
            col_num = int(col[1:]) - 1
            if col_num < len(data_columns):
                col_name = data_columns[col_num]
            else:
                col_name = choice_data_columns[choice]
            if sort_by == col_name:
                search_page(search_term, sort_by, not desc, choice)
            else:
                search_page(search_term, col_name)

    clear_window(root)
    config_grid(row_weights=[1, 10], row_mins=[30, 100], column_weights=[1, 10, 1], column_mins=[50, 210, 40])
    # Create home button
    home_button = tk.Button(root, text='Home', command=home_page)
    home_button.grid(row=0, column=0, sticky='nesw')
    # Create 'change metric' button
    switch_button = tk.Button(root, text='Change metric', command=lambda: search_page(search_term, sort_by, desc, (choice+1) % 3))
    switch_button.grid(row=1, column=0, sticky='new', pady=5)
    # Create search bar:
    search_bar = tk.Entry(root)
    search_bar.grid(row=0, column=1, sticky='nesw', padx=(5, 0), pady=5)
    # Create 'Go' button
    search_button = tk.Button(root, text='Go', command=lambda: search_page(search_bar.get(), sort_by, desc, choice))
    search_button.grid(row=0, column=2, sticky='nesw', padx=(0, 5), pady=5)
    # Create the table
    tree = ttk.Treeview(root, columns=data_columns + [choice_data_columns[choice]], show='headings',
                        height=(int(root.grid_bbox(1, 1)[3] * 10 - 25)) // 30)
    for i in range(len(data_columns)):  # Set the table column names
        tree.heading(data_columns[i], text=tree_columns[i])
    tree.heading(choice_data_columns[choice], text=choice_tree_columns[choice])
    if sort_by in choice_data_columns:
        sort_by = choice_data_columns[choice]
    data = search_products(search_term, sort_by, desc, choice)  # Get the data from the 'search_products' function
    choice_data = list(data[choice_data_columns[choice]])
    # Set the colours of the rows and insert the data:
    if choice_data:
        min_metric, max_metric = min(choice_data), max(choice_data)
        for index, row in data.iterrows():
            tree.insert('', tk.END, values=[row[x] for x in data_columns + [choice_data_columns[choice]]],
                        tags=(str(index),))  # Insert the data
            # Calculate the colours:
            relative_metric = (row[choice_data_columns[choice]] - min_metric) / (max_metric - min_metric)
            if relative_metric <= 0.5:
                r, g = int(511 * relative_metric), 255
            else:
                r, g = 255, int(511 * (1 - relative_metric))
            # Set the colours
            tree.tag_configure(str(index), background=(('#' + "{:-2X}".format(r)[-2:]
                                                        + "{:-2X}".format(g)[-2:] + '00').replace(' ', '0')))
    tree.bind('<ButtonRelease-1>', item_selected)  # Bind the function 'item_selected' to the table
    # Set the sizes of the table columns:
    tree.column('name', minwidth=60, anchor='w', stretch=True)
    for i in range(1, len(data_columns)):
        tree.column(data_columns[i], width=60, minwidth=40, anchor='center', stretch=False)
    tree.column(choice_data_columns[choice], width=60, minwidth=40, anchor='center', stretch=False)
    # Position the tree in the window:
    tree.grid(row=1, column=1, sticky='nsew', padx=5, pady=5)
    # Create the scrollbar:
    scrollbar = ttk.Scrollbar(root, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscroll=scrollbar.set)
    scrollbar.grid(row=1, column=2, sticky='ns', pady=5)
    style = ttk.Style()
    style.theme_use("default")
    style.configure('Treeview', rowheight=30)
    root.mainloop()


home_page()  # Run the program
