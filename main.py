import ipaddress
import random
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from kivy.app import App
from kivy.clock import Clock
from kivy.core.clipboard import Clipboard
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

# رنج‌های آی‌پی کلودفلر و ریلی
CLOUDFLARE_CIDRS = [
    "103.21.244.0/22",
    "103.22.200.0/22",
    "103.31.4.0/22",
    "141.101.64.0/18",
    "108.162.192.0/18",
    "190.93.240.0/20",
    "188.114.96.0/20",
    "197.234.240.0/22",
    "198.41.128.0/17",
    "162.158.0.0/15",
    "104.16.0.0/13",
    "104.24.0.0/14",
    "172.64.0.0/13",
    "131.0.72.0/22",
]
RAILWAY_CIDRS = [
    "34.198.0.0/16",
    "35.153.0.0/16",
    "52.200.0.0/16",
    "3.80.0.0/14",
    "18.200.0.0/14",
]
VPN_PORTS = [443, 8443, 2053, 2083, 2087, 2095, 80, 8080]


class MobileScannerApp(App):

  def build(self):
    self.title = "AghaKocholo Mobile Scanner"
    self.is_scanning = False
    self.live_results = []
    self.current_mode = "cloudflare"

    root = BoxLayout(orientation="vertical", padding=15, spacing=10)

    # عنوان برنامه
    self.title_lbl = Label(
        text="⚡ AGHAKOCHOLO MOBILE SCANNER ⚡",
        font_size=18,
        bold=True,
        color=(0, 1, 0.8, 1),
        size_hint_y=None,
        height=40,
    )
    root.add_widget(self.title_lbl)

    # دکمه‌های انتخاب حالت (کلودفلر / ریلی)
    mode_layout = BoxLayout(
        orientation="horizontal", spacing=10, size_hint_y=None, height=45
    )
    self.btn_cf = Button(
        text="کلودفلر",
        background_color=(0, 0.7, 0.3, 1),
        on_press=lambda x: self.set_mode("cloudflare"),
    )
    self.btn_rw = Button(
        text="ریلی (Railway)",
        background_color=(0.2, 0.2, 0.2, 1),
        on_press=lambda x: self.set_mode("railway"),
    )
    mode_layout.add_widget(self.btn_cf)
    mode_layout.add_widget(self.btn_rw)
    root.add_widget(mode_layout)

    # ورودی تعداد آی‌پی
    input_layout = BoxLayout(
        orientation="horizontal", spacing=10, size_hint_y=None, height=45
    )
    input_layout.add_widget(
        Label(
            text="تعداد آی‌پی (حداکثر 100k):",
            font_size=14,
            size_hint_x=0.6,
        )
    )
    self.ip_input = TextInput(
        text="1000", multiline=False, font_size=16, size_hint_x=0.4
    )
    input_layout.add_widget(self.ip_input)
    root.add_widget(input_layout)

    # دکمه‌های کنترل اسکن (شروع و توقف)
    btn_ctrl_layout = BoxLayout(
        orientation="horizontal", spacing=10, size_hint_y=None, height=45
    )
    self.start_btn = Button(
        text="🚀 شروع اسکن",
        background_color=(0, 0.8, 0.4, 1),
        bold=True,
        on_press=self.start_scan,
    )
    self.stop_btn = Button(
        text="⏹ توقف",
        background_color=(0.8, 0.2, 0.2, 1),
        bold=True,
        disabled=True,
        on_press=self.stop_scan,
    )
    btn_ctrl_layout.add_widget(self.start_btn)
    btn_ctrl_layout.add_widget(self.stop_btn)
    root.add_widget(btn_ctrl_layout)

    # ترمینال نمایش لاگ‌ها
    self.log_scroll = ScrollView(size_hint=(1, 1))
    self.log_label = Label(
        text="[ System Ready ] آماده برای اسکن...\n",
        font_size=13,
        color=(0, 1, 0.4, 1),
        valign="top",
        halign="left",
    )
    self.log_label.bind(
        texture_size=lambda s, w: setattr(s, "height", w[1]),
        width=lambda s, w: setattr(s, "text_size", (w[0], None)),
    )
    self.log_scroll.add_widget(self.log_label)
    root.add_widget(self.log_scroll)

    # دکمه درباره ما و خروج
    footer_layout = BoxLayout(
        orientation="horizontal", spacing=10, size_hint_y=None, height=40
    )
    about_btn = Button(
        text="ℹ️ درباره ما",
        background_color=(0.3, 0.3, 0.3, 1),
        on_press=self.show_about,
    )
    exit_btn = Button(
        text="🚪 خروج",
        background_color=(0.5, 0.1, 0.1, 1),
        on_press=lambda x: App.get_running_app().stop(),
    )
    footer_layout.add_widget(about_btn)
    footer_layout.add_widget(exit_btn)
    root.add_widget(footer_layout)

    return root

  def set_mode(self, mode):
    self.current_mode = mode
    if mode == "cloudflare":
      self.btn_cf.background_color = (0, 0.7, 0.3, 1)
      self.btn_rw.background_color = (0.2, 0.2, 0.2, 1)
    else:
      self.btn_rw.background_color = (0, 0.7, 0.3, 1)
      self.btn_cf.background_color = (0.2, 0.2, 0.2, 1)

  def log(self, message):
    Clock.schedule_once(lambda dt: self._append_log(message))

  def _append_log(self, message):
    self.log_label.text += message + "\n"

  def show_about(self, instance):
    content = BoxLayout(orientation="vertical", padding=15, spacing=10)
    text = (
        "این برنامه برای اسکن آی‌پی‌های تمیز\nکلودفلر و ریلی برای ایران طراحی شده"
        " است.\n\nتلگرام حامی:\n@Game94mod000"
    )
    content.add_widget(Label(text=text, halign="center"))
    close_btn = Button(
        text="بستن", size_hint_y=None, height=40, background_color=(0, 0.6, 0.3, 1)
    )
    content.add_widget(close_btn)

    popup = Popup(
        title="درباره ما", content=content, size_hint=(0.8, 0.5), auto_dismiss=True
    )
    close_btn.bind(on_press=popup.dismiss)
    popup.open()

  def test_ip(self, ip, port):
    if not self.is_scanning:
      return None
    start_time = time.time()
    try:
      s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
      s.settimeout(0.8)
      result = s.connect_ex((str(ip), port))
      if result == 0:
        latency = int((time.time() - start_time) * 1000)
        return {"ip": str(ip), "port": port, "latency": latency}
      s.close()
    except Exception:
      pass
    return None

  def run_scanner(self):
    try:
      total_ips = int(self.ip_input.text)
    except ValueError:
      self.log("[!] خطا: تعداد آی‌پی باید عدد باشد!")
      self.reset_buttons()
      return

    if total_ips > 100000 or total_ips <= 0:
      self.log("[!] خطا: تعداد آی‌پی باید بین 1 تا 100,000 باشد!")
      self.reset_buttons()
      return

    self.live_results.clear()
    selected_cidrs = (
        CLOUDFLARE_CIDRS if self.current_mode == "cloudflare" else RAILWAY_CIDRS
    )
    all_cidrs = [ipaddress.ip_network(cidr) for cidr in selected_cidrs]

    self.log(
        f"[*] آماده‌سازی {total_ips} آی‌پی برای اسکن"
        f" {'کلودفلر' if self.current_mode=='cloudflare' else 'ریلی'}..."
    )

    tasks = []
    while len(tasks) < total_ips and self.is_scanning:
      network = random.choice(all_cidrs)
      bits = network.max_prefixlen - network.prefixlen
      if bits < 2:
        continue
      random_ip = network.network_address + random.randint(
          1, (2**bits) - 2
      )
      for port in VPN_PORTS:
        tasks.append((random_ip, port))

    self.log("[*] شروع فرآیند تست پورت‌ها...")

    with ThreadPoolExecutor(max_workers=200) as executor:
      futures = {
          executor.submit(self.test_ip, ip, port): (ip, port)
          for ip, port in tasks
      }

      for future in as_completed(futures):
        if not self.is_scanning:
          executor.shutdown(wait=False, cancel_futures=True)
          break
        res = future.result()
        if res:
          self.live_results.append(res)
          self.log(
              f"[✔] LIVE -> {res['ip']}:{res['port']} | Ping: {res['latency']}ms"
          )

    if self.is_scanning:
      self.log("\n==================== [ پایان اسکن ] ====================")
      self.log(f"[+] کل آی‌پی‌های سالم: {len(self.live_results)}")
      self.reset_buttons()
      Clock.schedule_once(lambda dt: self.show_top_results())

  def start_scan(self, instance):
    if self.is_scanning:
      return
    self.is_scanning = True
    self.start_btn.disabled = True
    self.stop_btn.disabled = False
    self.log_label.text = ""

    t = threading.Thread(target=self.run_scanner)
    t.daemon = True
    t.start()

  def stop_scan(self, instance):
    self.is_scanning = False
    self.log("[!] اسکن متوقف شد.")
    self.reset_buttons()

  def reset_buttons(self):
    self.is_scanning = False
    self.start_btn.disabled = False
    self.stop_btn.disabled = True

  def show_top_results(self):
    sorted_res = sorted(self.live_results, key=lambda x: x["latency"])
    content = BoxLayout(orientation="vertical", padding=10, spacing=10)

    if not sorted_res:
      content.add_widget(
          Label(text="هیچ آی‌پی فعالی پیدا نشد!", color=(1, 0, 0, 1))
      )
    else:
      top_3 = sorted_res[:3]
      for i, r in enumerate(top_3):
        ip_str = f"{r['ip']}:{r['port']}"
        row = BoxLayout(orientation="horizontal", spacing=10)
        row.add_widget(
            Label(
                text=f"رتبه {i+1}: {ip_str}\nپینگ: {r['latency']}ms",
                font_size=12,
            )
        )
        copy_btn = Button(
            text="کپی",
            size_hint_x=None,
            width=70,
            background_color=(0, 0.5, 0.8, 1),
            on_press=lambda x, text=ip_str: self.copy_ip(text),
        )
        row.add_widget(copy_btn)
        content.add_widget(row)

    close_btn = Button(
        text="تایید",
        size_hint_y=None,
        height=40,
        background_color=(0, 0.6, 0.3, 1),
    )
    content.add_widget(close_btn)

    popup = Popup(
        title="🏆 ۳ آی‌پی برتر",
        content=content,
        size_hint=(0.9, 0.6),
        auto_dismiss=True,
    )
    close_btn.bind(on_press=popup.dismiss)
    popup.open()

  def copy_ip(self, ip_text):
    Clipboard.copy(ip_text)
    self.log(f"[ کپی شد ] -> {ip_text}")


if __name__ == "__main__":
  MobileScannerApp().run()
