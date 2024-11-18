import json
import os
import random
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter.colorchooser import askcolor
from PIL import Image, ImageTk

DEFAULT_SETTINGS = {"movetype": "Перетаскивание",
                    "gamemode": "Тренировочный",
                    "show_footer": "True",
                    "show_header": "True",
                    "card_back": "dark_back",
                    "canvas_color": "#0d4b34",
                    }


class MenuBar(tk.Frame):
    def __init__(self, parent, invert=False, manager="pack", height=30, bg="#1c1a1a", **kwargs):
        tk.Frame.__init__(self, parent, height=height, bg=bg, **kwargs)
        self.bg = bg



class HoverButton(tk.Button):
    def __init__(self, parent, movetype="Клик", alt=None, ttjustify="left",
                 ttbackground="#ffffe0", ttforeground="black", ttrelief="solid",
                 ttborderwidth=0, ttfont=("Verdana", "8", "normal"), ttlocationinvert=False,
                 ttheightinvert=False, **kwargs):

        self.command = kwargs.pop("command", None)
        self.clickedbackground = kwargs.pop("clickedbackground", "#d9d9d9")
        super().__init__(parent, command=self.command, **kwargs)
        self.default_highlight = self["highlightbackground"]
        self.default_background = self["background"]
        self.default_cursor = self["cursor"]
        self.text = alt
        self.parent = parent
        self.movetype = movetype
        self.on_button = False
        self.tooltip_window = None  
        self.ttjustify = ttjustify
        self.ttbackground = ttbackground
        self.ttforeground = ttforeground
        self.ttrelief = ttrelief
        self.ttborderwidth = ttborderwidth
        self.ttfont = ttfont
        self.ttlocationinvert = ttlocationinvert
        self.ttheightinvert = ttheightinvert
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.bind("<ButtonRelease-1>", self.on_release)

    def on_click(self, event):
        if self["state"] == "normal":
            self.config(bg=self.clickedbackground)

    def on_release(self, event):
        if self["state"] == "normal":
            if self.on_button and self.command:  
                self.command()  
            self.config(bg=self.default_background)

    def on_enter(self, event):
        self.on_button = True
        if self["state"] == "normal":
            self.config(background=self["activebackground"], highlightbackground="black", cursor="hand2")
        self.show_tooltip(event)

    def on_leave(self, event):
        self.on_button = False
        self.config(cursor=self.default_cursor)
        self.reset()
        self.hide_tooltip()

    def run_command(self):
        if self.command:
            self.command()

    def disable(self):
        self.reset()
        self.config(state="disabled")

    def reset(self):
        self.config(background=self.default_background,
                    highlightbackground=self.default_highlight)

    def change_command(self, command):
        self.command = command
        self.config(command=command)

    def show_tooltip(self, event):
        if not self.text:  
            return

        self.tooltip_window = tk.Toplevel(self)
        self.tooltip_window.wm_overrideredirect(True)  
        self.tooltip_window.wm_attributes("-topmost", True)  
        tooltip_label = tk.Label(self.tooltip_window, text=self.text, justify=self.ttjustify,
                                 background=self.ttbackground, foreground=self.ttforeground,
                                 relief=self.ttrelief, borderwidth=self.ttborderwidth,
                                 font=self.ttfont)
        tooltip_label.pack(ipadx=5, ipady=2)
        x = event.x_root + (10 if not self.ttlocationinvert else -10)
        y = event.y_root + (20 if not self.ttheightinvert else -20)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

    def hide_tooltip(self):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class Stopwatch(tk.Label):
    def __init__(self, parent, **kwargs):
        tk.Label.__init__(self, parent, text=f"Время: 00:00", **kwargs)
        self.value = 0
        self.action_id = None
        self.freeze_label = True

    def tick(self):
        self.value += 1
        if self.freeze_label:
            text = f"Время: {self.value // 60:02d}:{self.value % 60:02d}"
            self.configure(text=text)
        if self.value > 0:
            self.action_id = self.after(1000, self.tick)

    def start(self, starting_value=0):
        if self.action_id is not None:
            return

        self.value = starting_value
        self.stop_requested = False
        self.after(1000, self.tick)

    def stop(self):
        self.after_cancel(self.action_id)
        self.value = 0
        self.action_id = None

    def freeze(self, value):
        self.freeze_label = value
        if self.freeze_label:
            text = f"Время: {self.value // 60:02d}:{self.value % 60:02d}"
            self.configure(text=text)


class SolitareGameWindow(tk.Tk):
    def __init__(self, **kwargs):
        tk.Tk.__init__(self, **kwargs)
        self.title("Пасьянс")
        self.minsize(1300, 800)
        solitaire_frame = SolitareGameFrame(self)
        solitaire_frame.pack(expand=True, fill="both")
        self.iconbitmap(os.path.join("assets", "icon.ico"))


class SolitareGameFrame(tk.Frame):
    def __init__(self, parent, **kwargs):
        tk.Frame.__init__(self, parent, **kwargs)
        self.bind_all("<Control-n>", self.new_game)
        self.bind_all("<Control-r>", self.restart_game)
        self.bind_all("<Control-z>", self.undo_move)
        self.bind_all("<Control-y>", self.redo_move)
        self.bind_all("<Control-h>", self.generate_hint)
        self.bind_all("<F5>", self.send_cards_up)
        self.bind_all("<F1>", self.open_settings)
        self.bind_all("<F11>", self.fullscreen)
        self.canvas = tk.Canvas(self, bd=0, highlightthickness=0)
        self.card_drawing_count = 0
        self.cards_on_ace = 0
        self.parent = parent
        self.win_fullscreen = not parent.attributes("-fullscreen")
        self.card_moved_to_ace_by_sender = 0
        self.stock_left = 24
        self.redeals_left = 0
        self.last_active_card = ""
        self.card_stack_list = ""
        self.cards = []
        self.rect_images = []
        self.button_images = []
        self.dict_of_cards = {}
        self.card_back = None
        self.history = []
        self.redo = []
        self.game_started = False
        self.move_flag = False
        self.win = None
        self.load_settings()
        self.load_images()
        self.shuffle_cards()
        self.draw_card_slots()
        self.generate_card_position()
        self.draw_remaining_cards()
        self.create_widgets()

    def load_settings(self):
        settings = json.load(open("assets/settings.json", encoding="utf-8"))
        self.movetype = settings["movetype"]
        self.gamemode = settings["gamemode"]
        self.canvas_hover_time = 300
        self.wait_before_send = 100
        self.show_footer = settings["show_footer"] == "True"
        self.show_header = settings["show_header"] == "True"
        self.canvas.config(bg=settings["canvas_color"])
        self.restart_game_button_enabled = True
        self.undo_last_move_button_enabled = True
        self.redo_last_move_button_enabled = True
        self.hint_button_enabled = True
        self.show_stopwatch = True
        self.starting_points = 0
        self.point_increment = 5
        self.back_of_card_file = os.path.join("assets", settings["card_back"] + ".png")
        self.card_back = settings["card_back"]

        if self.gamemode == "Стандартный":
            self.total_redeals = 3
        else:
            self.total_redeals = "unlimited"
            self.show_stopwatch = False
            self.point_increment = 1
            self.refresh_points_after_game = True


    def create_widgets(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        self.header = header = MenuBar(self, invert=True, manager="grid")
        button_settings = {"movetype": self.movetype, "ttbackground": "#1c1c1b", "ttforeground": "white",
                           "ttfont": ("Verdana", "10", "normal"), "relief": "flat", "bg": "#1c1a1a",
                           "activebackground": "#4f4a4a", "highlightbackground": "#1c1a1a",
                           "clickedbackground": "#2e2b2b"}
        self.new_game_button = new_game_button = HoverButton(
            header, alt="Начать новую игру (Ctrl+N)", command=self.new_game,
            image=self.convert_pictures("new_game.png", main=False), **button_settings)
        self.restart_game_button = restart_game_button = HoverButton(
            header, alt="Перезапустить игру (Ctrl+R)", command=self.restart_game, state="disabled",
            image=self.convert_pictures("restart_game.png", main=False), **button_settings)
        self.undo_last_move_button = undo_last_move_button = HoverButton(
            header, alt="Отменить ход (Ctrl+Z)", command=self.undo_move, state="disabled",
            image=self.convert_pictures("undo.png", main=False), **button_settings)
        self.redo_last_move_button = redo_last_move_button = HoverButton(
            header, alt="Повторить ход (Ctrl+Shift+Z)", command=self.redo_move, state="disabled",
            image=self.convert_pictures("redo.png", main=False), **button_settings)
        self.hint_button = hint_button = HoverButton(
            header, alt="Показать подсказку (Ctrl+H)", command=self.generate_hint,
            image=self.convert_pictures("hint.png", main=False), **button_settings)
        self.send_cards_up_button = send_cards_up_button = HoverButton(
            header, alt="Отправить в базу (F5)", command=self.send_cards_up,
            image=self.convert_pictures("send.png", main=False), **button_settings)
        self.settings_button = settings_button = HoverButton(
            header, alt="Настройки игры (F1)", command=self.open_settings,
            image=self.convert_pictures("settings.png", main=False), **button_settings)
        self.fullscreen_button = fullscreen_button = HoverButton(header, alt="Полноэкранный режим (F11)",
            command=self.fullscreen, image=self.convert_pictures("maximize.png", main=False),
            ttlocationinvert=True, **button_settings)

        header.columnconfigure(12, weight=1)
        new_game_button.grid(row=1, column=0, padx=6, pady=1)
        if self.restart_game_button_enabled:
            restart_game_button.grid(row=1, column=1, padx=6, pady=1)
        if self.undo_last_move_button_enabled:
            undo_last_move_button.grid(row=1, column=2, padx=6, pady=1)
        if self.redo_last_move_button_enabled:
            redo_last_move_button.grid(row=1, column=3, padx=6, pady=1)
        if self.hint_button_enabled:
            hint_button.grid(row=1, column=4, padx=6, pady=1)

        send_cards_up_button.grid(row=1, column=5, padx=6, pady=1)
        settings_button.grid(row=1, column=6, padx=6, pady=1)
        fullscreen_button.grid(row=1, column=12, padx=16, pady=1, sticky="e")

        self.headerless_settings_button = headerless_settings_button = HoverButton(self.canvas,
        movetype=self.movetype, alt="Настройки игры", ttheightinvert=True, ttbackground="#1c1c1b",
        ttforeground="white", ttfont=("Verdana", "10", "normal"),
        bg=self.canvas["bg"], activebackground=self.generate_new_color(self.canvas["bg"]),
        highlightbackground="#0d4b34", clickedbackground=self.generate_new_color(self.canvas["bg"]),
        command=self.open_settings, relief="flat", image=self.convert_pictures("settings.png", main=False))

        if self.show_header:
            header.grid(row=0, column=0, columnspan=100, sticky="ew")
        else:
            self.canvas.rowconfigure(1, weight=1)
            headerless_settings_button.grid(row=1, sticky="sw")
        self.canvas.grid(row=1, column=0, sticky="nsew")
        self.footer = footer = MenuBar(self)
        self.points_label = tk.Label(
            footer, text=f"Очки: {self.starting_points}", fg="white", bg="#1c1a1a")
        self.stopwatch = stopwatch = Stopwatch(
            footer, fg="white", bg="#1c1a1a")
        if self.total_redeals != "unlimited":
            self.redeal_label = tk.Label(footer, text=f"Осталось пересдач: {max(0, self.total_redeals + self.redeals_left - 1)}", fg="white", bg="#1c1a1a")
        else:
            self.redeal_label = tk.Label(
                footer, text="", fg="white", bg="#1c1a1a")
        self.stock_label = tk.Label(
            footer, text=f"Осталось карт:  {self.stock_left}", fg="white", bg="#1c1a1a")

        if self.show_footer:
            footer.grid(row=2, column=0, sticky="ew")

        self.points_label.pack(side="right", padx=6, pady=4)
        if self.show_stopwatch:
            stopwatch.pack(side="right", padx=6, pady=4)

    def open_settings(self, *args):
        if self.move_flag:
            return
        self.settings = settings = Settings(self)
        settings.bind("<<SettingsClose>>", self.continue_settings)

    def fullscreen(self, event=None):
        self.parent.attributes(
            "-fullscreen", not self.parent.attributes("-fullscreen"))

        if self.win_fullscreen:
            self.fullscreen_button.config(
                image=self.convert_pictures("minimize.png", main=False))
            self.win_fullscreen = False
        else:
            self.fullscreen_button.config(
                image=self.convert_pictures("maximize.png", main=False))
            self.win_fullscreen = True

    def continue_settings(self, *args):
        previous_movetype = self.movetype
        self.canvas.tag_unbind("card_below_rect", "<Enter>")
        self.canvas.tag_unbind("rect", "<Enter>")
        self.canvas.tag_unbind("rect", "<Leave>")
        self.canvas.tag_unbind("rect", "<Button-1>")
        self.canvas.delete("rect")
        self.last_active_card = ""
        self.card_stack_list = ""
        self.load_settings()
        self.update_idletasks()
        back_of_card = Image.open(self.back_of_card_file)
        self.back_of_card = (ImageTk.PhotoImage(back_of_card))
        self.canvas.itemconfig("face_down", image=self.back_of_card)
        self.restart_game_button.movetype = self.movetype
        self.undo_last_move_button.movetype = self.movetype
        self.redo_last_move_button.movetype = self.movetype
        self.hint_button.movetype = self.movetype
        self.send_cards_up_button.movetype = self.movetype
        self.new_game_button.movetype = self.movetype
        self.settings_button.movetype = self.movetype
        self.fullscreen_button.movetype = self.movetype
        self.headerless_settings_button.movetype = self.movetype

        if self.restart_game_button_enabled:
            if not self.restart_game_button.winfo_ismapped():
                self.restart_game_button.grid(row=1, column=1, padx=6, pady=1)
        else:
            self.restart_game_button.grid_forget()

        if self.undo_last_move_button_enabled:
            if not self.undo_last_move_button.winfo_ismapped():
                self.undo_last_move_button.grid(
                    row=1, column=2, padx=6, pady=1)
        else:
            self.undo_last_move_button.grid_forget()

        if self.redo_last_move_button_enabled:
            if not self.redo_last_move_button.winfo_ismapped():
                self.redo_last_move_button.grid(
                    row=1, column=3, padx=6, pady=1)
        else:
            self.redo_last_move_button.grid_forget()

        if self.hint_button_enabled:
            if not self.hint_button.winfo_ismapped():
                self.hint_button.grid(row=1, column=4, padx=6, pady=1)
        else:
            self.hint_button.grid_forget()

        self.points_label.pack_forget()
        self.stopwatch.pack_forget()
        self.redeal_label.pack_forget()
        self.stock_label.pack_forget()

        if self.show_footer:
            if not self.footer.winfo_ismapped():
                self.update_idletasks()
                self.footer.grid(row=2, column=0, sticky="ew")
        else:
            self.footer.grid_forget()
        self.points_label["text"] = (f"Очки:  {(self.cards_on_ace * self.point_increment) + self.starting_points}")
        self.points_label.pack(side="right", padx=6, pady=4)
        if self.show_stopwatch:
            self.stopwatch.pack(side="right", padx=6, pady=4)
        if self.total_redeals != "unlimited":
            self.redeal_label.config(text=f"Осталось пересдач:  {max(0, self.total_redeals + self.redeals_left - 1)}")
            if self.game_started:
                self.redeal_label.pack(side="left", padx=6, pady=4)
        if self.game_started:
            self.stock_label.pack(side="left", padx=6, pady=4)

        self.headerless_settings_button.grid_forget()
        if self.show_header:
            if not self.header.winfo_ismapped():
                self.update_idletasks()
                self.header.grid(row=0, column=0, columnspan=100, sticky="ew")
        else:
            self.header.grid_forget()
            self.canvas.rowconfigure(1, weight=1)
            self.headerless_settings_button.config(bg=self.canvas["bg"])
            self.headerless_settings_button.default_background = self.canvas["bg"]
            self.headerless_settings_button["activebackground"] = self.generate_new_color(
                self.canvas["bg"])
            self.canvas.update_idletasks()
            self.headerless_settings_button.grid(row=1, sticky="sw")

        if self.movetype != previous_movetype:
            for card in self.canvas.find_withtag("face_up"):
                card_tag = self.canvas.gettags(card)[0]
                self.canvas.tag_unbind(card_tag,  "<Button-1>")
                self.canvas.tag_unbind(card_tag, "<Button1-Motion>")
                self.canvas.tag_unbind(card_tag, "<ButtonRelease-1>")
                self.canvas.tag_unbind(card_tag, "<Enter>")
                self.canvas.tag_unbind(card_tag, "<Leave>")

                if self.movetype == "Клик":
                    self.canvas.tag_bind(
                        card_tag, "<Button-1>", self.card_onclick)
                else:
                    self.canvas.tag_bind(
                        card_tag, "<Button-1>", self.end_onclick)
                    self.canvas.tag_bind(
                        card_tag, "<Button1-Motion>", self.move_card)
                    self.canvas.tag_bind(
                        card_tag, "<ButtonRelease-1>", self.drop_card)
                    self.canvas.tag_bind(
                        card_tag, "<Enter>", self.on_draggable_card)
                    self.canvas.tag_bind(
                        card_tag, "<Leave>", self.leave_draggable_card)

            for card in self.canvas.find_overlapping(*self.canvas.bbox("empty_cardstack_slot")):
                card_tag = self.canvas.gettags(card)[0]
                if card_tag == "empty_cardstack_slot":
                    continue
                else:
                    self.canvas.tag_unbind(card_tag, "<Enter>")
                    self.canvas.tag_unbind(card_tag, "<Leave>")

            self.canvas.tag_unbind("empty_slot", "<Enter>")
            self.canvas.tag_unbind("empty_ace_slot", "<Enter>")
            self.canvas.tag_unbind("empty_cardstack_slot", "<Enter>")
            self.canvas.tag_unbind("empty_slot", "<Leave>")
            self.canvas.tag_unbind("empty_ace_slot", "<Leave>")
            self.canvas.tag_unbind("empty_cardstack_slot", "<Leave>")
            self.canvas.tag_unbind("empty_slot", "<Button-1>")
            self.canvas.tag_unbind("empty_ace_slot", "<Button-1>")
            self.canvas.tag_unbind("empty_cardstack_slot", "<Button-1>")
            self.canvas.tag_unbind("empty_slot", "<Button-1>")
            self.canvas.tag_unbind("empty_ace_slot", "<Button-1>")
            self.canvas.tag_unbind("empty_cardstack_slot", "<Button-1>")
            self.canvas.tag_unbind("empty_slot", "<Button-1>")
            self.canvas.tag_unbind("empty_ace_slot", "<Button-1>")
            self.canvas.tag_unbind("empty_slot", "<Button1-Motion>")
            self.canvas.tag_unbind("empty_slot", "<ButtonRelease-1>")
            self.canvas.tag_unbind("empty_ace_slot", "<Button1-Motion>")
            self.canvas.tag_unbind("empty_ace_slot", "<ButtonRelease-1>")
            self.canvas.tag_unbind("empty_cardstack_slot", "<Button-1>")

            if self.movetype == "Клик":
                self.canvas.tag_bind(
                    "empty_slot", "<Button-1>", self.card_onclick)
                self.canvas.tag_bind(
                    "empty_ace_slot", "<Button-1>", self.card_onclick)
                self.canvas.tag_bind("empty_cardstack_slot",
                                     "<Button-1>", self.refill_card_stack)
            else:
                self.canvas.tag_bind(
                    "empty_slot", "<Button-1>", self.end_onclick)
                self.canvas.tag_bind(
                    "empty_ace_slot", "<Button-1>", self.end_onclick)
                self.canvas.tag_bind(
                    "empty_slot", "<Button1-Motion>", self.move_card)
                self.canvas.tag_bind(
                    "empty_slot", "<ButtonRelease-1>", self.drop_card)
                self.canvas.tag_bind(
                    "empty_ace_slot", "<Button1-Motion>", self.move_card)
                self.canvas.tag_bind(
                    "empty_ace_slot", "<ButtonRelease-1>", self.drop_card)
                self.canvas.tag_bind("empty_cardstack_slot",
                                     "<Button-1>", self.refill_card_stack)
        ret = False
        
                
    def generate_new_color(self, color):
        rgb = list(self.hex_to_rgb(color))
        if rgb[0] > 200:
            rgb[0] = round(((rgb[0])) * 1 / 2)
        else:
            rgb[0] = round(min(255, 10 + rgb[0] * 2))
        if rgb[1] > 130:
            rgb[1] = round((rgb[1]) * 1 / 2)
        else:
            rgb[1] = round(min(255, 10 + rgb[1] * 2))
        if rgb[2] > 130:
            rgb[2] = round((rgb[2]) * 1 / 2)
        else:
            rgb[2] = round(min(255, 10 + rgb[2] * 2))
        return self.rgb_to_hex(*rgb)

    def hex_to_rgb(self, color):
        value = color.lstrip("#")
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    def rgb_to_hex(self, red, green, blue):
        return f"#{red:02x}{green:02x}{blue:02x}"

    def load_images(self):
        suits = ["clubs", "diamonds", "spades", "hearts"]
        ranks = ["ace", "2", "3", "4", "5", "6", "7",
                 "8", "9", "10", "jack", "queen", "king"]

        for suit in suits:
            for rank in ranks:
                name_of_image = os.path.join("assets", "cards", f"{rank}_of_{suit}.png")
                image = Image.open(name_of_image)
                self.cards.append(f"{rank}_of_{suit}")
                self.dict_of_cards[(f"{rank}_of_{suit}")] = (ImageTk.PhotoImage(image))
        back_of_card = Image.open(self.back_of_card_file)
        self.back_of_card = (ImageTk.PhotoImage(back_of_card))

    def shuffle_cards(self):
        random.shuffle(self.cards)

    def generate_card_position(self):
        rows = 7
        column = 0

        for i in range(rows):
            for e in range(column):
                self.draw_down_cards((i + 1), (e + 1))
            column += 1
            self.draw_up_cards((i + 1), (column))

    def draw_up_cards(self, row, col):
        card_tag = str(self.cards[self.card_drawing_count])
        card_image = self.dict_of_cards[self.cards[self.card_drawing_count]]
        self.canvas.create_image(165 + row * 130, col * 20 + 250, image=card_image,
                                 tag=(card_tag, "face_up"), anchor=tk.NW)
        if self.movetype == "Клик":
            self.canvas.tag_bind(card_tag, "<Button-1>", self.card_onclick)
        else:
            self.canvas.tag_bind(card_tag, "<Button-1>", self.end_onclick)
            self.canvas.tag_bind(card_tag, "<Button1-Motion>", self.move_card)
            self.canvas.tag_bind(card_tag, "<ButtonRelease-1>", self.drop_card)
            self.canvas.tag_bind(card_tag, "<Enter>", self.on_draggable_card)
            self.canvas.tag_bind(card_tag, "<Leave>", self.leave_draggable_card)
        self.card_drawing_count += 1

    def draw_down_cards(self, row, col):
        card_tag = str(self.cards[self.card_drawing_count])
        self.canvas.tag_unbind(card_tag,  "<Button-1>")
        self.canvas.tag_unbind(card_tag, "<Button1-Motion>")
        self.canvas.tag_unbind(card_tag, "<ButtonRelease-1>")
        self.canvas.tag_unbind(card_tag, "<Enter>")
        self.canvas.tag_unbind(card_tag, "<Leave>")
        self.canvas.create_image(165 + row * 130, col * 20 + 250, image=self.back_of_card,
                                 tag=(card_tag, "face_down"), anchor=tk.NW)
        self.card_drawing_count += 1

    def draw_remaining_cards(self):
        remaining_cards = 52 - self.card_drawing_count
        for i in range(remaining_cards):
            card_tag = str(self.cards[self.card_drawing_count])
            self.canvas.tag_unbind(card_tag, "<Enter>")
            self.canvas.tag_unbind(card_tag, "<Leave>")
            self.canvas.create_image(51, 50, image=self.back_of_card,
                                     tag=(card_tag, "face_down"), anchor=tk.NW)
            self.canvas.tag_bind(card_tag, "<Button-1>", self.stack_onclick)
            self.card_drawing_count += 1

    def rounded_rectangle(self, x1, y1, x2, y2, r=18, **kwargs):
        points = (x1 + r, y1, x1 + r, y1, x2 - r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
                  x2, y1 + r, x2, y2 - r, x2, y2 - r, x2, y2, x2 - r, y2, x2 - r, y2,
                  x1 + r, y2, x1 + r, y2, x1, y2, x1, y2 - r, x1, y2 - r, x1, y1 + r, x1, y1 + r, x1, y1)
        return self.canvas.create_polygon(points, **kwargs, smooth=True)

    def convert_pictures(self, url, main=True):
        picture = Image.open(os.path.join("assets", url))
        picture = (ImageTk.PhotoImage(picture))
        if main:
            self.canvas.images.append(picture)
        else:
            self.button_images.append(picture)
        return picture                
        
    def draw_card_slots(self):
        self.aces_moved = False
        self.canvas.images = list()
        positions_of_main_rects = [
                (295, 250), (425, 250), (555, 250), (685, 250), (815, 250), (945, 250), (1075, 250)]

        self.empty_slot = empty_slot = self.convert_pictures("empty_slot.png")
        for item in positions_of_main_rects:
            self.canvas.create_image(
                *item, image=empty_slot, tag=("empty_slot"), anchor=tk.NW)

        self.canvas.create_image(525, 50, image=self.convert_pictures("ace_of_spades_slot.png"),
                                 tag=("spades", "empty_ace_slot"), anchor=tk.NW)
        self.canvas.create_image(665, 50, image=self.convert_pictures("ace_of_hearts_slot.png"),
                                 tag=("hearts", "empty_ace_slot"), anchor=tk.NW)
        self.canvas.create_image(805, 50, image=self.convert_pictures("ace_of_clubs_slot.png"),
                                 tag=("clubs", "empty_ace_slot"), anchor=tk.NW)
        self.canvas.create_image(945, 50, image=self.convert_pictures("ace_of_diamonds_slot.png"),
                                 tag=("diamonds", "empty_ace_slot"), anchor=tk.NW)

        self.rounded_rectangle(52, 52, 149, 178, width=3, fill="#0f412e", outline="#0d7c53",
                               tag="empty_cardstack_slot")
        self.rounded_rectangle(166, 52, 259, 178, width=3, fill="#0f412e", outline="#0d7c53",
                               tag="empty_cardstack_slotb")

        if self.movetype == "Клик":
            self.canvas.tag_bind("empty_slot", "<Button-1>", self.card_onclick)
            self.canvas.tag_bind("empty_ace_slot", "<Button-1>", self.card_onclick)
            self.canvas.tag_bind("empty_cardstack_slot","<Button-1>", self.refill_card_stack)
        else:
            self.canvas.tag_bind("empty_slot", "<Button-1>", self.end_onclick)
            self.canvas.tag_bind("empty_ace_slot", "<Button-1>", self.end_onclick)
            self.canvas.tag_bind("empty_slot", "<Button1-Motion>", self.move_card)
            self.canvas.tag_bind("empty_slot", "<ButtonRelease-1>", self.drop_card)
            self.canvas.tag_bind("empty_ace_slot", "<Button1-Motion>", self.move_card)
            self.canvas.tag_bind("empty_ace_slot", "<ButtonRelease-1>", self.drop_card)
            self.canvas.tag_bind("empty_cardstack_slot","<Button-1>", self.refill_card_stack)
        self.canvas.bind("<Button-1>", self.on_background)
        

    def on_background(self, event):
        if (self.canvas.find_overlapping(event.x - 5, event.y - 5, event.x + 5, event.y + 5)) == ():
            self.canvas.delete("rect")
            self.last_active_card = ""
            self.card_stack_list = ""

    def create_rectangle(self, x1, y1, x2, y2, tag="rect", **kwargs):
        if "alpha" in kwargs:
            alpha = int(kwargs.pop("alpha") * 255)
            fill = kwargs.pop("fill")
            fill = self.winfo_rgb(fill) + (alpha,)
            image = Image.new("RGBA", (x2 - x1, y2 - y1), fill)
            self.rect_images.append(ImageTk.PhotoImage(image))
            self.canvas.create_image(x1, y1, image=self.rect_images[-1], anchor="nw", tag=tag)
        else:
            self.canvas.create_rectangle(x1, y1, x2, y2, tag="rect", **kwargs)

    def initiate_game(self):
        self.canvas_item_hover_time = self.canvas_hover_time
        self.restart_game_button.config(state="normal")
        self.redo_last_move_button.config(state="normal")
        try:
            last_move = self.history[-1]
        except:
            self.undo_last_move_button.disable()
            self.restart_game_button.disable()
        try:
            last_move = self.redo[-1]
        except:
            self.redo_last_move_button.disable()
        if self.game_started == False:
            self.stopwatch.start()
            self.game_started = True
            if self.total_redeals != "unlimited":
                self.redeal_label.pack(side="left", padx=6, pady=4)
            self.stock_label.pack(side="left", padx=6, pady=4)
        else:
            self.game_started = True


    def restart_game(self, *args):
        if self.move_flag:
            return
        self.reset_vars()
        self.redraw()

    def new_game(self, *args):
        if self.move_flag:
            return
        self.shuffle_cards()
        self.reset_vars()
        self.redraw()

    def reset_vars(self):
        self.card_drawing_count = 0
        self.cards_on_ace = 0
        self.card_moved_to_ace_by_sender = 0
        self.stock_left = 24
        self.last_active_card = ""
        self.card_stack_list = ""
        self.history = []
        self.redo = []
        self.game_started = False
        self.move_flag = False
        self.redeals_left = 0
        self.canvas_item_hover_time = self.canvas_hover_time

        try:
            self.stopwatch.stop()
            self.stopwatch.config(text=f"Time: 00:00")
        except:
            pass

        self.restart_game_button.disable()
        self.undo_last_move_button.disable()
        self.redo_last_move_button.disable()
        if self.total_redeals != "unlimited":
            self.redeal_label.config(
                text=f"Осталось пересдач: {max(0, self.total_redeals + self.redeals_left - 1)}")
        self.points_label.config(text=f"Очки: {self.starting_points}")
        self.stock_label.config(text=f"Осталось карт:  {self.stock_left}")
        if self.total_redeals != "unlimited":
            self.redeal_label.pack_forget()
        self.stock_label.pack_forget()
        self.canvas.delete("all")

    def redraw(self):
        self.draw_card_slots()
        self.generate_card_position()
        self.draw_remaining_cards()

    def find_available_cards(self):
        face_up_cards = list(reversed(self.canvas.find_withtag("face_up")))
        flipped_cards = []
        positions_of_ace_rects = []
        found_cards = []

        for card in (self.canvas.find_overlapping(*self.canvas.bbox("empty_cardstack_slotb"))):
            if card in face_up_cards:
                face_up_cards.remove(card)
            if "empty" not in str(self.canvas.gettags(card)):
                flipped_cards.append(card)
        if flipped_cards != []:
            del flipped_cards[:-1]
        ace_slots = self.canvas.find_withtag("empty_ace_slot")
        for slot in ace_slots:
            positions_of_ace_rects.append(self.canvas.bbox(slot))
        for position in positions_of_ace_rects:
            for card in self.canvas.find_overlapping(*position):
                if card in face_up_cards:
                    face_up_cards.remove(card)
                found_cards.append(card)
            if found_cards != []:
                flipped_cards.append(found_cards[-1])
            found_cards = []
        flipped_cards.extend(face_up_cards)
        face_up_cards = flipped_cards

        base_slots = self.canvas.find_withtag("empty_slot")
        for slot in base_slots:
            if len(self.canvas.find_overlapping(*self.canvas.bbox(slot))) == 1:
                face_up_cards.append(slot)

        return face_up_cards

    def generate_hint(self, *args):
        if self.move_flag:
            return
        self.initiate_game()
        self.card_stack_list = ""
        self.last_active_card = ""
        self.canvas.delete("rect")
        face_up_cards = self.find_available_cards()
        returnval = False
        for pair in face_up_cards:
            self.canvas.delete("rect")
            card_stack = list(self.canvas.bbox(pair))
            card_stack[1] = (int(card_stack[1])) + 129
            card_stack[3] = (int(card_stack[3])) + 350
            card_stack = tuple(card_stack)
            card_stack = list(self.canvas.find_overlapping(*card_stack))
            for pairr in self.card_stack_list:
                card_tag = self.canvas.gettags(pairr)
                if ("ace_slot" in str(card_tag)) or ("cardstack" in str(card_tag)):
                    to_be_card_stack_list = card_stack[-1]
                    card_stack = []
                    card_stack.append(to_be_card_stack_list)
                    break
            last_active_card_bbox_list = list(self.canvas.bbox(pair))
            last_active_card_bbox_list[1] = int(last_active_card_bbox_list[1]) + 60
            last_active_card_bbox_list[3] = int(last_active_card_bbox_list[3]) - 25
            last_active_card_bbox_list = tuple(last_active_card_bbox_list)
            card_a_bbox = self.canvas.bbox(pair)
            first_item = list(self.canvas.bbox(self.canvas.find_withtag(card_stack[0])))
            last_item = list(self.canvas.bbox(self.canvas.find_withtag(card_stack[-1])))
            tl = first_item[0]
            tr = first_item[1]
            bl = last_item[2]
            br = last_item[3]
            positionsb = []
            positionsb.append(tl)
            positionsb.append(tr)
            positionsb.append(bl)
            positionsb.append(br)
            card_a_bbox = tuple(positionsb)

            if ("empty_ace_slot" not in str(self.canvas.gettags(pair)) and "empty_slot" not in str(self.canvas.gettags(pair))):
                last_active_card = str(self.canvas.gettags(pair)).replace(")", "").replace(
                    "('", "").replace("', 'face_down'", "").replace("', 'face_up'", "")
            else:
                continue
            for card in face_up_cards:
                card_tag = str(self.canvas.gettags(card))
                current_image = self.canvas.find_withtag(card)
                current_image_tags = self.canvas.gettags(current_image)
                current_image_bbox = self.canvas.bbox(current_image)

                bbox_list = list(current_image_bbox)
                card_b_bbox = self.canvas.bbox(card)
                current_image_overlapping = self.canvas.find_overlapping(*bbox_list)
                tag_a = str(current_image_tags).replace(", 'current')", "").replace(")", "").replace(
                    "('", "").replace("', 'face_down'", "").replace("', 'face_up'", "")

                overlapping = False
                ace_slot = False
                if ("empty_ace_slot" not in str(current_image_tags)) and ("empty_slot" not in str(current_image_tags)):
                    csl = list(self.canvas.bbox(tag_a))
                    csl[1] = (int(csl[1])) + 135
                    csl[3] = (int(csl[3])) + 20
                    csl = tuple(csl)
                    csl = list(self.canvas.find_overlapping(*csl))
                    for card in csl:
                        if card in card_stack:
                            continue
                        elif "empty_cardstack_slot" in str(self.canvas.gettags(card)):
                            overlapping = True
                            break
                        elif "face_up" in self.canvas.gettags(card):
                            overlapping = True
                            break

                if "empty_slot" in str(current_image_tags):
                    if "king" in card_stack:
                        for card in current_image_overlapping:
                            if card in card_stack:
                                continue
                            elif "face" in str(self.canvas.gettags(card)):
                                overlapping = True
                                break

                for item in current_image_overlapping:
                    if "empty_ace_slot" in self.canvas.gettags(self.canvas.find_withtag(item)):
                        ace_slot = True
                for item in self.canvas.find_overlapping(*self.canvas.bbox(pair)):
                    if "empty_ace_slot" in self.canvas.gettags(self.canvas.find_withtag(item)):
                        ace_slot = True

                for item in current_image_overlapping:
                    if last_active_card in self.canvas.gettags(self.canvas.find_withtag(item)):
                        overlapping = True

                if ace_slot:
                    try:
                        for item in card_stack:
                            self.canvas.tag_raise(item)
                        item = self.canvas.find_overlapping(
                            *self.canvas.bbox(self.canvas.find_above(last_active_card)))
                        overlapping = True
                    except:
                        pass
                else:
                    try:
                        below_last = self.canvas.find_overlapping(
                            *self.canvas.bbox(last_active_card))
                    except:
                        continue
                    last_card_index_in_below = below_last.index(
                        list(self.canvas.find_withtag(last_active_card))[0])
                    below_last = str(self.canvas.gettags(
                        below_last[last_card_index_in_below-1]))
                    last_overlapping = self.canvas.find_overlapping(
                        *self.canvas.bbox(last_active_card))
                    if "king" in last_active_card:
                        if ("empty_slot" in below_last):
                            overlapping = True
                    over_cardstack = False
                    for card in current_image_overlapping:
                        if "empty_cardstack_slot" in str(self.canvas.gettags(card)):
                            over_cardstack = True
                            break
                    if not over_cardstack:
                        over_cardstack = False
                        for card in last_overlapping:
                            if "empty_cardstack_slot" in str(self.canvas.gettags(card)):
                                over_cardstack = True
                        if not over_cardstack:
                            if "face_up" in below_last:
                                overlapping = True
                    else:
                        overlapping = True
                if ("ace" not in last_active_card and "empty_ace_slot" in current_image_tags):
                    continue
                elif ("king" not in last_active_card and "empty_slot" in current_image_tags):
                    continue
                elif "empty_slot" in last_active_card:
                    continue
                elif overlapping:
                    continue
                elif "king" in last_active_card and "empty_slot" in current_image_tags:
                    returnval = True
                    break
                elif self.check_move_validity(tag_a, last_active_card, ace_slot):
                    returnval = True
                    break
                else:
                    continue
            if returnval:
                break

        if returnval:
            self.create_rectangle(*card_b_bbox, fill="green", alpha=.5)
            self.create_rectangle(*card_a_bbox, fill="green", alpha=.5)

            if self.movetype == "Клик":
                self.canvas.tag_bind("rect", "<Button-1>", self.click_on_hint_rect)
            else:
                self.canvas.tag_bind("rect", "<Enter>", self.enter_on_hint_rect)
        else:
            ret = False
            if self.total_redeals != "unlimited":
                if self.stock_left == 0 and (self.total_redeals + self.redeals_left - 1) <= 0:
                    ret = True
                    messagebox.showinfo(
                        title="Нет доступных ходов", message="Не могу ничего посоветовать.\nЛучше начать новую игру.")
            if not ret:
                cards = False
                for card in self.canvas.find_overlapping(*self.canvas.bbox("empty_cardstack_slotb")):
                    if "empty_cardstack_slotb" in self.canvas.gettags(card):
                        continue
                    cards = True
                    break
                if not cards:
                    for card in self.canvas.find_overlapping(*self.canvas.bbox("empty_cardstack_slot")):
                        if "empty_cardstack_slot" in self.canvas.gettags(card):
                            continue
                        cards = True
                        break
                if not cards:
                    ret = True
                    messagebox.showinfo(
                        title="Хммм", message="Не могу подсказать ход.\nЛучше начать игру заново.")

            if not ret:
                self.create_rectangle(
                    *self.canvas.bbox("empty_cardstack_slot"), fill="purple", alpha=.5)

                if self.movetype == "Клик":
                    self.canvas.tag_bind("rect", "<Button-1>", self.click_on_hint_rect)
                else:
                    self.canvas.tag_bind("rect", "<Button-1>", self.click_on_hint_rect)


    def send_cards_up(self, *args):
        if self.move_flag:
            return
        self.initiate_game()
        self.card_stack_list = ""
        self.last_active_card = ""
        self.canvas.delete("rect")
        self.stopwatch.freeze(False)
        face_up_cards = list(reversed(self.canvas.find_withtag("face_up")))
        for card in face_up_cards:
            below_last = self.canvas.find_overlapping(*self.canvas.bbox(card))
            last_card_index_in_below = below_last.index(
                list(self.canvas.find_withtag(card))[0])
            below_last = str(self.canvas.gettags(
                below_last[last_card_index_in_below - 1]))
            if "face_up" in self.canvas.gettags(below_last):
                face_up_cards.remove(card)
        flipped_cards = []
        for card in (self.canvas.find_overlapping(*self.canvas.bbox("empty_cardstack_slotb"))):
            if card in face_up_cards:
                face_up_cards.remove(card)
            if "empty" not in str(self.canvas.gettags(card)):
                flipped_cards.append(card)
        if flipped_cards != []:
            del flipped_cards[:-1]
        flipped_cards.extend(face_up_cards)
        face_up_cards = flipped_cards
        cards_moved = self.card_moved_to_ace_by_sender
        over_ace = []
        temp_over_ace = []
        for item in self.canvas.find_withtag("empty_ace_slot"):
            temp_over_ace = []
            for card in self.canvas.find_overlapping(*self.canvas.bbox(item)):
                temp_over_ace.append(card)
                if card in face_up_cards:
                    face_up_cards.remove(card)
            over_ace.append(temp_over_ace[-1])
        self.cardsender_may_continue = True
        for pair in over_ace:
            for card in face_up_cards:
                if pair == card:
                    continue
                self.change_current(card)
                self.end_onclick(event="send_cards_to_ace")
                self.canvas.dtag("current")
                self.change_current(pair)
                self.card_onclick(event="send_cards_to_ace")
                self.canvas.dtag("current")
                self.card_stack_list = ""
                self.last_active_card = ""
                self.canvas.delete("cardsender_highlight")
                self.update_idletasks()

                if not self.cardsender_may_continue:
                    return
        if self.cardsender_may_continue:
            if cards_moved != self.card_moved_to_ace_by_sender:
                self.send_cards_up()
            else:
                self.card_moved_to_ace_by_sender = 0
                self.stopwatch.freeze(True)

    def redo_move(self, *args):
        if self.move_flag:
            return
        try:
            last_move = self.redo[-1]
        except:
            return
        self.last_active_card = ""
        self.card_stack_list = ""
        self.canvas.delete("rect")
        del self.redo[-1]
        self.initiate_game()

        if "refill_card_stack" in last_move:
            self.refill_card_stack(event="redo")
        elif "stack_click_move" in last_move:
            self.stack_onclick(event="redo")
        else:
            if "move_card" in last_move:
                last_active_card = list(last_move[2])[0]
            else:
                last_active_card = last_move[3]
            self.change_current(last_active_card)
            self.end_onclick(event="redo")
            self.canvas.dtag("current")
            if "empty" in str(last_move[-1]):
                last_move[-1] = list(str(last_move[-1]).split("'"))[0]
            self.change_current(last_move[-1])
            self.card_onclick(event="redo")
            self.canvas.dtag("current")
        self.initiate_game()
        try:
            last_move = self.redo[-1]
            self.redo_last_move_button.config(state="normal")
            if self.redo_last_move_button.on_button:
                self.redo_last_move_button.config(
                    background=self.redo_last_move_button["activebackground"])
        except:
            self.redo_last_move_button.disable()

    def change_current(self, tag):
        self.canvas.dtag("current")
        self.canvas.focus("")
        self.canvas.addtag_withtag("current", tag)

    def undo_move(self, *args):
        if self.move_flag:
            return
        self.last_active_card = ""
        self.card_stack_list = ""
        self.canvas.delete("rect")
        self.initiate_game()
        try:
            last_move = self.history[-1]
        except:
            return
        self.redo.append(last_move)
        del self.history[-1]
        if "refill_card_stack" in last_move:
            self.redeals_left += 1
            if self.total_redeals != "unlimited":
                self.redeal_label.config(
                    text=f"Осталось пересдач: {max(0, self.total_redeals + self.redeals_left - 1)}")
            for card in reversed(list(self.canvas.find_overlapping(*self.canvas.bbox("empty_cardstack_slot")))):
                current_item_tags = self.canvas.gettags(card)
                tag_a = current_item_tags[0]
                if "empty_cardstack_slot" in (self.canvas.gettags(card)):
                    continue
                self.canvas.tag_unbind(tag_a, "<Enter>")
                self.canvas.tag_unbind(tag_a, "<Leave>")
                self.canvas.tag_unbind(tag_a, "<Button-1>")
                if self.movetype == "Клик":
                    self.canvas.tag_bind(
                        tag_a, "<Button-1>", self.card_onclick)
                else:
                    self.canvas.tag_bind(tag_a, "<Button-1>", self.end_onclick)
                    self.canvas.tag_bind(
                        tag_a, "<Button1-Motion>", self.move_card)
                    self.canvas.tag_bind(
                        tag_a, "<ButtonRelease-1>", self.drop_card)
                    self.canvas.tag_bind(
                        tag_a, "<Enter>", self.on_draggable_card)
                    self.canvas.tag_bind(
                        tag_a, "<Leave>", self.leave_draggable_card)
                self.canvas.tag_raise(card)
                self.canvas.move(card, 115, 0)
                self.canvas.itemconfig(card, image=self.dict_of_cards[tag_a], tag=(tag_a, "face_up"))
                self.stock_left -= 1
            self.stock_label.config(text=f"Осталось карт:  {self.stock_left}")
            self.undo_last_move_button.config(state="normal")
            self.restart_game_button.config(state="normal")
            self.redo_last_move_button.disable()

        elif "stack_click_move" in last_move:
            self.canvas.delete("rect")
            self.stock_left += 1
            self.stock_label.config(text=f"Осталось карт:  {(self.stock_left)}")
            tag_a = last_move[0]
            self.canvas.move(tag_a, -115, 0)
            self.canvas.itemconfig(
                tag_a, image=self.back_of_card, tag=(tag_a, "face_down"))
            self.canvas.tag_unbind(tag_a, "<Enter>")
            self.canvas.tag_unbind(tag_a, "<Leave>")
            self.canvas.tag_unbind(tag_a, "<Button-1>")
            self.canvas.tag_bind(tag_a, "<Button-1>", self.stack_onclick)
            self.canvas.tag_raise(self.canvas.find_withtag(tag_a))

        elif "move_card" in last_move:
            card_tags = last_move[-2]
            self.canvas.itemconfig(card_tags, image=self.back_of_card,
                                   tag=(card_tags, "face_down"))
            self.canvas.tag_unbind(card_tags, "<Enter>")
            self.canvas.tag_unbind(card_tags, "<Leave>")
            self.canvas.tag_unbind(card_tags, "<Button-1>")
            for i in last_move[2]:
                card_location = self.canvas.coords(i)
                current_location = last_move[2][i]
                xpos = int(current_location[0]) - int(card_location[0])
                ypos = (int(current_location[1]) - int(card_location[1]))
                self.canvas.move(i, xpos, ypos)
                if True in last_move:
                    self.canvas.tag_raise(i)
            if last_move[1] == 1:
                self.cards_on_ace -= 1
                for i in last_move[2]:
                    self.canvas.tag_raise(i)
                self.points_label["text"] = (f"Очки: {(self.cards_on_ace * self.point_increment) + self.starting_points}")
            elif last_move[1] == 2:
                self.cards_on_ace += 1
                self.points_label["text"] = (f"Очки: {(self.cards_on_ace * self.point_increment) + self.starting_points}")

        elif "move_card_srv" in last_move:
            card_location = self.canvas.coords(last_move[3])
            current_image_location = last_move[-2]
            
            if last_move[1]:
                current_image_location = self.canvas.coords(last_move[1])
                    
            xpos = int(current_image_location[0]) - int(card_location[0])
            ypos = (int(current_image_location[1]) - int(card_location[1]))
            self.canvas.move(last_move[3], xpos, ypos)
            self.canvas.tag_raise(last_move[3])

            if last_move[2] == 1:
                self.cards_on_ace -= 1
                self.points_label["text"] = (f"Очки: {(self.cards_on_ace * self.point_increment) + self.starting_points}")
            elif last_move[2] == 2:
                self.cards_on_ace += 1
                self.points_label["text"] = (f"Очки: {(self.cards_on_ace * self.point_increment) + self.starting_points}")
        self.canvas.tag_raise("face_up")
        self.restart_game_button.config(state="normal")
        self.redo_last_move_button.config(state="normal")
        try:
            last_move = self.history[-1]
        except:
            self.undo_last_move_button.disable()
            self.restart_game_button.disable()


    def check_move_validity(self, current_card, last_card, ace_slot):
        card_values = {
            "j": "11",
            "q": "12",
            "k": "13",
            "a": "1"
        }        
        if ace_slot:
            if "clubs" in current_card and "clubs" not in last_card:
                return False
            if "spades" in current_card and "spades" not in last_card:
                return False
            if "diamonds" in current_card and "diamonds" not in last_card:
                return False
            if "hearts" in current_card and "hearts" not in last_card:
                return False
        else:
            if (("clubs" in current_card) or ("spades" in current_card)) and (("clubs" in last_card) or ("spades" in last_card)):
                return False
            elif (("diamonds" in current_card) or ("hearts" in current_card)) and (("diamonds" in last_card) or ("hearts" in last_card)):
                return False
        if "empty_ace_slot" in current_card:
            return True
        else:
            if last_card[1] == "0":
                last_card = "10"
            else:
                last_card = last_card[0]

            if current_card[1] == "0":
                current_card = "10"
            else:
                current_card = current_card[0]

            last_card = card_values.get(last_card, last_card)  
            current_card = card_values.get(current_card, current_card)
            last_card = int(last_card)
            current_card = int(current_card)

            if ace_slot:
                if last_card - 1 == current_card:
                    return True
                else:
                    return False
            else:
                if last_card + 1 == current_card:
                    return True
                else:
                    return False

    def stack_onclick(self, event):
        if self.move_flag:
            return
        self.initiate_game()
        current_item = list(self.canvas.find_overlapping(
            *self.canvas.bbox("empty_cardstack_slot")))[-1]
        current_item_tags = self.canvas.gettags(current_item)
        tag_a = current_item_tags[0]
        if event != "redo":
            self.redo = []
            if "empty_cardstack_slot" in tag_a:
                return
            elif event != "hint":
                if current_item not in self.canvas.find_withtag("current"):
                    return
            elif "rect" in tag_a:
                return
        else:
            if "empty_cardstack_slot" in tag_a:
                return

        self.canvas.delete("rect")
        self.stock_left -= 1
        self.stock_label.config(text=f"Осталось карт:  {self.stock_left}")
        self.last_active_card = ""
        self.card_stack_list = ""
        history_to_add = [tag_a, "stack_click_move"]
        self.history.append(history_to_add)
        self.canvas.move(current_item, 115, 0)
        self.canvas.itemconfig(current_item, image=self.dict_of_cards[tag_a], tag=(tag_a, "face_up"))
        self.canvas.tag_unbind(tag_a, "<Button-1>")
        if self.movetype == "Клик":
            self.canvas.tag_bind(tag_a, "<Button-1>", self.card_onclick)
        else:
            self.canvas.tag_bind(tag_a, "<Button-1>", self.end_onclick)
            self.canvas.tag_bind(tag_a, "<Button1-Motion>", self.move_card)
            self.canvas.tag_bind(tag_a, "<ButtonRelease-1>", self.drop_card)
            self.canvas.tag_bind(tag_a, "<Enter>", self.on_draggable_card)
            self.canvas.tag_bind(tag_a, "<Leave>", self.leave_draggable_card)

        self.canvas.tag_raise(self.canvas.find_withtag(tag_a))
        self.undo_last_move_button.config(state="normal")
        self.restart_game_button.config(state="normal")
        self.redo_last_move_button.disable()

    def refill_card_stack(self, event):
        if self.move_flag:
            return
        if event != "redo":
            self.redo = []
        self.initiate_game()
        self.canvas.delete("rect")
        ret = False
        if self.total_redeals != "unlimited":
            if (self.total_redeals + self.redeals_left - 1) <= 0:
                messagebox.showinfo(title="Пересдачи закончились :(",
                                    message="Пересдать карты можно только 3 раза. Начните новую игру.")
                ret = True
        if not ret:
            history_to_add = ["refill_card_stack"]
            self.history.append(history_to_add)
            self.redeals_left -= 1
            if self.total_redeals != "unlimited":
                self.redeal_label.config(text=f"Осталось пересдач: {max(0, self.total_redeals + self.redeals_left - 1)}")

            for card in reversed(list(self.canvas.find_overlapping(*self.canvas.bbox("empty_cardstack_slotb")))):
                if "empty_cardstack_slotb" in self.canvas.gettags(card):
                    continue
                card = self.canvas.gettags(card)[0]
                self.canvas.tag_unbind(card, "<Button-1>")
                self.canvas.tag_unbind(card, "<Enter>")
                self.canvas.tag_unbind(card, "<Leave>")
                self.canvas.tag_bind(card, "<Button-1>", self.stack_onclick)
                self.canvas.tag_raise(card)
                self.canvas.move(card, -115, 0)
                self.canvas.itemconfig(card, image=self.back_of_card, tag=(card, "face_down"))
            self.stock_left -= 1
            for i in (self.canvas.find_overlapping(*self.canvas.bbox("empty_cardstack_slot"))):
                self.stock_left += 1
            self.stock_label.config(text=f"Осталось пересдач: {self.stock_left}")
            self.undo_last_move_button.config(state="normal")
            self.restart_game_button.config(state="normal")
            self.redo_last_move_button.config(state="disabled")

    def on_draggable_card(self, event):
        if self.canvas["cursor"] != "fleur":
            self.canvas.config(cursor="hand2")

    def leave_draggable_card(self, event):
        if self.canvas["cursor"] != "fleur":
            self.canvas.config(cursor="")

    def move_card(self, event):
        self.canvas.delete("available_card_rect")
        self.canvas.delete("rect")
        if self.move_flag:
            new_xpos, new_ypos = event.x, event.y
            self.canvas.move("moveable", new_xpos - self.mouse_xpos, new_ypos - self.mouse_ypos)
            self.mouse_xpos = new_xpos
            self.mouse_ypos = new_ypos
            self.highlight_available_cards()
        else:
            for item in self.card_stack_list:
                card_tag = list(self.canvas.gettags(item))[0]
                if "empty" in str(self.canvas.gettags(item)):
                    continue
                elif "face_down" in str(self.canvas.gettags(item)):
                    continue
                else:
                    self.canvas.addtag_withtag("moveable", card_tag)
            self.move_flag = True
            self.canvas.tag_raise("moveable")
            self.mouse_xpos = event.x
            self.mouse_ypos = event.y

    def highlight_available_cards(self):
        try:
            last_image_location = self.current_image_location
            returnval = True
            bbox = list(self.canvas.bbox(self.canvas.find_withtag("current")))
            bbox[0] = int(bbox[0]) - 15
            bbox[1] = int(bbox[1]) - 15
            bbox[2] = int(bbox[2]) + 15
            bbox[3] = int(bbox[3]) + 15
            card_overlapping = self.canvas.find_overlapping(*tuple(bbox))
        except:
            return
        for card in card_overlapping:
            if (self.canvas.find_withtag("current")) == card:
                continue
            card_tag = str(self.canvas.gettags(card))
            if "face_down" in card_tag:
                continue
            elif "current" in card_tag:
                continue
            elif "empty_cardstack_slot" in card_tag:
                break
            else:
                current_image = self.canvas.find_withtag(card)
                current_image_bbox = self.canvas.bbox(current_image)
                returnval = self.generate_returnval(current_image)
                if returnval:
                    self.create_rectangle(
                        *current_image_bbox, fill="blue", alpha=.3, tag="available_card_rect")
                    for card in self.card_stack_list:
                        if "empty_slot" not in self.canvas.gettags(card):
                            self.canvas.tag_raise(card)
                    continue

    def drop_card(self, event):
        if self.canvas["cursor"] == "fleur":
            self.canvas.config(cursor="hand2")
        self.canvas.delete("available_card_rect")
        self.move_flag = False
        self.canvas.dtag("face_up", "moveable")
        try:
            last_image_location = self.current_image_location
            returnval = True
            bbox = list(self.canvas.bbox(self.canvas.find_withtag("current")))
            bbox[0] = int(bbox[0]) - 15
            bbox[1] = int(bbox[1]) - 15
            bbox[2] = int(bbox[2]) + 15
            bbox[3] = int(bbox[3]) + 15
            card_overlapping = self.canvas.find_overlapping(*tuple(bbox))
        except:
            moving_count = 0
            for item in self.card_stack_list:
                if "empty" in str(self.canvas.gettags(item)):
                    continue
                elif "face_down" in str(self.canvas.gettags(item)):
                    continue
                else:
                    xpos = int(last_image_location[0]) - int(self.canvas.coords(item)[0])
                    ypos = moving_count + (int(last_image_location[1]) - int(self.canvas.coords(item)[1]))
                    self.canvas.move(item, xpos, ypos)
                    moving_count += 20
            return
        for card in card_overlapping:
            card_tag = str(self.canvas.gettags(card))
            if "face_down" in card_tag:
                continue
            elif "current" in card_tag:
                continue
            elif "empty_cardstack_slot" in card_tag:
                break
            else:
                self.current_image = current_image = self.canvas.find_withtag(card)
                self.current_image_tags = current_image_tags = self.canvas.gettags(current_image)
                self.current_image_location = self.canvas.coords(current_image)
                self.current_image_bbox = current_image_bbox = self.canvas.bbox(current_image)
                bbox_list = list(current_image_bbox)
                current_image_overlapping = self.canvas.find_overlapping(*bbox_list)
                self.tag_a = tag_a = str(current_image_tags).replace(", 'current')", "").replace(
                    ")", "").replace("('", "").replace("', 'face_down'", "").replace("', 'face_up'", "")
                overlapping = False
                ace_slot = False
                over_ace_slot = False
                for card in self.canvas.find_overlapping(*self.canvas.bbox(current_image)):
                    if "empty_ace_slot" in self.canvas.gettags(card):
                        over_ace_slot = True
                        break
                if (not over_ace_slot) and ("empty_slot" not in str(current_image_tags)):
                    csl = list(self.canvas.bbox(tag_a))
                    csl[1] = (int(csl[1])) + 135
                    csl[3] = (int(csl[3])) + 20
                    csl = tuple(csl)
                    csl = list(self.canvas.find_overlapping(*csl))
                    for card in csl:
                        if card in self.card_stack_list:
                            continue
                        elif "empty_cardstack_slot" in str(self.canvas.gettags(card)):
                            overlapping = True
                            break
                        elif "face_up" in self.canvas.gettags(card):
                            overlapping = True
                            break

                if "empty_slot" in str(self.current_image_tags):
                    if "king" in self.last_active_card:
                        for card in current_image_overlapping:
                            if card in self.card_stack_list:
                                continue
                            elif "face" in str(self.canvas.gettags(card)):
                                overlapping = True
                                break

                for item in current_image_overlapping:
                    if "empty_ace_slot" in self.canvas.gettags(self.canvas.find_withtag(item)):
                        ace_slot = True

                if ace_slot:
                    try:
                        for item in self.card_stack_list:
                            self.canvas.tag_raise(item)
                        item = self.canvas.find_overlapping(*self.canvas.bbox(self.canvas.find_above(self.last_active_card)))
                        overlapping = True
                    except:
                        pass

                try:
                    if str(list(current_image)[0]) == str(self.last_active_card_over[self.last_active_card_over.index(list(self.canvas.find_withtag(self.last_active_card))[0])-1]):
                        overlapping = True
                except (ValueError, IndexError):
                    pass
                
                if "ace" not in self.last_active_card and "empty_ace_slot" in self.current_image_tags:
                    continue
                elif "king" not in self.last_active_card and "empty_slot" in self.current_image_tags:
                    continue
                elif "empty_slot" in self.last_active_card:
                    continue
                elif overlapping:
                    continue
                elif "king" in self.last_active_card and "empty_slot" in self.current_image_tags:
                    self.continue_onclick(ace_slot=ace_slot, event=event)
                    returnval = False
                    break
                elif self.check_move_validity(tag_a, self.last_active_card, ace_slot):
                    self.continue_onclick(ace_slot=ace_slot, event=event)
                    returnval = False
                    break
                else:
                    continue

        if returnval:
            moving_count = 0
            for item in self.card_stack_list:
                if "empty" in str(self.canvas.gettags(item)):
                    continue
                elif "face_down" in str(self.canvas.gettags(item)):
                    continue
                else:
                    xpos = int(last_image_location[0]) - int(self.canvas.coords(item)[0])
                    ypos = moving_count + (int(last_image_location[1]) - int(self.canvas.coords(item)[1]))
                    self.canvas.move(item, xpos, ypos)
                    moving_count += 20
        self.card_stack_list = ""
        self.canvas.delete("rect")
        self.last_active_card = ""

    def generate_returnval(self, current_image, use_last_active_card=None):
        if use_last_active_card:
            last_active_card = use_last_active_card
        else:
            last_active_card = self.last_active_card
        current_image_tags = self.canvas.gettags(current_image)

        current_image_bbox = self.canvas.bbox(current_image)
        bbox_list = list(current_image_bbox)
        current_image_overlapping = self.canvas.find_overlapping(*bbox_list)

        tag_a = str(current_image_tags).replace(", 'current')", "").replace(")", "").replace(
            "('", "").replace("', 'face_down'", "").replace("', 'face_up'", "")
        overlapping = False
        ace_slot = False
        returnval = False

        over_ace_slot = False
        for card in self.canvas.find_overlapping(*self.canvas.bbox(current_image)):
            if "empty_ace_slot" in self.canvas.gettags(card):
                over_ace_slot = True
                break
        if (not over_ace_slot) and ("empty_slot" not in str(current_image_tags)):
            csl = list(self.canvas.bbox(current_image))
            csl[1] = (int(csl[1])) + 135
            csl[3] = (int(csl[3])) + 20
            csl = tuple(csl)
            csl = list(self.canvas.find_overlapping(*csl))
            for card in csl:
                if card in self.card_stack_list:
                    continue
                elif "face_up" in self.canvas.gettags(card):

                    overlapping = True
                    break

        if "empty_slot" in str(current_image_tags):
            if "king" in last_active_card:
                for card in current_image_overlapping:
                    if card in self.card_stack_list:
                        continue
                    elif "face" in str(self.canvas.gettags(card)):
                        overlapping = True
                        break

        for item in current_image_overlapping:
            if "empty_ace_slot" in self.canvas.gettags(self.canvas.find_withtag(item)):
                ace_slot = True

        if ace_slot:
            try:
                for item in self.card_stack_list:
                    self.canvas.tag_raise(item)
                item = self.canvas.find_overlapping(*self.canvas.bbox(self.canvas.find_above(last_active_card)))
                overlapping = True
            except:
                pass

        if "ace" not in last_active_card and "empty_ace_slot" in current_image_tags:
            return returnval
        elif "king" not in last_active_card and "empty_slot" in current_image_tags:
            return returnval
        elif "empty_slot" in last_active_card:
            return returnval
        elif overlapping:
            return returnval
        elif "king" in last_active_card and "empty_slot" in current_image_tags:
            returnval = True
            return returnval
        elif self.check_move_validity(tag_a, last_active_card, ace_slot):
            returnval = True
            return returnval
        else:
            return returnval

    def card_onclick(self, event):
        self.initiate_game()
        self.current_image = current_image = self.canvas.find_withtag("current")
        self.current_image_tags = current_image_tags = self.canvas.gettags(current_image)
        self.current_image_location = self.canvas.coords(current_image)
        self.current_image_bbox = current_image_bbox = self.canvas.bbox(current_image)
        bbox_list = list(current_image_bbox)
        current_image_overlapping = self.canvas.find_overlapping(*bbox_list)
        self.tag_a = tag_a = str(current_image_tags).replace(", 'current')", "").replace(
            "('", "").replace("', 'face_down'", "").replace("', 'face_up'", "")
        overlapping = False
        ace_slot = False
        if self.last_active_card != "":
            if "empty_ace_slot" not in str(current_image_tags) and "empty_slot" not in str(current_image_tags):
                csl = list(self.canvas.bbox(tag_a))
                csl[1] = (int(csl[1])) + 135
                csl[3] = (int(csl[3]))+20
                csl = tuple(csl)
                csl = list(self.canvas.find_overlapping(*csl))
                for i in csl:
                    if "face_up" in self.canvas.gettags(self.canvas.find_withtag(i)):
                        overlapping = True

            for item in current_image_overlapping:
                if "empty_ace_slot" in self.canvas.gettags(self.canvas.find_withtag(item)):
                    ace_slot = True

            if ace_slot:
                try:
                    for item in self.card_stack_list:
                        self.canvas.tag_raise(item)
                    item = self.canvas.find_overlapping(
                        *self.canvas.bbox(self.canvas.find_above(self.last_active_card)))
                    overlapping = True
                except:
                    pass
                self.canvas.tag_raise("rect")

            try:
                for card in self.canvas.find_overlapping(*self.canvas.bbox(self.tag_a)):
                    if "empty_cardstack" in str(self.canvas.gettags(card)):
                        overlapping = True
            except:
                pass
            if "ace" not in self.last_active_card and "empty_ace_slot" in current_image_tags:
                if event != "send_cards_to_ace":
                    self.end_onclick(event=event)
            elif "king" not in self.last_active_card and "empty_slot" in current_image_tags:
                if event != "send_cards_to_ace":
                    self.end_onclick(event=event)
            elif "empty_slot" in self.last_active_card:
                if event != "send_cards_to_ace":
                    self.end_onclick(event=event)
            elif overlapping is True:
                if event != "send_cards_to_ace":
                    self.end_onclick(event=event)
            elif "king" in self.last_active_card and "empty_slot" in current_image_tags:
                self.continue_onclick(ace_slot=ace_slot, event=event)
            elif self.check_move_validity(tag_a, self.last_active_card, ace_slot) is True:
                if event == "send_cards_to_ace":
                    self.create_rectangle(
                        *self.canvas.bbox(self.last_active_card), fill="blue", tag="cardsender_highlight", alpha=.5)
                    self.canvas.tag_raise("cardsender_highlight")
                    self.update_idletasks()
                    self.canvas.after(self.wait_before_send)
                    self.update_idletasks()
                self.continue_onclick(ace_slot=ace_slot, event=event)
            else:
                if event != "send_cards_to_ace":
                    self.end_onclick(event=event)
        else:
            if event != "send_cards_to_ace":
                self.end_onclick(event=event)

    def end_onclick(self, event, current_tag_name="current", pass_variable_updates=False):
        self.initiate_game()
        self.canvas.tag_unbind("face_up", "<Enter>")
        self.canvas.tag_unbind("card_below_rect", "<Enter>")
        self.canvas.dtag("card_below_rect")
        self.current_image = current_image = self.canvas.find_withtag(current_tag_name)[0]
        self.current_image_tags = current_image_tags = self.canvas.gettags(current_image)
        self.current_image_location = self.canvas.coords(current_image)
        self.current_image_bbox = self.canvas.bbox(current_image)
        self.tag_a = current_image_tags[0]

        if ("empty_ace_slot" not in self.current_image_tags and "empty_slot" not in self.current_image_tags) or pass_variable_updates:
            self.card_stack_list = ""
            self.canvas.delete("rect")
            self.last_active_card = ""
            self.last_active_card = self.tag_a
            self.card_stack_list = list(self.canvas.bbox(self.last_active_card))
            self.card_stack_list[1] = (int(self.card_stack_list[1])) + 129
            self.card_stack_list[3] = (int(self.card_stack_list[3])) + 350
            self.card_stack_list = tuple(self.card_stack_list)
            self.card_stack_list = list(self.canvas.find_overlapping(*self.card_stack_list))

            if self.movetype == "Перетаскивание":
                if event != "send_cards_to_ace":
                    self.canvas.config(cursor="fleur")
                for card in self.card_stack_list:
                    card_tag = self.canvas.gettags(card)
                    if "cardstack" in str(card_tag):
                        to_be_card_stack_list = self.card_stack_list[-1]
                        self.card_stack_list = []
                        self.card_stack_list.append(to_be_card_stack_list)
                        break
                    elif "ace_slot" in str(card_tag):
                        self.card_stack_list = []
                        for card in self.canvas.find_withtag(self.last_active_card):
                            self.card_stack_list.append(card)
                        break
            last_active_card_bbox_list = list(self.canvas.bbox(self.last_active_card))
            last_active_card_bbox_list[1] = int(last_active_card_bbox_list[1]) + 90
            last_active_card_bbox_list[3] = int(last_active_card_bbox_list[3]) - 25
            last_active_card_bbox_list = tuple(last_active_card_bbox_list)
            self.last_active_card_overlapping = self.canvas.find_overlapping(*last_active_card_bbox_list)
            self.last_active_card_over = self.canvas.find_overlapping(*self.canvas.bbox(self.last_active_card))
            self.last_active_card_coordinates = []
            for card in self.card_stack_list:
                self.last_active_card_coordinates.append(self.canvas.coords(card))

            if self.movetype != "Перетаскивание" and event != "send_cards_to_ace":
                first_item = list(self.canvas.bbox(self.last_active_card))
                last_item = list(self.canvas.bbox(self.canvas.find_withtag(self.card_stack_list[-1])))
                tl = first_item[0]
                tr = first_item[1]
                bl = last_item[2]
                br = last_item[3]
                positionsb = []
                positionsb.append(tl)
                positionsb.append(tr)
                positionsb.append(bl)
                positionsb.append(br)
                positionsb = tuple(positionsb)
                positions = self.canvas.bbox(self.last_active_card)
                returnval = False
                for item in self.card_stack_list:
                    if "empty_ace_slot" in self.canvas.gettags(self.canvas.find_withtag(item)):
                        returnval = True
                        break
                if returnval is True:
                    self.create_rectangle(*positions, fill="blue", alpha=.3)
                else:
                    self.create_rectangle(*positionsb, fill="blue", alpha=.3)
                if self.movetype == "Клик":
                    self.canvas.tag_bind(
                        "rect", "<Button-1>", self.click_on_rect)


    def click_on_hint_rect(self, event):
        try:
            below_last = self.canvas.find_overlapping(*self.canvas.bbox("current"))
        except:
            return
        last_card_index_in_below = below_last.index(
            list(self.canvas.find_withtag("current"))[0])
        below_last = (below_last[last_card_index_in_below - 1])
        if "empty_cardstack_slot" in self.canvas.gettags(below_last):
            self.refill_card_stack(event="hint")
        else:
            returnval = False
            for card in self.canvas.find_overlapping(*self.canvas.bbox(below_last)):
                if "empty_cardstack_slot" in self.canvas.gettags(card):
                    self.canvas.delete("rect")
                    self.stack_onclick(event="hint")
                    returnval = True
                    break
            if not returnval:
                self.canvas.tag_bind("face_up", "<Enter>", self.end_onclick)
        self.canvas.tag_unbind("rect", "<Enter>")
        self.canvas.tag_unbind("rect", "<Leave>")
        self.canvas.tag_unbind("rect", "<Button-1>")
        self.canvas.delete("rect")

    def click_on_rect(self, event):
        self.canvas.tag_bind("face_up", "<Enter>", self.end_onclick)
        self.canvas.delete("rect")

    def enter_on_hint_rect(self, event):
        self.canvas.tag_unbind("rect", "<Enter>")
        self.canvas.delete("rect")

    def continue_onclick(self, ace_slot, event):
        self.update_idletasks()
        self.cardsender_may_continue = True
        if event != "redo":
            self.redo = []
        self.canvas.delete("rect")
        tag_list = []
        new_card_on_ace = 0
        self.card_drawing_count = 20

        for i in self.last_active_card_overlapping:
            tag_list.append(self.canvas.gettags(i))
            
        if "empty_ace_slot" in str(tag_list):
            self.cards_on_ace -= 1
            self.points_label["text"] = (f"Очки: {(self.cards_on_ace * self.point_increment) + self.starting_points}")
            new_card_on_ace = 2
            check = self.generate_drawing_count(ace_slot=ace_slot)
            if self.movetype == "Перетаскивание":
                self.card_drawing_count = 20
                for i in self.canvas.find_overlapping(*self.canvas.bbox(self.current_image)):
                    tag_list.append(self.canvas.gettags(i))
                if "empty_ace_slot" in str(tag_list):
                    check = self.generate_drawing_count(ace_slot=ace_slot)
                    if check != None:
                        new_card_on_ace = check
        else:
            check = self.generate_drawing_count(ace_slot=ace_slot)
            if check != None:
                new_card_on_ace = check

        last_active_card_bbox_list = list(self.canvas.bbox(self.last_active_card))
        last_active_card_bbox_list[1] = int(last_active_card_bbox_list[1]) + 60
        last_active_card_bbox_list[3] = int(last_active_card_bbox_list[3]) - 25
        last_active_card_bbox_list = tuple(last_active_card_bbox_list)

        secondreturnval = False
        empty_ace_slot_found = False
        for i in list(self.last_active_card_overlapping):
            if "empty_ace_slot" in self.canvas.gettags(self.canvas.find_withtag(i)):
                secondreturnval = True
                empty_ace_slot_found = i
                break
            elif "empty_cardstack_slotb" in self.canvas.gettags(self.canvas.find_withtag(i)):
                secondreturnval = True
                break
            
        if secondreturnval:
            last_active_card = self.canvas.find_withtag(self.last_active_card)
            last_active_card_coordinates = self.canvas.coords(last_active_card)
            xpos = int(self.current_image_location[0]) - int(last_active_card_coordinates[0])
            ypos = self.card_drawing_count + (int(self.current_image_location[1]) - int(last_active_card_coordinates[1]))
            self.canvas.move(last_active_card, xpos, ypos)
            self.canvas.tag_raise(last_active_card)
            if event == "send_cards_to_ace":
                self.canvas.tag_raise("cardsender_highlight")
                self.card_moved_to_ace_by_sender += 1
            if self.movetype != "Перетаскивание":
                history_to_add = ["move_card_srv", empty_ace_slot_found, new_card_on_ace,
                                  self.last_active_card, last_active_card_coordinates, self.tag_a]
            else:
                history_to_add = ["move_card_srv", empty_ace_slot_found, new_card_on_ace, self.last_active_card,
                                  self.last_active_card_coordinates[0], self.current_image]
        else:
            flipped_cards = []
            moved_cards = {}
            for card in list(self.last_active_card_overlapping):
                card_values = self.canvas.find_withtag(card)
                if "face_down" in self.canvas.gettags(card_values):
                    card_tags = str(self.canvas.gettags(card_values))
                    tag_a = card_tags.replace("('", "").replace(
                        "', 'face_down')", "").replace("', 'face_up')", "")
                    self.canvas.itemconfig(card_values, image=self.dict_of_cards[tag_a],
                                           tag=(tag_a, "face_up"))
                    if self.movetype == "Клик":
                        self.canvas.tag_bind(
                            tag_a, "<Button-1>", self.card_onclick)
                    else:
                        self.canvas.tag_bind(
                            tag_a, "<Button-1>", self.end_onclick)
                        self.canvas.tag_bind(
                            tag_a, "<Button1-Motion>", self.move_card)
                        self.canvas.tag_bind(
                            tag_a, "<ButtonRelease-1>", self.drop_card)
                        self.canvas.tag_bind(
                            tag_a, "<Enter>", self.on_draggable_card)
                        self.canvas.tag_bind(
                            tag_a, "<Leave>", self.leave_draggable_card)
                    flipped_cards.append(tag_a)
            for card in list(self.card_stack_list):
                if "face_up" in self.canvas.gettags(self.canvas.find_withtag(card)):
                    card_location = self.canvas.coords(card)
                    xpos = int(self.current_image_location[0]) - int(card_location[0])
                    ypos = self.card_drawing_count + (int(self.current_image_location[1]) - int(card_location[1]))
                    self.canvas.move(card, xpos, ypos)
                    self.canvas.tag_raise(card)
                    if event == "send_cards_to_ace":
                        self.canvas.tag_raise("cardsender_highlight")
                        self.card_moved_to_ace_by_sender += 1
                    self.card_drawing_count += 20
                    moved_cards[str(self.canvas.gettags(self.canvas.find_withtag(card))).replace("('", "").replace("', 'face_down')", "").replace(
                        "', 'face_up')", "").replace("', 'face_up', 'current')", "")] = self.last_active_card_coordinates[self.card_stack_list.index(card)]
            history_to_add = ["move_card", new_card_on_ace, moved_cards,
                              self.card_drawing_count, flipped_cards, self.current_image]
        self.card_stack_list = ""
        self.last_active_card = ""

        if self.cards_on_ace == 52:
            if self.win != None:
                self.canvas.delete("cardsender_highlight")
                self.win.destroy()
                self.win = None
                self.card_moved_to_ace_by_sender = 0
                self.stopwatch.freeze(True)
            self.history = []
            self.cardsender_may_continue = False
            after_game = messagebox.askyesno(title="Вы выиграли!", message="Сыграем еще раз?", icon="question")
            if after_game:
                self.new_game()
            else:
                self.destroy()
                exit()

        self.history.append(history_to_add)
        self.undo_last_move_button.config(state="normal")
        self.restart_game_button.config(state="normal")
        self.redo_last_move_button.disable()
        self.update_idletasks()

    def generate_drawing_count(self, ace_slot):
        ace_slots = self.canvas.find_withtag("empty_ace_slot")
        positions_of_ace_rects = []
        for slot in ace_slots:
            positions_of_ace_rects.append(self.canvas.bbox(slot))
        returnval = False
        for i in positions_of_ace_rects:
            if str(self.current_image_bbox) == str(i):
                returnval = True
        if returnval is False:
            self.card_drawing_count = 20
        else:
            self.card_drawing_count = 0
        if "king" in self.last_active_card and "empty_slot" in self.current_image_tags:
            self.card_drawing_count = 0
        if ace_slot:
            self.cards_on_ace += 1
            self.points_label["text"] = (f"Очки: {(self.cards_on_ace * self.point_increment) + self.starting_points}")
            self.card_drawing_count = 0
            new_card_on_ace = 1
            self.canvas_item_hover_time += 300
            return new_card_on_ace


class Combobox(tk.Frame):
    def __init__(self, parent, values=[], frame_args={}, entry_args={}, label_args={}, listbox_args={}, replace_entry_with_label=True):
        tk.Frame.__init__(self, parent, **frame_args)        
        self.parent = parent
        self.values = values
        self.listbox_args = listbox_args
        self.box_opened_count = False
        self.mouse_on_self = False
        self.box_opened = 0
        self.pack_propagate(0)
        self.label_image = tk.PhotoImage(file=os.path.join("assets", "arrow_down.png"))
        self.other_label_image = tk.PhotoImage(file=os.path.join("assets", "arrow_up.png"))
        try:
            self.textvariable = entry_args["textvariable"]
        except:
            self.textvariable = tk.StringVar()
            entry_args["textvariable"] = self.textvariable
        try:
            self.highlightthickness = entry_args["highlightthickness"]
        except:
            self.highlightthickness = 0
        if replace_entry_with_label:
            self.entry = entry = tk.Label(self, **entry_args)
        else:
            self.entry = entry = tk.Entry(self, **entry_args)
        entry.pack(side="left", expand=True, fill="both")
        self.entry.config(highlightthickness=self.highlightthickness)
        self.label = label = tk.Label(self, image=self.label_image, cursor="hand2", **label_args)
        label.pack(side="right", fill="both")

        try:
            activecolor = label_args.pop("activebackground")
            try:
                color = label_args["background"]
            except:
                try:
                    color = label_args["bg"]
                except:
                    color = "white"
            label.bind("<Enter>", lambda event, color=activecolor: self.label_hover(event, color))
            label.bind("<Leave>", lambda event, color=color: self.label_hover(event, color))
        except:
            pass

        divider = tk.Frame(self, width=1, bg="black")
        divider.pack(side="right", pady=4, fill="both")
        self.bind("<Button-1>", self.focusin, "+")
        self.label.bind("<Button-1>", self.focusin, "+")
        self.entry.bind("<Button-1>", self.focusin, "+")
        divider.bind("<Button-1>", self.focusin, "+")
        self.bind("<Enter>", self.on_self, "+")
        self.label.bind("<Enter>", self.on_self, "+")
        self.entry.bind("<Enter>", self.on_self, "+")
        divider.bind("<Enter>", self.on_self, "+")
        self.bind("<Leave>", self.off_self, "+")
        self.label.bind("<Leave>", self.off_self, "+")
        self.entry.bind("<Leave>", self.off_self, "+")
        divider.bind("<Leave>", self.off_self, "+")
        if os.name != "nt":
           self.parent.bind("<Button-1>", self.focusout, "+")

    def on_self(self, event):
        self.mouse_on_self = True

    def off_self(self, event):
        self.mouse_on_self = False

    def open_listbox(self, event):
        self.entry.config(highlightthickness=self.highlightthickness)

        if self.box_opened_count:
            if self.box_opened == 1:
                self.box_opened = 0
            else:
                self.delete_box()
                self.box_opened += 1
                return

        self.entry.update()
        self.label.update()
        loc_x = self.winfo_rootx()
        loc_y = self.entry.winfo_rooty() + self.winfo_height() - 2
        width = self.entry.winfo_width() + self.label.winfo_width() + 3
        self.box = box = tk.Toplevel(self.parent)
        box.wm_overrideredirect(1)
        self.listbox = listbox = tk.Listbox(box, **self.listbox_args)
        height_increment = 25
        height = 0
        for item in self.values:
            listbox.insert("end", item)
            height += height_increment
        listbox.pack(fill="both")
        listbox.config(width=0, height=0)
        box.wm_geometry(f"{width}x{height}+{loc_x}+{loc_y}")
        listbox.update()
        box.wm_geometry(f"{width}x{listbox.winfo_height()}")
        listbox.bind("<<ListboxSelect>>", self.listbox_select)
        listbox.bind("<Motion>", self.on_listbox_enter)
        self.label.config(image=self.other_label_image)
        self.box.focus_set()
        self.box.bind("<FocusOut>", self.window_move, "+")

    def focusin(self, event):
        self.open_listbox(event=event)
        self.box_opened_count = True

    def focusout(self, event):
        for item in self.winfo_children():
            if str(item) in str(event.widget):
                return
        try:
            self.delete_box()
        except:
            pass

    def window_move(self, event):
        if self.mouse_on_self:
            return
        try:
            self.delete_box()
        except:
            pass

    def label_hover(self, event, color):
        event.widget.config(background=color)

    def delete_box(self, event=None):
        self.box.unbind("<FocusOut>")
        self.label.config(image=self.label_image)
        self.box.destroy()
        self.box_opened_count = False

    def listbox_select(self, event):
        widget = event.widget
        try:
            index = widget.curselection()[0]
        except:
            return
        selected = widget.get(index)
        self.delete_box()
        self.textvariable.set(selected)
        self.event_generate("<<ComboboxSelect>>")

    def on_listbox_enter(self, event):
        index = event.widget.index(f"@{event.x},{event.y}")
        event.widget.selection_clear(0, "end")
        event.widget.select_set(index)


class Settings(tk.Toplevel):
    def __init__(self, parent, **kwargs):
        tk.Toplevel.__init__(self, parent, **kwargs)
        self.title("Настройки пасьянса")
        self.geometry("600x400")
        self.resizable(False, False)
        self.config(background="#b0acac")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)
        self.columnconfigure(2, weight=1)
        self.columnconfigure(3, weight=1)
        self.updated_settings = False
        self.wm_protocol("WM_DELETE_WINDOW", self.delete_window)
        self.settings = settings = json.load(open(os.path.join("assets", "settings.json"), encoding="utf-8"))
        movetype = settings["movetype"]
        gamemode = settings["gamemode"]
        canvas_hover_time = 300
        wait_before_send = 100
        show_footer = settings["show_footer"] == "True"
        show_header = settings["show_header"] == "True"
        card_back = settings["card_back"]
        canvas_color = settings["canvas_color"]
        self.movetype_chooser_var = tk.StringVar(value=movetype)
        self.gametype_chooser_var = tk.StringVar(value=gamemode)
        self.card_back_var = tk.StringVar(value=card_back)
        self.canvas_color_var = tk.StringVar(value=canvas_color)
        self.header_button_var = tk.BooleanVar(value=show_header)
        self.footer_button_var = tk.BooleanVar(value=show_footer)
        self.movetype_chooser_options = ["Перетаскивание", "Клик"]
        self.gametype_chooser_options = ["Стандартный", "Тренировочный"]
        self.create_widgets()
        self.config_widgets()
        self.grid_all()
        self.iconbitmap(os.path.join("assets", "icon.ico"))


    def create_widgets(self):
        style = ttk.Style()
        style.configure("TScale", background="#b0acac")
        self.intro_label = tk.Label(self, text="Настройки игры", font=(
            "Calibri", 10, "normal"), bg="#b0acac", fg="grey")
        self.movetype_chooser = Combobox(self, self.movetype_chooser_options, {"height": 22, "width": 200, "bg": "#cccaca", "highlightbackground": "black", "highlightthickness": 1},
                                         {"textvariable": self.movetype_chooser_var, "anchor": "w",
                                             "padx": 2, "background": "#cccaca", "cursor": "arrow"},
                                         {"width": 10, "relief": "flat",
                                          "activebackground": "#b0b2bf", "bg": "#cccaca"},
                                         {"relief": "flat", "highlightbackground": "black", "highlightthickness": 1, "bg": "#d4d2d2"})
        self.gametype_chooser = Combobox(self, self.gametype_chooser_options, {"height": 22, "width": 200, "bg": "#cccaca", "highlightbackground": "black", "highlightthickness": 1},
                                         {"textvariable": self.gametype_chooser_var, "anchor": "w",
                                             "padx": 2, "background": "#cccaca", "cursor": "arrow"},
                                         {"width": 10, "relief": "flat",
                                          "activebackground": "#b0b2bf", "bg": "#cccaca"},
                                         {"relief": "flat", "highlightbackground": "black", "highlightthickness": 1, "bg": "#d4d2d2"})
        self.movetype_label = tk.Label(self,
                                       text="Перемещение:", bg="#b0acac", fg="black")
        self.gametype_label = tk.Label(self,
                                       text="Режим игры:", bg="#b0acac", fg="black")

        self.dark_back_button = tk.Radiobutton(self, text="Темная", variable=self.card_back_var, highlightthickness=0,
                                               value="dark_back", anchor="w", bg="#b0acac", activebackground="#706c6c")
        self.light_back_button = tk.Radiobutton(self, text="Светлая", variable=self.card_back_var, highlightthickness=0,
                                                      value="light_back", anchor="w", bg="#b0acac", activebackground="#706c6c")

        self.color_entry_label = tk.Label(self,
                                          text="Цвет фона:", bg="#b0acac")
        self.color_entry = tk.Entry(self, textvariable=self.canvas_color_var, state='disabled', relief="flat", highlightbackground="black", highlightthickness=1,
                                    bg=self.canvas_color_var.get(), disabledbackground=self.canvas_color_var.get(), disabledforeground=self.generate_new_color(self.canvas_color_var.get()), cursor="arrow")

        self.header_button = tk.Checkbutton(self,
                                            text="Верхнее меню", variable=self.header_button_var, highlightthickness=0, anchor="w", bg="#b0acac", activebackground="#706c6c")
        self.footer_button = tk.Checkbutton(self,
                                            text="Статистика", variable=self.footer_button_var, highlightthickness=0, anchor="w", bg="#b0acac", activebackground="#706c6c")
        self.save_button = tk.Button(self, text="Сохранить", relief="solid", borderwidth=1,
                                     command=self.save, bg="#b0acac", activebackground="#706c6c")
        self.reset_button = tk.Button(self, text="По умолчанию", relief="solid", borderwidth=1,
                                      command=self.reset_all, bg="#b0acac", activebackground="#706c6c")

    def config_widgets(self):
        self.movetype_chooser.bind("<<ComboboxSelect>>", self.movetype_chooser_select)
        self.gametype_chooser.bind("<<ComboboxSelect>>", self.gametype_chooser_select)
        self.dark_back_button.bind("<Enter>", self.enter_button)
        self.light_back_button.bind("<Enter>", self.enter_button)
        self.header_button.bind("<Enter>", self.enter_button)
        self.footer_button.bind("<Enter>", self.enter_button)
        self.dark_back_button.bind("<Leave>", self.leave_button)
        self.light_back_button.bind("<Leave>", self.leave_button)
        self.header_button.bind("<Leave>", self.leave_button)
        self.footer_button.bind("<Leave>", self.leave_button)
        self.save_button.bind("<Enter>", self.enter_button)
        self.reset_button.bind("<Enter>", self.enter_button)
        self.save_button.bind("<Leave>", self.leave_button)
        self.reset_button.bind("<Leave>", self.leave_button)
        self.color_entry.bind("<Button-1>", self.open_colorpicker)
        self.color_entry.bind("<Enter>", lambda event: self.color_entry.config(
            highlightbackground=self.color_entry["bg"]))
        self.color_entry.bind("<Leave>", self.leave_combo)
        self.movetype_chooser.bind("<Enter>", self.enter_combo)
        self.movetype_chooser.bind("<Leave>", self.leave_combo)
        self.gametype_chooser.bind("<Enter>", self.enter_combo)
        self.gametype_chooser.bind("<Leave>", self.leave_combo)

        self.last_gamemode = self.gametype_chooser_var.get()

    def enter_entry(self, event):
        if event.widget["state"] == "normal":
            event.widget.config(highlightbackground="grey")

    def leave_entry(self, event):
        if event.widget["state"] == "normal":
            event.widget.config(highlightbackground="black")

    def enter_combo(self, event):
        event.widget.config(highlightbackground="grey")

    def leave_combo(self, event):
        event.widget.config(highlightbackground="black")

    def grid_all(self):
        self.intro_label.grid(row=0, column=0, columnspan=4,
                              padx=8, pady=2, sticky="ew")
        tk.Label(self, text="Игра:", font=("Calibri", 11, "bold"), bg="#b0acac", fg="blue").grid(
            row=1, column=0, columnspan=2, padx=8, pady=2, sticky="w")
        self.movetype_label.grid(
            row=2, column=0, columnspan=2, padx=8, pady=7, sticky="w")
        self.movetype_chooser.grid(
            row=2, column=1, columnspan=3, padx=8, pady=7, sticky="ew")
        self.gametype_label.grid(
            row=3, column=0, columnspan=2, padx=8, pady=7,  sticky="w")
        self.gametype_chooser.grid(
            row=3, column=1, columnspan=3, padx=8, pady=7, sticky="ew")

        ttk.Separator(self).grid(row=8, column=0, columnspan=4,
                                 padx=6, pady=5, sticky="ew")
        tk.Label(self, text="Рубашка:", font=("Calibri", 11, "bold"), bg="#b0acac", fg="blue").grid(
            row=9, column=0, columnspan=2, padx=8, pady=2, sticky="w")
        self.dark_back_button.grid(
            row=10, column=0, columnspan=2, padx=8, pady=7, sticky="ew")
        self.light_back_button.grid(
            row=10, column=2, columnspan=2, padx=8, pady=7, sticky="ew")
        ttk.Separator(self).grid(row=12, column=0,
                                 columnspan=4, padx=8, pady=5, sticky="ew")
        self.color_entry_label.grid(row=13, column=0,
                                    columnspan=2, padx=8, pady=5, sticky="w")
        self.color_entry.grid(row=13, column=2,
                              columnspan=2, padx=8, pady=5, sticky="ew")
        ttk.Separator(self).grid(row=14, column=0,
                                 columnspan=4, padx=8, pady=5, sticky="ew")
        self.header_button.grid(
            row=16, column=0, columnspan=2, padx=8, pady=7, sticky="ew")
        self.footer_button.grid(
            row=16, column=2, columnspan=2, padx=8, pady=7, sticky="ew")
        ttk.Separator(self).grid(row=17, column=0,
                                 columnspan=4, padx=8, pady=5, sticky="ew")
        self.save_button.grid(row=18, column=3, padx=8, pady=7, sticky="ew")
        self.reset_button.grid(row=18, column=2, padx=8, pady=7, sticky="ew")

    def open_colorpicker(self, event):
        color = askcolor(parent=self, color=self.canvas_color_var.get(), title="Выберите цвет фона")[1]
        if color:
            self.canvas_color_var.set(color)
            self.color_entry.config(bg=color, disabledbackground=color,
                                    disabledforeground=self.generate_new_color(color))

    def generate_new_color(self, color):
        rgb = list(self.hex_to_rgb(color))
        rgb[0] = max(1, min(255, 240 - rgb[0]))
        rgb[1] = max(1, min(255, 240 - rgb[1]))
        rgb[2] = max(1, min(255, 240 - rgb[2]))
        return self.rgb_to_hex(*rgb)

    def hex_to_rgb(self, color):
        value = color.lstrip('#')
        lv = len(value)
        return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))

    def rgb_to_hex(self, red, green, blue):
        return f"#{red:02x}{green:02x}{blue:02x}"

    def reset_all(self):
        self.focus()
        self.movetype_chooser_var.set("Перетаскивание")
        self.gametype_chooser_var.set("Стандартный")
        self.canvas_color_var.set("#0d4b34")
        self.color_entry.config(bg="#0d4b34", disabledbackground="#0d4b34")
        self.header_button_var.set(True)
        self.footer_button_var.set(True)
        self.card_back_var.set("dark_back")
        self.last_gamemode = self.gametype_chooser_var.get()

    def save(self):
        settings = {}
        settings["movetype"] = self.movetype_chooser_var.get()
        settings["gamemode"] = self.gametype_chooser_var.get()
        settings["show_footer"] = str(self.footer_button_var.get())
        settings["show_header"] = str(self.header_button_var.get())
        settings["card_back"] = str(self.card_back_var.get())
        settings["canvas_color"] = str(self.canvas_color_var.get())
        self.updated_settings = True
        with open(os.path.join("assets", "settings.json"), "w", encoding="utf-8") as handle:
            handle.write(str(settings).replace("'", '"'))
        self.event_generate("<<SettingsClose>>")
        self.destroy()

    def enter_button(self, event):
        event.widget.config(bg="#706c6c")

    def leave_button(self, event):
        event.widget.config(bg="#b0acac")

    def gametype_chooser_select(self, event):
        self.focus()

    def movetype_chooser_select(self, event):
        self.focus()

    def delete_window(self, *args):
        if not self.updated_settings:
            settings = {}
            settings["movetype"] = self.movetype_chooser_var.get()
            settings["gamemode"] = self.gametype_chooser_var.get()
            settings["show_footer"] = str(self.footer_button_var.get())
            settings["show_header"] = str(self.header_button_var.get())
            settings["canvas_color"] = str(self.canvas_color_var.get())
            settings["card_back"] = str(self.card_back_var.get())
            if self.settings != settings:
                save = messagebox.askyesnocancel(
                    "Сохранение настроек.", "Вы изменили настройки. Хотите сохранить их?", parent=self, default="yes", icon="warning")
                if save:
                    with open(os.path.join("assets", "settings.json"), "w", encoding="utf-8") as handle:
                        handle.write(str(settings).replace("'", '"'))
                elif save is None:
                    return
        self.event_generate("<<SettingsClose>>")
        self.destroy()


def main():
    window = SolitareGameWindow()
    window.mainloop()


if __name__ == "__main__":
    main()




