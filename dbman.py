#!/usr/bin/env python3
import os
import json
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
        self.data = []
        
        # Apply Styles
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.setup_styles()
        
        # Build UI layout
        self.create_widgets()
        
        # Try auto-detecting cache DB as a convenience
        default_db = os.path.expanduser("~/.cache/osi/packages.json")
        if os.path.exists(default_db):
            if messagebox.askyesno("Load Default DB", f"Detected existing local OSI database at:\n{default_db}\n\nWould you like to open it?"):
                self.load_database(default_db)

    def setup_styles(self):
        # Premium/Modern color scheme
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
        # 1. Top Control Bar
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X, side=tk.TOP)
        
        self.db_label = ttk.Label(top_frame, text="Database: No file loaded", font=("Helvetica", 10, "italic"), foreground="#4b5563")
        self.db_label.pack(side=tk.LEFT, padx=5)
        
        btn_open = ttk.Button(top_frame, text="Open JSON DB", command=self.open_db_dialog)
        btn_open.pack(side=tk.RIGHT, padx=5)
        
        btn_new = ttk.Button(top_frame, text="Create New DB", command=self.create_db_dialog)
        btn_new.pack(side=tk.RIGHT, padx=5)

        # Main Workspace Split Pane
        paned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # 2. Left Panel: Treeview / Package List
        left_panel = ttk.Frame(paned_window, padding=5)
        paned_window.add(left_panel, weight=1)

        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=2)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.refresh_list())
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        btn_clear = ttk.Button(search_frame, text="Clear", width=6, command=lambda: self.search_var.set(""))
        btn_clear.pack(side=tk.RIGHT)

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
            
            sub_lbl = ttk.Label(self.right_panel, text=tooltip, font=("Helvetica", 8, "italic"), foreground="#6b7280")
            sub_lbl.grid(row=i*2+1, column=0, columnspan=2, sticky=tk.W, pady=(0, 5))
            
            var = tk.StringVar()
            entry = ttk.Entry(self.right_panel, textvariable=var)
            entry.grid(row=i*2, column=1, sticky=tk.EW, padx=(10, 0), pady=(5, 2))
            self.field_vars[var_key] = var
            
        self.right_panel.grid_columnconfigure(1, weight=1)

        # Description Field
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

        self.toggle_editor_state(tk.DISABLED)

    def toggle_editor_state(self, state):
        for child in self.right_panel.winfo_children():
            if isinstance(child, (ttk.Entry, tk.Text, ttk.Button)) or child.winfo_class() == "TFrame":
                if child.winfo_class() == "TFrame":
                    for sub in child.winfo_children():
                        sub.config(state=state)
                else:
                    child.config(state=state)
        if self.db_path:
            self.btn_new_entry.config(state=tk.NORMAL)

    def load_database(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if not content:
                    self.data = []
                else:
                    self.data = json.loads(content)
            
            # Sort array alphabetically by name on load
            self.data = sorted(self.data, key=lambda k: k.get('name', ''))
            
            self.db_path = filepath
            self.db_label.config(text=f"Database: {os.path.basename(filepath)}")
            self.toggle_editor_state(tk.NORMAL)
            self.refresh_list()
            self.clear_editor()
            
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to load or parse JSON file:\n{e}")

    def open_db_dialog(self):
        filepath = filedialog.askopenfilename(
            title="Open packages.json Database",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            self.load_database(filepath)

    def create_db_dialog(self):
        filepath = filedialog.asksaveasfilename(
            title="Create New packages.json",
            initialfile="packages.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if filepath:
            try:
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                self.load_database(filepath)
            except Exception as e:
                messagebox.showerror("Error", f"Could not create file: {e}")

    def refresh_list(self):
        if not self.db_path:
            return
            
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        search_query = self.search_var.get().strip().lower()
        
        for pkg in self.data:
            match = False
            if search_query:
                # Check search query against name, description, author
                if search_query in pkg.get('name', '').lower() or \
                   search_query in pkg.get('description', '').lower() or \
                   search_query in pkg.get('author', '').lower():
                    match = True
            else:
                match = True
                
            if match:
                self.tree.insert("", tk.END, iid=pkg['name'], values=(pkg.get('name', ''), pkg.get('author', '')))

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
            
        self.selected_item_id = selected_items[0] # Treeview item ID is the unique package name
        
        # Find item in memory
        selected_pkg = next((item for item in self.data if item["name"] == self.selected_item_id), None)
        
        if selected_pkg:
            self.field_vars["name"].set(selected_pkg.get("name", ""))
            self.field_vars["author"].set(selected_pkg.get("author", ""))
            self.field_vars["git_url"].set(selected_pkg.get("git_url", ""))
            self.field_vars["instruct_url"].set(selected_pkg.get("instruct_url", ""))
            
            self.txt_desc.delete("1.0", tk.END)
            self.txt_desc.insert("1.0", selected_pkg.get("description", ""))

    def clear_editor(self):
        self.selected_item_id = None
        if self.tree.selection():
            self.tree.selection_remove(self.tree.selection())
        for var in self.field_vars.values():
            var.set("")
        self.txt_desc.delete("1.0", tk.END)

    def write_json_db(self):
        # Keeps formatting clean for Github merges (4 spaces)
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=4)

    def save_entry(self):
        if not self.db_path:
            messagebox.showwarning("Warning", "No database file active.")
            return
            
        p_name = self.field_vars["name"].get().strip().lower()
        p_author = self.field_vars["author"].get().strip()
        p_git = self.field_vars["git_url"].get().strip()
        p_instruct = self.field_vars["instruct_url"].get().strip()
        p_desc = self.txt_desc.get("1.0", tk.END).strip()
        
        if not p_name:
            messagebox.showerror("Validation Error", "The 'app-name' field is required.")
            return

        try:
            if self.selected_item_id is not None:
                # Check for uniqueness if the name was altered
                if self.selected_item_id != p_name and any(p["name"] == p_name for p in self.data):
                    messagebox.showerror("Error", f"A package named '{p_name}' already exists.")
                    return
                
                # Update existing row
                for pkg in self.data:
                    if pkg["name"] == self.selected_item_id:
                        pkg["name"] = p_name
                        pkg["author"] = p_author
                        pkg["git_url"] = p_git
                        pkg["instruct_url"] = p_instruct
                        pkg["description"] = p_desc
                        break
                        
                messagebox.showinfo("Success", f"Package '{p_name}' updated successfully.")
            else:
                # Validate uniqueness
                if any(p["name"] == p_name for p in self.data):
                    messagebox.showerror("Error", f"A package named '{p_name}' already exists.")
                    return
                
                # Append new dictionary item
                new_pkg = {
                    "name": p_name,
                    "author": p_author,
                    "git_url": p_git,
                    "instruct_url": p_instruct,
                    "description": p_desc
                }
                self.data.append(new_pkg)
                
                # Keep sorted natively
                self.data = sorted(self.data, key=lambda k: k.get('name', ''))
                
                messagebox.showinfo("Success", f"Package '{p_name}' added to database.")
                
            self.write_json_db()
            
            # Refresh tree view safely
            self.refresh_list()
            self.clear_editor()
            
        except Exception as e:
            messagebox.showerror("File Error", f"Could not perform save transaction:\n{e}")

    def delete_entry(self):
        if not self.selected_item_id:
            messagebox.showwarning("Warning", "Please select a package from the list to delete.")
            return
            
        if messagebox.askyesno("Confirm Deletion", f"Are you absolutely sure you want to permanently delete '{self.selected_item_id}'?"):
            try:
                self.data = [pkg for pkg in self.data if pkg["name"] != self.selected_item_id]
                self.write_json_db()
                
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
        
        instructions = """🚀 How to publish packages.json updates to AstroMeYT/OSI:

Step 1: Save the changes using this application. Make sure the file matches the name: packages.json

Step 2: Copy your edited 'packages.json' to your local git repository.

Step 3: Run the following terminal commands to push the updates to GitHub:

   git add packages.json
   git commit -m "Update packages JSON database"
   git push origin main

Step 4: Verify your raw repository URL in osi.sh matches standard fetch specifications:
https://raw.githubusercontent.com/AstroMeYT/OSI/main/packages.json

Your OSI package manager will automatically fetch this updated JSON database!
"""
        txt.insert("1.0", instructions)
        txt.config(state=tk.DISABLED)
        
        btn_close = ttk.Button(help_window, text="Close Window", command=help_window.destroy)
        btn_close.pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = OSIDatabaseManager(root)
    root.mainloop()