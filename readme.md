# ⚽ Football Shirts Order Manager

My friends and I love football and, as every fan knows, soccer shirts are a must for almost everyone. 

I built this project to act as a private shop for my circle, allowing us to easily manage and order shirts from our suppliers. 

## 🛠️ Infrastructure & Tech Stack
* **Hardware:** The project is fully deployed on a **Raspberry Pi 3b+** that was sitting in my wardrobe for years. It's the perfect board for this kind of project since the website doesn't have massive traffic.
* **Performance:** I experienced some lag issues when 4 or 5 people were entering the site at the same time. I partially fixed this by configuring caching through **Cloudflare**, which significantly improved load times.
* **Backend:** Powered by Python (`app.py`). I integrated the **Telegram API** to automatically send the incoming "orders" to my personal account, formatted exactly how I need them to forward to my supplier.
* **Frontend:** Based on `catalogo.html`. 

## 💡 About the Development
The core logic and structure were mainly built with the help of AI because I wanted a quick and easy solution. The design is highly upgradeable, but since it is mainly for personal use and front-end design isn't my main focus, it gets the job done perfectly. 

The scripts are straightforward and heavily commented, but feel free to AMA (Ask Me Anything)!
