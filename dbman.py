#!/usr/bin/env python3
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

class OSIDatabaseManager:
    def __init__(self, root):
        self.root = root
        self.root.title("OSI (OriginSourceInstall) Database Manager")
        self.root.geometry("900x600")
        self.root.minimum_size = (800, 500)
        
        self.db_path = None
        self.selected_item_id = None
        
        # Apply Styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.setup_styles()
        
        # Build UI layout
        self.create_widgets()
        
        # Try auto-detecting cache DB as a convenience
        default_db = os.path.expanduser("~/.cache/osi/packages.db")
        if os.path.exists(default_db):
            if messagebox.askyesno("Load Default DB", f"Detected existing local OSI database at:\n{default_db}\n\nWould you like to open it?"):
                self.load_database(default_db)

    def setup_styles(self):
        # Premium/Modern color scheme (Slate / Dark theme accents)
        self.style.configure(".", font=("Helvetica", 10))
        self.style.configure("TFrame", background="#f3f4f6")
        self.style.configure("TLabelframe", background="#f3f4f6", foreground="#374151")
        self.style.configure("TLabelframe.Label", font=("Helvetica", 10, "bold"), background="#f3f4f6", foreground="#1f2937")
        self.style.configure("TButton", font=("Helvetica", 10, "bold"), padding=6)
        self.style.configure("Accent.TButton", foreground="white", background="#2563eb")
        self.style.map("Accent.TButton", background=[("active", "#1d4ed8")])
        self.style.configure("Treeview", rowheight=25, font=("Helvetica", 10))
        self.style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"))
        self.root.configure(background="#f3f4f6")

    def create_widgets(self):
        # 1. Top Control Bar (DB File Operations)
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X, side=tk.TOP)
        
        self.db_label = ttk.Label(top_frame, text="Database: No file loaded", font=("Helvetica", 10, "italic"), foreground="#4b5563")
        self.db_label.pack(side=tk.LEFT, padx=5)
        
        btn_open = ttk.Button(top_frame, text="Open DB", command=self.open_db_dialog)
        btn_open.pack(side=tk.RIGHT, padx=5)
        
        btn_new = ttk.Button(top_frame, text="Create New DB", command=self.create_db_dialog)
        btn_new.pack(side=tk.RIGHT, padx=5)

        # Main Workspace Split Pane
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 2. Left Panel: Treeview / Package List
        left_panel = ttk.Frame(paned_window, padding=5)
        paned_window.add(left_panel, weight=1)

        # Search Bar Frame
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=2)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_list())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        btn_clear = ttk.Button(search_frame, text="Clear", width=6, command=lambda: self.search_var.set(""))
        btn_clear.pack(side=tk.RIGHT)

        # Treeview (Package Listing)
        tree_frame = ttk.Frame(left_panel)
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree = ttk.Treeview(tree_frame, columns=("Name", "Author"), show="headings", yscrollcommand=scrollbar.set)
        self.tree.heading("Name", text="Package Name")
        self.tree.heading("Author", text="Author")
        self.tree.column("Name", width=120, anchor=tk.W)
        self.tree.column("Author", width=100, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.tree.yview)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        # 3. Right Panel: Detail Editor Form
        self.right_panel = ttk.LabelFrame(paned_window, text="Package Editor", padding=15)
        paned_window.add(self.right_panel, weight=1)

        # Form fields
        self.field_vars = {}
        fields = [
            ("app-name", "name", "Unique system package name (e.g. ollama)"),
            ("author", "author", "Developer name, organization, or publisher"),
            ("git-url", "git_url", "Project git repository URL"),
            ("instruct-url", "instruct_url", "GitHub Raw URL hosting the .instruct file")
        ]

        for i, (label_text, var_key, tooltip) in enumerate(fields):
            lbl = ttk.Label(self.right_panel, text=f"{label_text}:", font=("Helvetica", 10, "bold"))
            lbl.grid(row=i*2, column=0, sticky=tk.W, pady=(5, 2))
            
            # Subtitle/tooltip label
            sub_lbl = ttk.Label(self.right_panel, text=tooltip, font=("Helvetica", 8, "italic"), foreground="#6b7280")
            sub_lbl.grid(row=i*2+1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
            
            var = tk.StringVar()
            entry = ttk.Entry(self.right_panel, textvariable=var)
            entry.grid(row=i*2, column=1, sticky=tk.EW, padx=(10, 0), pady=(5, 2))
            self.field_vars[var_key] = var
            
        self.right_panel.grid_columnconfigure(1, weight=1)

        # Description Field (Multi-line text box)
        desc_row_start = len(fields) * 2
        lbl_desc = ttk.Label(self.right_panel, text="description:", font=("Helvetica", 10, "bold"))
        lbl_desc.grid(row=desc_row_start, column=0, sticky=tk.W, pady=(10, 2))
        
        self.txt_desc = tk.Text(self.right_panel, height=4, font=("Helvetica", 10), borderwidth=1, relief="solid")
        self.txt_desc.grid(row=desc_row_start+1, column=0, columnspan=2, sticky=tk.NSEW, pady=(0, 10))
        self.right_panel.grid_rowconfigure(desc_row_start+1, weight=1)

        # Editor Buttons Bar
        btn_frame = ttk.Frame(self.right_panel)
        btn_frame.grid(row=desc_row_start+2, column=0, columnspan=2, sticky=tk.EW, pady=(10, 0))

        self.btn_new_entry = ttk.Button(btn_frame, text="Add New", command=self.clear_editor)
        self.btn_new_entry.pack(side=tk.LEFT, padx=5)

        self.btn_save = ttk.Button(btn_frame, text="Save / Update", style="Accent.TButton", command=self.save_entry)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.btn_delete = ttk.Button(btn_frame, text="Delete Package", command=self.delete_entry)
        self.btn_delete.pack(side=tk.RIGHT, padx=5)

        # 4. Status Bar & Informative Footer
        footer = ttk.Frame(self.root, padding=5, relief=tk.SUNKEN)
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        
        lbl_info = ttk.Label(footer, text="💡 Tip: Make sure to commit and push changes back to AstroMeYT/OSI repo to sync globally.", font=("Helvetica", 9, "italic"))
        lbl_info.pack(side=tk.LEFT)
        
        btn_help = ttk.Button(footer, text="Git Sync Steps", width=15, command=self.show_git_help)
        btn_help.pack(side=tk.RIGHT)

        # Disable fields initially
        self.toggle_editor_state(tk.DISABLED)

    def toggle_editor_state(self, state):
        for child in self.right_panel.winfo_children():
            if isinstance(child, (ttk.Entry, tk.Text, ttk.Button)) or child.winfo_class() == "TFrame":
                # Handle frames
                if child.winfo_class() == "TFrame":
                    for sub in child.winfo_children():
                        sub.config(state=state)
                else:
                    child.config(state=state)
        # Always allow "New Entry" button if database is connected
        if self.db_path:
            self.btn_new_entry.config(state=tk.NORMAL)

    def load_database(self, filepath):
        try:
            conn = sqlite3.connect(filepath)
            cursor = conn.cursor()
            # Ensure the table exist matches osi.sh's setup
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS packages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, 
                    name TEXT UNIQUE, 
                    author TEXT, 
                    git_url TEXT, 
                    instruct_url TEXT, 
                    description TEXT
                );
            """)
            conn.commit()
            conn.close()
            
            self.db_path = filepath
            self.db_label.config(text=f"Database: {os.path.basename(filepath)}")
            self.toggle_editor_state(tk.NORMAL)
            self.refresh_list()
            self.clear_editor()
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load or initialize the database:\n{e}")

    def open_db_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Open packages.db Database",
            filetypes=[("SQLite Databases", "*.db *.sqlite"), ("All Files", "*.*")]
        )
        if filepath:
            self.load_database(filepath)

    def create_db_dialog(self):
        filepath = filedialog.asksaveasfilename(
            title="Create New packages.db",
            initialfile="packages.db",
            filetypes=[("SQLite Databases", "*.db"), ("All Files", "*.*")]
        )
        if filepath:
            self.load_database(filepath)

    def refresh_list(self):
        if not self.db_path:
            return
            
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        search_query = self.search_var.get().strip()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if search_query:
                cursor.execute("""
                    SELECT id, name, author FROM packages 
                    WHERE name LIKE ? OR description LIKE ? OR author LIKE ?
                """, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
            else:
                cursor.execute("SELECT id, name, author FROM packages ORDER BY name ASC")
                
            rows = cursor.fetchall()
            for row in rows:
                self.tree.insert("", tk.END, iid=row[0], values=(row[1], row[2]))
                
            conn.close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to query database:\n{e}")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        self.selected_item_id = selected_items[0]
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name, author, git_url, instruct_url, description FROM packages WHERE id = ?", (self.selected_item_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                self.field_vars["name"].set(row[0] if row[0] else "")
                self.field_vars["author"].set(row[1] if row[1] else "")
                self.field_vars["git_url"].set(row[2] if row[2] else "")
                self.field_vars["instruct_url"].set(row[3] if row[3] else "")
                
                self.txt_desc.delete("1.0", tk.END)
                self.txt_desc.insert("1.0", row[4] if row[4] else "")
                
        except Exception as e:
            messagebox.showerror("Error", f"Could not pull package details:\n{e}")

    def clear_editor(self):
        self.selected_item_id = None
        self.tree.selection_remove(self.tree.selection())
        for var in self.field_vars.values():
            var.set("")
        self.txt_desc.delete("1.0", tk.END)

    def save_entry(self):
        if not self.db_path:
            messagebox.showwarning("Warning", "No database file active. Please load or create one first.")
            return
            
        # Collect & sanitize input data
        p_name = self.field_vars["name"].get().strip().lower() # Names are clean and lowercase
        p_author = self.field_vars["author"].get().strip()
        p_git = self.field_vars["git_url"].get().strip()
        p_instruct = self.field_vars["instruct_url"].get().strip()
        p_desc = self.txt_desc.get("1.0", tk.END).strip()
        
        if not p_name:
            messagebox.showerror("Validation Error", "The 'app-name' field is required.")
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if self.selected_item_id is not None:
                # Update existing row
                cursor.execute("""
                    UPDATE packages 
                    SET name=?, author=?, git_url=?, instruct_url=?, description=?
                    WHERE id=?
                """, (p_name, p_author, p_git, p_instruct, p_desc, self.selected_item_id))
                messagebox.showinfo("Success", f"Package '{p_name}' updated successfully.")
            else:
                # Check for uniqueness manually to present clean warning
                cursor.execute("SELECT id FROM packages WHERE name = ?", (p_name,))
                if cursor.fetchone():
                    messagebox.showerror("Validation Error", f"A package with the name '{p_name}' already exists in this database.")
                    conn.close()
                    return
                
                # Insert dynamic row
                cursor.execute("""
                    INSERT INTO packages (name, author, git_url, instruct_url, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (p_name, p_author, p_git, p_instruct, p_desc))
                messagebox.showinfo("Success", f"Package '{p_name}' added to database.")
                
            conn.commit()
            conn.close()
            
            self.refresh_list()
            self.clear_editor()
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Could not perform save transaction:\n{e}")

    def delete_entry(self):
        if not self.selected_item_id:
            messagebox.showwarning("Warning", "Please select a package from the left-hand column to delete.")
            return
            
        p_name = self.field_vars["name"].get()
        if messagebox.askyesno("Confirm Deletion", f"Are you absolutely sure you want to permanently delete '{p_name}'?"):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM packages WHERE id = ?", (self.selected_item_id,))
                conn.commit()
                conn.close()
                
                self.refresh_list()
                self.clear_editor()
                messagebox.showinfo("Deleted", "Package removed successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to execute package deletion:\n{e}")

    def show_git_help(self):
        help_window = tk.Toplevel(self.root)
        help_window.title("Publish Changes to GitHub")
        help_window.geometry("600x420")
        help_window.transient(self.root)
        
        txt = tk.Text(help_window, wrap=tk.WORD, font=("Helvetica", 10), padx=10, pady=10)
        txt.pack(fill=tk.BOTH, expand=True)
        
        instructions = """🚀 How to publish packages.db updates to AstroMeYT/OSI:

Step 1: Save the changes using this application. Make sure the file matches the name: packages.db

Step 2: Copy your edited 'packages.db' to your local git repository.

Step 3: Run the following terminal commands to push the updates to GitHub:

   git add packages.db
   git commit -m "Update packages database: added/modified packages"
   git push origin main

Step 4: Verify your raw repository URL in osi.sh matches standard fetch specifications:
https://raw.githubusercontent.com/AstroMeYT/OSI/main/packages.db

Your OSI package manager automatically fetches this updated database next time 'osi.sh' is run!
"""
        txt.insert("1.0", instructions)
        txt.config(state=tk.DISABLED)
        
        btn_close = ttk.Button(help_window, text="Close Window", command=help_window.destroy)
        btn_close.pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = OSIDatabaseManager(root)
    root.mainloop()